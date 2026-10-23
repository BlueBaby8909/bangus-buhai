@echo off
cd /d "%~dp0.."
backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --no-proxy-headers --ws wsproto --ws-max-size 4096
