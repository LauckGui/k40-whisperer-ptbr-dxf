@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv-%COMPUTERNAME%\Scripts\python.exe"
set "APP_SCRIPT=%PROJECT_DIR%k40_whisperer.py"

"%PYTHON_EXE%" -c "import lxml, usb, PIL, pyclipper, ezdxf, cairosvg" >nul 2>&1
if errorlevel 1 (
    echo Preparando o ambiente Python local para este computador...
    call "%PROJECT_DIR%Preparar_Ambiente.bat"
    if errorlevel 1 exit /b %ERRORLEVEL%
)

pushd "%PROJECT_DIR%"
"%PYTHON_EXE%" "%APP_SCRIPT%" %*
set "APP_EXIT_CODE=%ERRORLEVEL%"
popd

if not "%APP_EXIT_CODE%"=="0" (
    echo.
    echo O K40 Whisperer foi encerrado com o codigo %APP_EXIT_CODE%.
    pause
)

exit /b %APP_EXIT_CODE%
