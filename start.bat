@echo off
echo Starting Friday MCP Server in a new window...
start "Friday MCP Server" cmd /k "uv run friday"

echo Starting Friday Web Client in a new window...
start "Friday Web Client" cmd /k "uv run python web_friday.py"

echo Waiting for services to initialize...
timeout /t 6 >nul
start msedge http://127.0.0.1:8050/
