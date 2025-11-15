@echo off
title 🚀 Cloudflare Tunnel - Smart Seat
echo ==========================================
echo   Starting Cloudflare Tunnel for Smart Seat
echo   Tunnel Name : smart-seat
echo   Domain      : seat.liangzhe.top
echo ==========================================
echo.

REM 切换到 cloudflared 的安装目录
cd /d "C:\Program Files (x86)\cloudflared"

REM 启动隧道（正确参数顺序）
cloudflared.exe tunnel run smart-seat


echo.
echo ==========================================
echo Tunnel stopped or exited.
echo You can close this window.
echo ==========================================
pause

