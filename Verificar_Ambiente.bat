@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%.venv-%COMPUTERNAME%\Scripts\python.exe"

pushd "%PROJECT_DIR%"

"%PYTHON_EXE%" -c "import lxml, usb, PIL, pyclipper, ezdxf"
if errorlevel 1 goto :erro

for %%F in (*.py) do (
    "%PYTHON_EXE%" -m py_compile "%%F"
    if errorlevel 1 goto :erro
)

"%PYTHON_EXE%" -m unittest discover -s tests -v
if errorlevel 1 goto :erro

echo Verificacao local concluida sem acessar a maquina laser.
popd
exit /b 0

:erro
echo ERRO: a verificacao local falhou.
popd
exit /b 1
