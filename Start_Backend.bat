@echo off
cd /d "%~dp0"
echo ---------------------------------------------
echo  Starting Smart Seat backend (Node.js)
echo ---------------------------------------------

set JWT_SECRET=change-me-in-prod
set DB_FILE=%cd%\data\db.secure.json

echo Running server on http://localhost:3000 ...
node server\server_protected_public.js

pause
