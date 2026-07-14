import os

import requests
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

from src.auth import OAuthError, build_authorize_url, exchange_code_for_token
from src.github import list_repos

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")


def _oauth_config():
    return {
        "client_id": os.environ.get("GITHUB_CLIENT_ID"),
        "client_secret": os.environ.get("GITHUB_CLIENT_SECRET"),
        "redirect_uri": os.environ.get("GITHUB_REDIRECT_URI", "http://localhost:8080/callback"),
        "scope": os.environ.get("GITHUB_CLIENT_SCOPE", "read:user repo"),
    }


PUBLIC_ENDPOINTS = {"login", "login_github", "callback", "static"}


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

    try:
        repo_list = list_repos(token)
    except requests.HTTPError:
        session.pop("github_token", None)
        return redirect(url_for("login", error="세션이 만료되었습니다. 다시 로그인해주세요"))

    return render_template("repos.html", repos=repo_list)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
