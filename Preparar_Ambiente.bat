@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv-%COMPUTERNAME%"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

pushd "%PROJECT_DIR%"

"%PYTHON_EXE%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo Criando ambiente Python em "%VENV_DIR%"...
    py -3.14 -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo ERRO: instale o Python 3.14 de 64 bits e habilite o comando py.
        popd
        exit /b 1
    )
)

echo Instalando dependencias fixadas...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :erro
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto :erro

"%PYTHON_EXE%" -c "import lxml, usb, PIL, pyclipper, ezdxf, cairosvg; print('Ambiente K40 pronto:', __import__('sys').executable)"
if errorlevel 1 goto :erro

popd
exit /b 0

:erro
echo ERRO: nao foi possivel preparar o ambiente Python.
popd
exit /b 1
