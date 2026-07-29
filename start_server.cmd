@echo off

cd /d C:\sistemaBMCM

call venv\Scripts\activate

python -m waitress --listen=0.0.0.0:8080 wsgi:app