import hashlib
import hmac
import json
import os
import queue
import threading
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

from src.auth import OAuthError, build_authorize_url, exchange_code_for_token
from src.github import list_repos, search_repos, view_repo, list_commits

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

KST_OFFSET = timedelta(hours=9)

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

_subscribers = []
_subscribers_lock = threading.Lock()


def _broadcast_event(message):
    with _subscribers_lock:
        subscribers = list(_subscribers)
    for subscriber_queue in subscribers:
        try:
            subscriber_queue.put_nowait(message)
        except queue.Full:
            pass  # 느린/방치된 구독자는 건너뛴다


@app.template_filter("format_datetime")
def format_datetime(value):
    """GitHub이 UTC로 내려주는 시각을 한국 시간(KST)으로 변환해 표시한다."""
    if not value:
        return value
    try:
        utc_dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return (utc_dt + KST_OFFSET).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return value


def _oauth_config():
    return {
        "client_id": os.environ.get("GITHUB_CLIENT_ID"),
        "client_secret": os.environ.get("GITHUB_CLIENT_SECRET"),
        "redirect_uri": os.environ.get("GITHUB_REDIRECT_URI", "http://localhost:8080/callback"),
        "scope": os.environ.get("GITHUB_CLIENT_SCOPE", "read:user repo"),
    }


PUBLIC_ENDPOINTS = {"login", "login_github", "callback", "static", "github_webhook"}
ALLOWED_REPO_SORTS = {"full_name", "created", "updated"}


@app.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if not session.get("github_token"):
        return redirect(url_for("login"))
    return None


@app.route("/")
def index():
    return redirect(url_for("repos"))


@app.route("/login")
def login():
    return render_template("login.html", error=request.args.get("error"))


@app.route("/login/github")
def login_github():
    config = _oauth_config()
    if not config["client_id"]:
        return redirect(url_for("login", error="GITHUB_CLIENT_ID가 설정되어 있지 않습니다"))

    authorize_url = build_authorize_url(
        config["client_id"], config["redirect_uri"], config["scope"]
    )
    return redirect(authorize_url)


@app.route("/callback")
def callback():
    error = request.args.get("error")
    code = request.args.get("code")
    if error or not code:
        return redirect(url_for("login", error=error or "인가 코드를 받지 못했습니다"))

    config = _oauth_config()
    try:
        token = exchange_code_for_token(
            config["client_id"],
            config["client_secret"],
            code,
            config["redirect_uri"],
        )
    except OAuthError as exc:
        return redirect(url_for("login", error=str(exc)))

    session["github_token"] = token
    return redirect(url_for("repos"))


@app.route("/repos")
def repos():
    token = session["github_token"]

    q = request.args.get("q", "")
    sort = request.args.get("sort", "updated")
    if sort not in ALLOWED_REPO_SORTS:
        sort = "updated"

    try:
        repo_list = search_repos(token, q, sort) if q else list_repos(token, sort)
    except requests.HTTPError:
        session.pop("github_token", None)
        return redirect(url_for("login", error="세션이 만료되었습니다. 다시 로그인해주세요"))

    return render_template("repos.html", repos=repo_list)


@app.route("/repos/<owner>/<repo>")
def repo_detail(owner, repo):
    token = session["github_token"]

    try:
        repo_detail = view_repo(token, owner, repo)
    except requests.HTTPError:
        session.pop("github_token", None)
        return redirect(url_for("login", error="세션이 만료되었습니다. 다시 로그인해주세요"))

    return render_template("repo_detail.html", repo=repo_detail)


@app.route("/repos/<owner>/<repo>/commits")
def repo_commits(owner, repo):
    token = session["github_token"]

    try:
        commits = list_commits(token, owner, repo)
    except requests.HTTPError:
        session.pop("github_token", None)
        return redirect(url_for("login", error="세션이 만료되었습니다. 다시 로그인해주세요"))

    return jsonify(commits)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _verify_webhook_signature(raw_body):
    if not GITHUB_WEBHOOK_SECRET:
        return True  # 로컬 개발 편의를 위해 시크릿 미설정 시에는 검증을 건너뛴다

    signature = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)


@app.route("/github/webhook", methods=["POST"])
def github_webhook():
    """GitHub Webhook 이벤트를 수신해 실시간 구독자(SSE)에게 전달한다."""
    if not _verify_webhook_signature(request.get_data()):
        return "signature mismatch", 401

    event_type = request.headers.get("X-GitHub-Event", "unknown")

    # GitHub Webhook 설정의 Content type이 기본값(application/x-www-form-urlencoded)이면
    # JSON이 아니라 payload=<form-encoded JSON> 형태로 오므로, 두 경우 모두 처리한다.
    payload = request.get_json(silent=True)
    if payload is None:
        raw_payload = request.form.get("payload")
        payload = json.loads(raw_payload) if raw_payload else {}

    repository = payload.get("repository") or {}

    message = {
        "event": event_type,
        "repo": repository.get("full_name"),
        "sender": (payload.get("sender") or {}).get("login"),
    }
    if event_type == "push":
        head_commit = payload.get("head_commit") or {}
        message["ref"] = payload.get("ref")
        message["commit_message"] = head_commit.get("message")

    _broadcast_event(message)

    return "OK", 200


@app.route("/events/stream")
def events_stream():
    """연결을 유지하며 webhook으로 들어온 이벤트를 실시간으로 브라우저에 전달한다(SSE)."""

    def generate():
        subscriber_queue = queue.Queue(maxsize=50)
        with _subscribers_lock:
            _subscribers.append(subscriber_queue)
        try:
            while True:
                try:
                    message = subscriber_queue.get(timeout=15)
                    yield f"data: {json.dumps(message)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            with _subscribers_lock:
                _subscribers.remove(subscriber_queue)

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)
