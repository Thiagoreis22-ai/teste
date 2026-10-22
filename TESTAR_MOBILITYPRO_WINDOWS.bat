@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
echo Execute INICIAR_MobilityPro_WINDOWS.bat primeiro.
pause
exit /b 1
)
.venv\Scripts\python.exe -m pytest -v tests\npause
