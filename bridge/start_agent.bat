@echo off
rem Codex bridge local agent (Windows). Copy config.example.json to config.json first.
cd /d "%~dp0"
if not exist config.json (
  echo config.json not found. Copy config.example.json to config.json and edit it.
  pause
  exit /b 1
)
:loop
python local_agent.py --config config.json
echo agent exited, restarting in 10s...
timeout /t 10 /nobreak >nul
goto loop
