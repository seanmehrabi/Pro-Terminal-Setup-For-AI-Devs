# Requires -Version 5.1
param()

function Ensure-Admin {
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
        Write-Warning "Please run this script as Administrator."
        exit 1
    }
}

function Install-WingetPackage {
    param(
        [string]$Id
    )
    if (-not (winget list --id $Id | Out-Null 2>&1)) {
        winget install --id $Id -e --accept-package-agreements --accept-source-agreements
    }
}

Ensure-Admin

if ($PSVersionTable.PSVersion.Major -lt 7) {
    Install-WingetPackage -Id 'Microsoft.PowerShell'
}

if (-not (Get-Command oh-my-posh -ErrorAction SilentlyContinue)) {
    Install-WingetPackage -Id 'JanDeDobbeleer.OhMyPosh'
}

$modules = @('PSReadLine','Terminal-Icons')
foreach ($m in $modules) {
    if (-not (Get-Module -ListAvailable -Name $m)) {
        Install-Module $m -Scope CurrentUser -Force -ErrorAction Stop
    }
}

$fontDir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$fontFile = Join-Path $fontDir 'MesloLGS NF Regular.ttf'
if (-not (Test-Path $fontFile)) {
    $zip = Join-Path $env:TEMP 'Meslo.zip'
    Invoke-WebRequest -Uri 'https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/Meslo.zip' -OutFile $zip -UseBasicParsing
    $tempExtract = Join-Path $env:TEMP 'MesloFonts'
    Expand-Archive $zip -DestinationPath $tempExtract -Force
    Get-ChildItem -Path $tempExtract -Filter '*.ttf' | ForEach-Object {
        Copy-Item $_.FullName -Destination $fontDir -Force
    }
    Remove-Item $zip -Force
    Remove-Item $tempExtract -Recurse -Force
}

if (-not (Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

$profileContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
$lines = @(
    "oh-my-posh init pwsh --config \"$(Join-Path $env:POSH_THEMES_PATH 'paradox.omp.json')\" | Invoke-Expression",
    'Import-Module PSReadLine',
    'Import-Module Terminal-Icons',
    'Set-Alias ll Get-ChildItem',
    'Set-Alias gs git status'
)
foreach ($line in $lines) {
    if ($profileContent -notmatch [regex]::Escape($line)) {
        Add-Content -Path $PROFILE -Value $line
    }
}

Write-Host "\nTerminal setup complete! Please restart PowerShell and set the font to 'MesloLGS NF'." -ForegroundColor Green
