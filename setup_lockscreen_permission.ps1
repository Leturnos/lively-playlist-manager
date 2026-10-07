# setup_lockscreen_permission.ps1
# Configura permissoes seguras (Principio do Menor Privilegio) para o Lively Wallpaper
# sincroniza a tela de bloqueio do Windows com carregamento ultra rapido no boot.

param (
    [string]$TargetUserName = ""
)

# 1. Verificacao de privilegios de Administrador (Auto-elevacao)
$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)

if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    # Detecta o usuario interativo original antes de acionar o prompt UAC
    $detectedUser = $TargetUserName
    if (-not $detectedUser) {
        try {
            $cimUser = (Get-CimInstance Win32_ComputerSystem -ErrorAction Stop).UserName
            if ($cimUser) { $detectedUser = $cimUser }
        } catch {}
    }
    if (-not $detectedUser -and $env:USERNAME) {
        $detectedUser = if ($env:USERDOMAIN) { "$($env:USERDOMAIN)\$($env:USERNAME)" } else { $env:USERNAME }
    }
    if (-not $detectedUser) {
        $detectedUser = $currentIdentity.Name
    }

    try {
        Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -TargetUserName `"$detectedUser`"" -Verb RunAs
        exit 0
    } catch {
        Write-Host "Execucao cancelada ou negada pelo usuario." -ForegroundColor Yellow
        $null = Read-Host "Pressione Enter para sair..."
        exit 1
    }
}

try {
    $Host.UI.RawUI.WindowTitle = "Configuracao de Permissao - Tela de Bloqueio Lively"
} catch {}

Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "     LIVELY PLAYLIST MANAGER - ATIVACAO DE TELA DE BLOQUEIO            " -ForegroundColor Cyan
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configurando permissoes de menor privilegio para o usuario ativo..." -ForegroundColor Yellow

$ErrorActionPreference = 'Stop'
$hasError = $false

try {
    # 2. Identificar conta de usuario alvo
    $target = $TargetUserName
    if (-not $target) {
        try {
            $cimUser = (Get-CimInstance Win32_ComputerSystem -ErrorAction Stop).UserName
            if ($cimUser) { $target = $cimUser }
        } catch {}
    }
    if (-not $target -and $env:USERNAME) {
        $target = if ($env:USERDOMAIN) { "$($env:USERDOMAIN)\$($env:USERNAME)" } else { $env:USERNAME }
    }
    if (-not $target) {
        $target = $currentIdentity.Name
    }

    $userAccount = if ($target -match '^S-1-\d+') {
        New-Object System.Security.Principal.SecurityIdentifier($target)
    } else {
        New-Object System.Security.Principal.NTAccount($target)
    }

    Write-Host "[1/4] Usuario identificado: $($userAccount.Value)" -ForegroundColor Gray

    # 3. Chave de Registro: HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP
    # Permissao minima: SetValue, CreateSubKey, ReadKey (sem FullControl)
    $cspPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP'
    if (-not (Test-Path $cspPath)) {
        New-Item -Path $cspPath -Force | Out-Null
    }
    $acl = Get-Acl $cspPath

    # Limpa regra legada explicita de BUILTIN\Users (S-1-5-32-545) gerada por versoes antigas
    $legacyUsersSid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-545')
    $acl.PurgeAccessRules($legacyUsersSid)

    $regRights = [System.Security.AccessControl.RegistryRights]'SetValue, CreateSubKey, ReadKey'
    $regRule = New-Object System.Security.AccessControl.RegistryAccessRule(
        $userAccount,
        $regRights,
        'ContainerInherit,ObjectInherit',
        'None',
        'Allow'
    )
    $acl.AddAccessRule($regRule)
    Set-Acl $cspPath $acl
    Write-Host "[2/4] Registro PersonalizationCSP configurado com sucesso." -ForegroundColor Gray

    # 4. Limpeza preventiva de chave legada de GPO (evita timeouts no servico gpsvc)
    $polPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Personalization'
    if (Test-Path $polPath) {
        Remove-ItemProperty -Path $polPath -Name 'LockScreenImage' -ErrorAction SilentlyContinue
    }
    Write-Host "[3/4] Politicas legadas de GPO verificadas/limpas." -ForegroundColor Gray

    # 5. Diretorio de Sistema: C:\ProgramData\LivelyPlaylistManager\Lockscreen
    # Permissao minima: Modify (leitura, gravacao e exclusao para slots A/B sem FullControl)
    $programData = [System.Environment]::GetFolderPath('CommonApplicationData')
    if (-not $programData) { $programData = 'C:\ProgramData' }
    $livelyDir = Join-Path $programData 'LivelyPlaylistManager'
    $lockDir = Join-Path $livelyDir 'Lockscreen'

    if (-not (Test-Path $lockDir)) {
        New-Item -ItemType Directory -Path $lockDir -Force | Out-Null
    }

    $fileRights = [System.Security.AccessControl.FileSystemRights]'Modify'
    $fileRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $userAccount,
        $fileRights,
        'ContainerInherit,ObjectInherit',
        'None',
        'Allow'
    )

    foreach ($dir in @($livelyDir, $lockDir)) {
        $fileAcl = Get-Acl $dir
        # Limpa regra legada explicita de BUILTIN\Users
        $fileAcl.PurgeAccessRules($legacyUsersSid)
        $fileAcl.AddAccessRule($fileRule)
        Set-Acl $dir $fileAcl
    }
    Write-Host "[4/4] Permissao de modificacao aplicada em C:\ProgramData." -ForegroundColor Gray

    Write-Host ""
    Write-Host "=======================================================================" -ForegroundColor Green
    Write-Host " [SUCESSO] Configuracao concluida com exito para: $($userAccount.Value)" -ForegroundColor Green
    Write-Host " Agora voce pode ativar 'Sincronizar Tela de Bloqueio' no menu" -ForegroundColor Green
    Write-Host " da bandeja do sistema (proximo ao relogio, abaixo de Fundo)." -ForegroundColor Green
    Write-Host "=======================================================================" -ForegroundColor Green
} catch {
    $hasError = $true
    Write-Host ""
    Write-Host "=======================================================================" -ForegroundColor Red
    Write-Host " [ERRO] Falha ao configurar permissoes: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "=======================================================================" -ForegroundColor Red
}

Write-Host ""
$null = Read-Host "Pressione Enter para fechar..."

if ($hasError) {
    exit 1
} else {
    exit 0
}
