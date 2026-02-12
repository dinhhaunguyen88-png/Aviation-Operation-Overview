@echo off
title Aviation Dashboard - Cloudflare Tunnel
color 0B
echo ===================================================
echo   AVIATION OPERATIONS DASHBOARD - CLOUD TUNNEL
echo ===================================================
echo.
echo [INFO] Preparing Cloudflare Tunnel...
echo [INFO] Production Port: 5000
echo.
echo ---------------------------------------------------
echo  INSTRUCTIONS:
echo  1. Look for a line saying: "https://[your-link].trycloudflare.com"
echo  2. Copy that URL and share with the Team.
echo  3. Keep this window OPEN to keep the link active.
echo ---------------------------------------------------
echo.
.\cloudflared.exe tunnel --url http://localhost:5000 --protocol http2
echo.
echo [WARN] Tunnel Disconnected.
pause
