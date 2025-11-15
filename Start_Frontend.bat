@echo off
cd /d "%~dp0"
echo ---------------------------------------------
echo  Starting Smart Seat frontend (http-server)
echo ---------------------------------------------

npx http-server "public" -p 5500 -c-1

pause
