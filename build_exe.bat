@echo off
setlocal

rem Compatibilidade com o nome histórico do script de build.
call "%~dp0Construir_Instalador.bat"
exit /b %ERRORLEVEL%

