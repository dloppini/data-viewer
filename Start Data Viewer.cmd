@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv || goto failed
)
if not exist ".venv\Lib\site-packages\bokeh\server\static\js\bokeh.min.js" (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto failed
)
".venv\Scripts\python.exe" viewer.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo Could not start Data Viewer. Check Python 3.12 and requirements.txt.
pause
exit /b 1
