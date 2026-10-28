@echo off
title IRIS
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual pela primeira vez...
    python -m venv .venv || goto erro
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
)

rem instala as bibliotecas na primeira vez e sempre que o requirements.txt mudar
fc /b requirements.txt ".venv\requirements-instalado.txt" >nul 2>&1
if errorlevel 1 (
    echo Instalando/atualizando bibliotecas...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto erro
    copy /y requirements.txt ".venv\requirements-instalado.txt" >nul
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Criei o arquivo .env - cole suas chaves de API nele.
)

".venv\Scripts\python.exe" -m iris
goto fim

:erro
echo.
echo Algo deu errado na instalacao. Veja a mensagem acima.
pause

:fim
