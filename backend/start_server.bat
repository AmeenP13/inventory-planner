@echo off
cd /d "%~dp0"
uvicorn app.main:app --reload
pause