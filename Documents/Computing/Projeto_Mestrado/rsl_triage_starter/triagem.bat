@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" >nul 2>nul || (
    echo [ERRO] Nao foi possivel acessar o diretorio do launcher.
    exit /b 1
)

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
if not defined VIRTUAL_ENV if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    exit /b 1
)

if not "%~1"=="" (
    python "src\fastslr\bat_ui.py" %*
    exit /b %ERRORLEVEL%
)

python "src\fastslr\bat_ui.py"
set "EXIT_CODE=%ERRORLEVEL%"

if "%TERM_PROGRAM%"=="" if "%WT_SESSION%"=="" pause
exit /b %EXIT_CODE%
