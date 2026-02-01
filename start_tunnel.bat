@echo off
title Aviation Dashboard Tunnel
color 0A
echo ===================================================
echo   AVIATION OPERATIONS DASHBOARD - CLOUD TUNNEL
echo ===================================================
echo.
echo [INFO] API Server should be running on Port 5001...
echo [INFO] Initiating Secure Tunnel to Internet...
echo.
echo ---------------------------------------------------
echo  INSTRUCTIONS:
echo  1. Look for a line saying: "Connect to https://..."
echo  2. Copy that URL and open on your Phone/Laptop.
echo  3. Keep this window OPEN to keep the link active.
echo ---------------------------------------------------
echo.
ssh -o StrictHostKeyChecking=no -R 80:localhost:5001 nokey@localhost.run
echo.
echo [WARN] Tunnel Disconnected.
pause
