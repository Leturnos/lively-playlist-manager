@echo off
:: Request Administrator privileges if not already running as Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Solicitando privilegios de Administrador...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

title Configuracao de Permissao - Tela de Bloqueio Lively
color 0b
echo =======================================================================
echo     LIVELY PLAYLIST MANAGER - ATIVACAO DE TELA DE BLOQUEIO
echo =======================================================================
echo.
echo Concedendo permissao para que o aplicativo possa atualizar a imagem
echo da tela de bloqueio do Windows sem exibir avisos de Administrador...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference = 'Stop';" ^
    "try {" ^
    "    $sid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-545');" ^
    "    $paths = @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP', 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization');" ^
    "    foreach ($p in $paths) {" ^
    "        if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }" ^
    "        $acl = Get-Acl $p;" ^
    "        $rule = New-Object System.Security.AccessControl.RegistryAccessRule($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow');" ^
    "        $acl.SetAccessRule($rule);" ^
    "        Set-Acl $p $acl;" ^
    "    }" ^
    "    Write-Host 'Permissoes de registro aplicadas com exito!' -ForegroundColor Green;" ^
    "    exit 0;" ^
    "} catch {" ^
    "    Write-Host \"Erro ao configurar registro: $_\" -ForegroundColor Red;" ^
    "    exit 1;" ^
    "}"

if %errorLevel% equ 0 (
    echo.
    echo =======================================================================
    echo  [SUCESSO] Configuracao concluida com exito!
    echo  Agora voce pode ativar "Sincronizar Tela de Bloqueio" no menu
    echo  da bandeja do sistema (proximo ao relogio, abaixo de Monitor).
    echo =======================================================================
) else (
    echo.
    echo =======================================================================
    echo  [ERRO] Nao foi possivel aplicar as alteracoes no registro.
    echo =======================================================================
)

echo.
pause
