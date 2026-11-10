@echo off
cd /d "%~dp0"
title Doce Pedido - PIT II
py -3 --version >nul 2>&1
if not errorlevel 1 goto usar_py
python --version >nul 2>&1
if not errorlevel 1 goto usar_python
echo.
echo O Python ainda nao esta instalado neste computador.
echo Baixe o Python em https://www.python.org/downloads/
echo Na instalacao, marque a opcao Add Python to PATH.
echo Depois, abra este arquivo novamente.
pause
exit /b
:usar_py
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
py -3 app.py
goto fim
:usar_python
start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
python app.py
:fim
echo.
echo O sistema foi encerrado. Se houver erro, envie uma foto desta tela.
pause
