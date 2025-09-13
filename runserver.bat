@echo off
cd /d C:\plate_o\plate_o
call ..\venv\Scripts\activate.bat
python manage.py runserver 0.0.0.0:8000
