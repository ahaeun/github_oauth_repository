import http.server
import os
import threading
import urllib.parse
import webbrowser

import requests

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"

DEFAULT_SCOPE = "read:user repo"
DEFAULT_REDIRECT_URI = "http://localhost:8080/callback"


class OAuthError(Exception):
    pass


class _CallbackServer(http.server.HTTPServer):
    def __init__(self, address):
        super().__init__(address, _CallbackHandler)
        self.auth_code = None
        self.error = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            self.server.auth_code = params["code"][0]
            body = "로그인 완료. 창을 닫으셔도 됩니다."
        else:
            self.server.error = params.get("error", ["unknown_error"])[0]
            body = f"로그인 실패: {self.server.error}"

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *_args):
        pass  # 콜백 서버 접근 로그는 출력하지 않는다


def _wait_for_authorization_code(redirect_uri):
    parsed = urllib.parse.urlparse(redirect_uri)
    server = _CallbackServer((parsed.hostname, parsed.port))

    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=300)

    if server.auth_code is None:
        raise OAuthError(f"인가 코드를 받지 못했습니다: {server.error}")
    return server.auth_code


def build_authorize_url(client_id, redirect_uri, scope):
    return f"{AUTHORIZE_URL}?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
        }
    )


def exchange_code_for_token(client_id, client_secret, code, redirect_uri):
    response = requests.post(
        ACCESS_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    if "access_token" not in payload:
        raise OAuthError(f"토큰 교환 실패: {payload}")
    return payload["access_token"]


def login(client_id=None, client_secret=None, redirect_uri=None, scope=None):
    """GitHub OAuth Authorization Code Flow로 로그인하고 access token을 반환한다 (CLI용).

    로컬에 콜백 서버(redirect_uri)를 잠깐 띄워 인가 코드를 받은 뒤 토큰으로 교환한다.
    웹앱(src/webapp.py)에서는 이 함수 대신 build_authorize_url / exchange_code_for_token을
    Flask 라우트에서 직접 사용한다.
    """
    client_id = client_id or os.environ.get("GITHUB_CLIENT_ID")
    client_secret = client_secret or os.environ.get("GITHUB_CLIENT_SECRET")
    redirect_uri = redirect_uri or os.environ.get("GITHUB_REDIRECT_URI", DEFAULT_REDIRECT_URI)
    scope = scope or os.environ.get("GITHUB_CLIENT_SCOPE", DEFAULT_SCOPE)

    if not client_id or not client_secret:
        raise OAuthError("GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET이 설정되어 있지 않습니다 (.env 참고)")

    authorize_url = build_authorize_url(client_id, redirect_uri, scope)

    print(f"브라우저에서 로그인 페이지를 엽니다: {authorize_url}")
    webbrowser.open(authorize_url)

    code = _wait_for_authorization_code(redirect_uri)
    return exchange_code_for_token(client_id, client_secret, code, redirect_uri)
