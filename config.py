import os
import secrets

# Controle de versão: principal.atualização.contagem_do_dia.
APP_VERSION_MAJOR = 1
APP_VERSION_UPDATE = 4
APP_VERSION_DAILY_COUNT = 6
APP_VERSION = f"{APP_VERSION_MAJOR}.{APP_VERSION_UPDATE}.{APP_VERSION_DAILY_COUNT}"

class Config:
    APP_VERSION = APP_VERSION
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "database.db")
    )
SQLALCHEMY_TRACK_MODIFICATIONS = False

from datetime import timedelta
PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)
