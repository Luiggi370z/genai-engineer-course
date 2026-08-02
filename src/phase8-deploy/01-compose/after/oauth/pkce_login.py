#!/usr/bin/env python3
"""Get a real access token from the OAuth lane's Keycloak, by logging in.

    docker compose -f docker-compose.yml -f docker-compose.secure.yml \
                   -f docker-compose.oauth.yml up --build
    python oauth/pkce_login.py                 # browser opens; log in as alice/alice
    curl -H "Authorization: Bearer $TOKEN" ... # the token works on /ask

Stdlib only, and short on purpose: the authorization-code + PKCE flow is about
sixty lines of real work, and seeing that is worth more than importing a client
library that hides which of the four defences you actually enabled.

The redirect URI is `http://127.0.0.1:8765/callback` — registered in the realm,
sent at authorize, and sent AGAIN at exchange. Loopback is what makes this safe
for a CLI: the code is delivered to a socket only this process is listening on.

Every real decision here lives in `assistant/oauth.py`, which is unit-tested
offline. This file is the part that needs a browser.
"""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import threading
import urllib.error
import webbrowser
from pathlib import Path

# Import the flow from the capstone package rather than reimplementing it: the
# tested code and the runnable script must not be two different flows.
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "workshops/assistant/after/src"))
from assistant import oauth  # noqa: E402

REDIRECT_HOST, REDIRECT_PORT = "127.0.0.1", 8765
REDIRECT_URI = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/callback"

PAGE = b"""<!doctype html><meta charset=utf-8>
<title>Signed in</title>
<body style="font:16px system-ui;padding:3rem">
<h1>Signed in.</h1><p>You can close this tab and go back to the terminal.</p>
"""


def wait_for_callback() -> str:
    """Serve exactly one request and return the URL the browser was sent to."""
    captured: dict[str, str] = {}
    arrived = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 — http.server's interface
            captured["url"] = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}{self.path}"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGE)
            arrived.set()

        def log_message(self, *_args) -> None:
            return  # the access log is noise here

    server = http.server.HTTPServer((REDIRECT_HOST, REDIRECT_PORT), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    if not arrived.wait(timeout=300):
        server.server_close()
        raise TimeoutError("no callback within five minutes — did the login finish?")
    server.server_close()
    return captured["url"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issuer", default="http://localhost:8081/realms/assistant")
    parser.add_argument("--client-id", default="assistant-cli")
    parser.add_argument("--audience", default="assistant")
    parser.add_argument(
        "--scope",
        default="openid assistant:ask assistant:ingest assistant:approve",
        help="ask for only what you need; the assistant checks per endpoint",
    )
    args = parser.parse_args()

    try:
        endpoints = oauth.discover(args.issuer)
    except (urllib.error.URLError, OSError) as exc:
        print(f"cannot reach the issuer at {args.issuer}: {exc}", file=sys.stderr)
        print("is the oauth overlay up? see docker-compose.oauth.yml", file=sys.stderr)
        return 1

    pkce = oauth.pkce_pair()
    url, state = oauth.authorization_url(
        endpoints,
        client_id=args.client_id,
        redirect_uri=REDIRECT_URI,
        scope=args.scope,
        audience=args.audience,
        pkce=pkce,
    )

    print(f"opening the browser; if nothing happens, visit:\n  {url}\n")
    webbrowser.open(url)
    code = oauth.callback_params(wait_for_callback(), expected_state=state)
    tokens = oauth.exchange_code(
        endpoints,
        code=code,
        client_id=args.client_id,
        redirect_uri=REDIRECT_URI,
        pkce=pkce,
    )
    print(json.dumps({k: v for k, v in tokens.items() if k != "id_token"}, indent=2))
    print(f"\nexport TOKEN={tokens['access_token']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
