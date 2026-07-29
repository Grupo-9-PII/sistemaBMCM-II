import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "sua_chave_super_secreta"
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "database.db")
    )
SQLALCHEMY_TRACK_MODIFICATIONS = False

from datetime import timedelta
PERMANENT_SESSION_LIFETIME = timedelta(minutes=15)
