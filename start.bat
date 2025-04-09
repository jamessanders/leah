@echo off


REM Add src to PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%\src

REM Start the Flask HTTP server
python src/http_server.py 