@echo off
title Aviation Dashboard - Production Server
color 0E
echo ===================================================
echo   AVIATION OPERATIONS DASHBOARD - PRODUCTION
echo ===================================================
echo.
echo [INFO] Loading Production Environment...
set FLASK_ENV=production
set DOTENV_CONFIG_PATH=.env.production

echo [INFO] Starting Server on Port 5000...
echo.
python run_server.py
echo.
echo [WARN] Server Stopped.
pause
