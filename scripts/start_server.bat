@echo off
cd /d "%~dp0\.."
uvicorn src.backend.main:app --reload
pause