@echo off
REM ResetAdmin.bat - resets the admin credentials in db.secure.json
REM Edit DB_FILE to your actual path if needed.
set "DB_FILE=%~dp0db.secure.json"
echo Using DB_FILE=%DB_FILE%
where node >NUL 2>&1 || ( echo [ERROR] Node.js not found. Install from https://nodejs.org ; pause & exit /b 1 )
node "%~dp0reset_admin.js" "%DB_FILE%"
pause