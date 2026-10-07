@echo off
setlocal
title Configuracao de Permissao - Tela de Bloqueio Lively
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_lockscreen_permission.ps1" -TargetUserName "%USERDOMAIN%\%USERNAME%"
if %ERRORLEVEL% neq 0 pause
