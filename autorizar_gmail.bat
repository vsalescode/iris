@echo off
title IRIS - autorizar Gmail
cd /d "%~dp0"
".venv\Scripts\python.exe" -m iris.emails.autorizar
pause
