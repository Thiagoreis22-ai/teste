@echo off
setlocal
cd /d "%~dp0"
title MobilityPro - Servidor e Tres Aplicativos
color 0B
echo.
echo =========================================================
echo    MobilityPro  ^|  CENTRAL + PASSAGEIRO + MOTORISTA
 echo =========================================================
echo.
set PY_CMD=python
where py >nul 2>&1
if %errorlevel%==0 set PY_CMD=py -3
%PY_CMD% --version
if errorlevel 1 goto failpython
if not exist ".venv\Scripts\python.exe" (
 echo Criando ambiente isolado Python...
 %PY_CMD% -m venv .venv
 if errorlevel 1 goto fail
)
if not exist ".venv\installed.ok" (
 echo Instalando dependencias na primeira execucao... Internet necessaria.
 .venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt
 if errorlevel 1 goto fail
 echo ok>".venv\installed.ok"
)
echo.
echo INICIANDO. A tela preta deve continuar ABERTA.
echo Abra no Chrome os links exibidos abaixo.
.venv\Scripts\python.exe run.py
if errorlevel 1 goto fail
goto end
:failpython
echo.
echo ERRO: Python 3.11+ nao encontrado. Instale em python.org
:fail
echo.
echo FALHA NA INICIALIZACAO. Copie o erro acima e envie ao suporte.
pause
:end
endlocal
