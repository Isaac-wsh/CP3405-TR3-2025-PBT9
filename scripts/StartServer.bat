@echo off
REM StartServer.bat - installs deps (first run) and starts the protected server
cd /d %~dp0
echo ===== Smart Seat Admin Auth =====
where npm >NUL 2>&1 || (
  echo [ERROR] npm not found. Install Node.js LTS from https://nodejs.org and re-open this window.
  pause
  exit /b 1
)
if not exist node_modules (
  echo Installing dependencies...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)
set PORT=3000
set JWT_SECRET=change-me-in-prod
set DB_FILE=%~dp0db.secure.json
echo Starting server on http://localhost:%PORT% ...
node server_protected.js
pause