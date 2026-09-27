import json
import os
import secrets
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import current_app, session

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
GOOGLE_CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"
GOOGLE_DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
GOOGLE_OAUTH_SCOPES = (
    GMAIL_SEND_SCOPE,
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    GOOGLE_DRIVE_FILE_SCOPE,
)
GMAIL_SENDER_PATTERN = re.compile(r"^[^@\s]+@gmail\.com$", re.IGNORECASE)


def google_oauth_config():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id:
        raise RuntimeError(
            "Variável de ambiente GOOGLE_OAUTH_CLIENT_ID não configurada. "
            "Defina-a no arquivo .env do sistema."
        )
    if not client_secret:
        raise RuntimeError(
            "Variável de ambiente GOOGLE_OAUTH_CLIENT_SECRET não configurada. "
            "Defina-a no arquivo .env do sistema."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": os.environ.get(
            "GOOGLE_OAUTH_REDIRECT_URI",
            "http://localhost:8080/google/oauth/callback",
        ),
        "scopes": tuple(
            scope.strip()
            for scope in os.environ.get(
                "GOOGLE_OAUTH_SCOPES", " ".join(GOOGLE_OAUTH_SCOPES)
            ).split()
            if scope.strip()
        ),
    }


def authorization_url():
    config = google_oauth_config()
    state = secrets.token_urlsafe(32)
    session["google_oauth_state"] = state
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(config["scopes"]),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code, state):
    if not state or state != session.pop("google_oauth_state", None):
        raise ValueError("Estado OAuth inválido ou expirado.")

    config = google_oauth_config()
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    response.raise_for_status()
    token = response.json()
    if not token.get("refresh_token") and not token.get("access_token"):
        raise ValueError("O Google não retornou um token utilizável.")
    if token.get("expires_in"):
        token["expires_at"] = time.time() + token["expires_in"]
    return token


def token_file_path():
    instance_dir = Path(current_app.config["BASE_DIR"]) / "instance"
    instance_dir.mkdir(parents=True, exist_ok=True)
    return instance_dir / "google_oauth_token.json"


def save_token(token):
    existing_token = load_token()
    if existing_token and not token.get("refresh_token"):
        token = {**token, "refresh_token": existing_token.get("refresh_token")}
    path = token_file_path()
    path.write_text(json.dumps(token), encoding="utf-8")
    os.chmod(path, 0o600)


def load_token():
    path = token_file_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def has_token():
    token = load_token()
    if not token:
        return False
    granted_scopes = set((token.get("scope") or "").split())
    required_scopes = set(GOOGLE_OAUTH_SCOPES)
    configured_scopes = set(google_oauth_config()["scopes"])
    return required_scopes.issubset(granted_scopes) and required_scopes.issubset(
        configured_scopes
    )


def has_scope(scope):
    token = load_token()
    if not token:
        return False
    config = google_oauth_config()
    granted_scopes = set((token.get("scope") or "").split())
    return scope in granted_scopes and scope in config["scopes"]


def get_access_token():
    token = load_token()
    if not token:
        raise RuntimeError("A conta Google ainda não foi autorizada.")

    access_token = token.get("access_token")
    if access_token and token.get("expires_at", 0) > time.time() + 60:
        return access_token

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("A autorização Google não possui refresh token.")

    config = google_oauth_config()
    response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    response.raise_for_status()
    refreshed = response.json()
    if not refreshed.get("access_token"):
        raise ValueError("O Google não retornou um token de acesso renovado.")
    refreshed["refresh_token"] = refresh_token
    refreshed["expires_at"] = time.time() + refreshed.get("expires_in", 3600)
    save_token({**token, **refreshed})
    return refreshed["access_token"]


def is_gmail_sender(email):
    """Retorna se o remetente atende ao domínio exigido pelo Gmail OAuth."""
    return bool(email and GMAIL_SENDER_PATTERN.fullmatch(email.strip()))


def google_workspace_status(sender_email):
    """Retorna a disponibilidade conjunta do remetente e da autorização Google."""
    sender_valid = is_gmail_sender(sender_email)
    oauth_valid = False
    oauth_error = None
    try:
        oauth_valid = has_scope(GMAIL_SEND_SCOPE)
    except RuntimeError as exc:
        oauth_error = str(exc)

    if not sender_valid:
        reason = "Configure um remetente com domínio @gmail.com."
    elif not oauth_valid:
        reason = "Autorize o acesso ao Gmail para habilitar a Central de Comunicações."
    else:
        reason = "Gmail autorizado para a Central de Comunicações."

    return {
        "available": sender_valid and oauth_valid,
        "sender_valid": sender_valid,
        "oauth_valid": oauth_valid,
        "oauth_error": oauth_error,
        "reason": reason,
    }
