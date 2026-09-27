import base64
import mimetypes
from email.message import EmailMessage
from pathlib import Path

import requests

from .google_oauth import (
    get_access_token,
    google_workspace_status,
)
from .utils import obter_configuracao

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _build_message(sender, recipient, subject, body, attachments):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    for attachment in attachments:
        path = Path(attachment.caminho)
        content_type, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
        message.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=attachment.nome_original,
        )
    return message


def enviar_email_gmail(recipient, subject, body, attachments=()):
    sender = obter_configuracao("communication_sender_email")
    if not sender:
        raise RuntimeError("Configure o e-mail remetente da banda antes do envio.")
    if not google_workspace_status(sender)["available"]:
        raise RuntimeError(
            "A comunicação está bloqueada: o remetente deve ser @gmail.com "
            "e o Google Workspace precisa estar autorizado."
        )

    message = _build_message(sender, recipient, subject, body, attachments)
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii").rstrip("=")
    response = requests.post(
        GMAIL_SEND_URL,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        json={"raw": raw},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
