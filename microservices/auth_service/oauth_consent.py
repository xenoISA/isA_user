"""Helpers for OAuth authorization consent rendering and redirects."""

import html
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def authorization_consent_payload(
    *,
    client: Dict[str, Any],
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    resource: Optional[str],
    code_challenge: Optional[str],
    code_challenge_method: Optional[str],
) -> Dict[str, Any]:
    return {
        "action": "consent_required",
        "client_id": client_id,
        "client_name": client.get("client_name", client_id),
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "resource": resource,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }


def wants_html_response(accept_header: str) -> bool:
    return "text/html" in accept_header.lower()


def _hidden_input(name: str, value: Optional[str]) -> str:
    escaped_name = html.escape(name, quote=True)
    escaped_value = html.escape(value or "", quote=True)
    return f'<input type="hidden" name="{escaped_name}" value="{escaped_value}">'


def render_consent_screen(payload: Dict[str, Any]) -> str:
    client_name = html.escape(payload["client_name"], quote=True)
    redirect_uri = html.escape(payload["redirect_uri"], quote=True)
    resource = html.escape(payload.get("resource") or "Default resource", quote=True)
    scopes = payload.get("scope", "").split()
    if scopes:
        scope_markup = "\n".join(
            f"<li><code>{html.escape(scope, quote=True)}</code></li>"
            for scope in scopes
        )
    else:
        scope_markup = "<li>No scopes requested</li>"

    hidden_fields = "\n".join(
        [
            _hidden_input("response_type", "code"),
            _hidden_input("client_id", payload["client_id"]),
            _hidden_input("redirect_uri", payload["redirect_uri"]),
            _hidden_input("scope", payload["scope"]),
            _hidden_input("state", payload["state"]),
            _hidden_input("resource", payload.get("resource")),
            _hidden_input("code_challenge", payload.get("code_challenge")),
            _hidden_input(
                "code_challenge_method",
                payload.get("code_challenge_method"),
            ),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Authorize {client_name}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --accent: #0f766e;
      --border: #cbd5e1;
      --muted: #475569;
      --surface: #ffffff;
      --text: #0f172a;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --border: #334155;
        --muted: #94a3b8;
        --surface: #0f172a;
        --text: #f8fafc;
      }}
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: Canvas;
      color: var(--text);
      font: 16px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(92vw, 480px);
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      padding: 28px;
      box-sizing: border-box;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.2;
    }}
    p {{
      margin: 0 0 20px;
      color: var(--muted);
    }}
    dl {{
      margin: 0 0 20px;
    }}
    dt {{
      margin-top: 16px;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--muted);
    }}
    dd {{
      margin: 6px 0 0;
      overflow-wrap: anywhere;
    }}
    ul {{
      margin: 6px 0 0;
      padding-left: 20px;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 14px;
    }}
    .actions {{
      display: flex;
      gap: 12px;
      margin-top: 28px;
    }}
    button {{
      min-height: 44px;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0 16px;
      font: inherit;
      cursor: pointer;
    }}
    button[value="approve"] {{
      border-color: var(--accent);
      background: var(--accent);
      color: white;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Authorize {client_name}</h1>
    <p>This application is requesting access to your account.</p>
    <dl>
      <dt>Redirect URI</dt>
      <dd>{redirect_uri}</dd>
      <dt>Resource</dt>
      <dd>{resource}</dd>
      <dt>Scopes</dt>
      <dd><ul>{scope_markup}</ul></dd>
    </dl>
    <form method="post" action="/oauth/consent">
      {hidden_fields}
      <div class="actions">
        <button type="submit" name="decision" value="approve">Approve</button>
        <button type="submit" name="decision" value="deny">Deny</button>
      </div>
    </form>
  </main>
</body>
</html>"""


def redirect_with_oauth_params(
    redirect_uri: str,
    params: Dict[str, Optional[str]],
) -> str:
    parsed_uri = urlsplit(redirect_uri)
    query_params = parse_qsl(parsed_uri.query, keep_blank_values=True)
    query_params.extend((key, value) for key, value in params.items() if value)
    return urlunsplit(
        (
            parsed_uri.scheme,
            parsed_uri.netloc,
            parsed_uri.path,
            urlencode(query_params),
            parsed_uri.fragment,
        )
    )
