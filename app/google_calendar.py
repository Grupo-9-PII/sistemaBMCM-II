import hashlib
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from . import db
from .google_oauth import GOOGLE_CALENDAR_EVENTS_SCOPE, get_access_token, has_scope
from .models import GoogleCalendarSync

CALENDAR_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)
CALENDAR_TIME_ZONE = "America/Sao_Paulo"


def _google_event_id(activity_type, activity_id):
    key = f"bmcm:{activity_type}:{activity_id}".encode("utf-8")
    return f"a{hashlib.sha256(key).hexdigest()}"


def _activity_payload(activity_type, activity):
    if activity_type == "ensaio":
        summary = activity.titulo
        description = activity.observacoes
        location = activity.local
        start_date = activity.data_ensaio
        if activity.horario:
            start_time = time.fromisoformat(activity.horario)
            start_datetime = datetime.combine(
                start_date, start_time, tzinfo=ZoneInfo(CALENDAR_TIME_ZONE)
            )
            end_datetime = start_datetime + timedelta(hours=1)
            start = {
                "dateTime": start_datetime.isoformat(),
                "timeZone": CALENDAR_TIME_ZONE,
            }
            end = {
                "dateTime": end_datetime.isoformat(),
                "timeZone": CALENDAR_TIME_ZONE,
            }
        else:
            start = {"date": start_date.isoformat()}
            end = {"date": (start_date + timedelta(days=1)).isoformat()}
    elif activity_type == "evento":
        summary = activity.nome_evento
        description = None
        location = activity.cidade
        start_date = activity.data_evento
        start = {"date": start_date.isoformat()}
        end = {"date": (start_date + timedelta(days=1)).isoformat()}
    else:
        raise ValueError("Tipo de atividade não suportado pelo Google Calendar.")

    payload = {
        "summary": summary,
        "start": start,
        "end": end,
    }
    if description:
        payload["description"] = description
    if location:
        payload["location"] = location
    if activity.status == "CANCELADO":
        payload["status"] = "cancelled"
    return payload


def sincronizar_atividade(activity_type, activity):
    if not has_scope(GOOGLE_CALENDAR_EVENTS_SCOPE):
        raise RuntimeError(
            "Autorize o escopo do Google Calendar nas configurações do sistema."
        )

    if activity_type == "ensaio":
        sync = GoogleCalendarSync.query.filter_by(ensaio_id=activity.id).first()
    elif activity_type == "evento":
        sync = GoogleCalendarSync.query.filter_by(evento_id=activity.id).first()
    else:
        raise ValueError("Tipo de atividade não suportado pelo Google Calendar.")

    if activity.status == "CANCELADO" and sync is None:
        return False

    google_event_id = sync.google_event_id if sync else _google_event_id(
        activity_type, activity.id
    )
    payload = _activity_payload(activity_type, activity)
    if not sync:
        payload["id"] = google_event_id
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    if sync:
        response = requests.patch(
            f"{CALENDAR_EVENTS_URL}/{google_event_id}",
            headers=headers,
            json=payload,
            timeout=30,
        )
    else:
        response = requests.post(
            CALENDAR_EVENTS_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code == 409:
            payload.pop("id", None)
            response = requests.patch(
                f"{CALENDAR_EVENTS_URL}/{google_event_id}",
                headers=headers,
                json=payload,
                timeout=30,
            )

    response.raise_for_status()
    if sync is None:
        sync = GoogleCalendarSync(
            ensaio_id=activity.id if activity_type == "ensaio" else None,
            evento_id=activity.id if activity_type == "evento" else None,
            google_event_id=google_event_id,
        )
        db.session.add(sync)
    sync.sincronizado_em = datetime.now(timezone.utc)
    db.session.commit()
    return True


def sincronizar_se_vinculada(activity_type, activity):
    if activity_type == "ensaio":
        sync = GoogleCalendarSync.query.filter_by(ensaio_id=activity.id).first()
    elif activity_type == "evento":
        sync = GoogleCalendarSync.query.filter_by(evento_id=activity.id).first()
    else:
        raise ValueError("Tipo de atividade não suportado pelo Google Calendar.")
    if sync is None:
        return None
    return sincronizar_atividade(activity_type, activity)
