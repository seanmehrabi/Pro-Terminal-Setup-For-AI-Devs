#Requires -Version 5.1
<#
.SYNOPSIS
  Professional terminal bootstrap for Windows PowerShell 7+.

.DESCRIPTION
  Installs Oh My Posh, useful modules/tools, a Nerd Font, and an idempotent
  profile block with modern defaults for AI/dev workflows.
#>
[CmdletBinding()]
param(
    [switch]$SkipTools,
    [switch]$SkipFont
)

$ErrorActionPreference = 'Stop'
$MarkerBegin = '# >>> pro-terminal-setup >>>'
$MarkerEnd   = '# <<< pro-terminal-setup <<<'
$NerdFontsVersion = 'v3.3.0'

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Green
}

function Write-WarnStep {
    param([string]$Message)
    Write-Host "!!  $Message" -ForegroundColor Yellow
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = @($machine, $user) -join ';'
}

function Test-WingetPackageInstalled {
    param([Parameter(Mandatory)][string]$Id)
    $null = winget list --id $Id --accept-source-agreements 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Install-WingetPackage {
    param(
        [Parameter(Mandatory)][string]$Id,
        [string]$Source = 'winget'
    )
    if (Test-WingetPackageInstalled -Id $Id) {
        Write-Step "$Id already installed."
        return
    }
    Write-Step "Installing $Id..."
    winget install --id $Id -e --source $Source `
        --accept-package-agreements --accept-source-agreements
    Refresh-Path
}

function Install-PsModule {
    param([Parameter(Mandatory)][string]$Name)
    if (Get-Module -ListAvailable -Name $Name) {
        Write-Step "Module $Name already installed."
        return
    }
    Write-Step "Installing module $Name..."
    Install-Module -Name $Name -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop
}

function Backup-Profile {
    param([Parameter(Mandatory)][string]$Path)
    if (Test-Path -LiteralPath $Path) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $backup = "$Path.bak.$stamp"
        Copy-Item -LiteralPath $Path -Destination $backup -Force
        Write-Step "Backed up profile -> $backup"
    }
}

function Install-MesloFont {
    $fontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
    $registryPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
    $fontFileName = 'MesloLGSNerdFont-Regular.ttf'
    $destFont = Join-Path $fontDir $fontFileName

    if (Test-Path -LiteralPath $destFont) {
        Write-Step 'Meslo Nerd Font already present.'
        return
    }

    # Prefer Oh My Posh's font installer when available (non-interactive best-effort).
    if (Get-Command oh-my-posh -ErrorAction SilentlyContinue) {
        Write-Step 'Attempting Oh My Posh font install (meslo)...'
        try {
            & oh-my-posh font install meslo --user 2>$null
            if (Test-Path -LiteralPath $destFont) { return }
        } catch {
            Write-WarnStep 'oh-my-posh font install was not available; falling back to direct download.'
        }
    }

    Write-Step "Downloading Meslo Nerd Font ($NerdFontsVersion)..."
    New-Item -ItemType Directory -Path $fontDir -Force | Out-Null
    $zip = Join-Path $env:TEMP 'MesloNerdFont.zip'
    $extract = Join-Path $env:TEMP 'MesloNerdFont'
    $uri = "https://github.com/ryanoasis/nerd-fonts/releases/download/$NerdFontsVersion/Meslo.zip"

    Invoke-WebRequest -Uri $uri -OutFile $zip -UseBasicParsing
    if (Test-Path -LiteralPath $extract) {
        Remove-Item -LiteralPath $extract -Recurse -Force
    }
    Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force

    $ttfFiles = Get-ChildItem -Path $extract -Filter '*.ttf' -Recurse |
        Where-Object { $_.Name -notmatch 'Windows Compatible' }

    if (-not $ttfFiles) {
        throw 'No Meslo TTF files found in the downloaded archive.'
    }

    if (-not (Test-Path -LiteralPath $registryPath)) {
        New-Item -Path $registryPath -Force | Out-Null
    }

    foreach ($font in $ttfFiles) {
        $target = Join-Path $fontDir $font.Name
        Copy-Item -LiteralPath $font.FullName -Destination $target -Force
        $displayName = ($font.BaseName -replace 'NerdFont', ' Nerd Font') + ' (TrueType)'
        New-ItemProperty -Path $registryPath -Name $displayName -Value $font.Name -PropertyType String -Force | Out-Null
    }

    Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue
    Write-Step 'Meslo Nerd Font installed for the current user. Restart the terminal to pick it up.'
}

function Set-ManagedProfileBlock {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType File -Path $Path -Force | Out-Null
    }

    $existing = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue
    if ($null -eq $existing) { $existing = '' }

    if ($existing -match [regex]::Escape($MarkerBegin)) {
        $pattern = '(?s)' + [regex]::Escape($MarkerBegin) + '.*?' + [regex]::Escape($MarkerEnd) + '\r?\n?'
        $existing = [regex]::Replace($existing, $pattern, '')
    }

    $block = @"
$MarkerBegin
# Managed by Pro-Terminal-Setup-For-AI-Devs — safe to re-run the installer.

# Oh My Posh: use theme name (POSH_THEMES_PATH is no longer reliable with MSIX installs)
oh-my-posh init pwsh --config paradox | Invoke-Expression

Import-Module PSReadLine -ErrorAction SilentlyContinue
Import-Module Terminal-Icons -ErrorAction SilentlyContinue

# Predictive IntelliSense + comfortable editing
try {
    Set-PSReadLineOption -PredictionSource HistoryAndPlugin -ErrorAction Stop
    Set-PSReadLineOption -PredictionViewStyle ListView -ErrorAction SilentlyContinue
    Set-PSReadLineOption -EditMode Windows
    Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete
} catch { }

# Modern CLI helpers (functions so arguments work).
# Avoid clobbering built-in aliases: gc=Get-Content, gp=Get-ItemProperty, gl=Get-Location.
function ll { Get-ChildItem -Force @args }
function la { Get-ChildItem -Force @args }
function gs { git status -sb @args }
function ga { git add @args }
function gcm { git commit @args }
function gpush { git push @args }
function glog { git log --oneline --graph --decorate -20 @args }
function gdiff { git diff @args }

if (Get-Command eza -ErrorAction SilentlyContinue) {
    function ls { eza --group-directories-first --icons=auto @args }
    function ll { eza -lah --group-directories-first --git --icons=auto @args }
}
if (Get-Command bat -ErrorAction SilentlyContinue) {
    function cat { bat --paging=never @args }
}
if (Get-Command rg -ErrorAction SilentlyContinue) {
    Set-Alias -Name grep -Value rg -Scope Global -Force -ErrorAction SilentlyContinue
}
if (Get-Command zoxide -ErrorAction SilentlyContinue) {
    Invoke-Expression (& { (zoxide init powershell | Out-String) })
}

# Machine-local overrides
`$localProfile = Join-Path `$HOME 'Documents\PowerShell\Microsoft.PowerShell_profile.local.ps1'
if (Test-Path -LiteralPath `$localProfile) { . `$localProfile }
$MarkerEnd
"@

    $trimmed = $existing.TrimEnd()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        Set-Content -LiteralPath $Path -Value ($block + "`r`n") -Encoding UTF8
    } else {
        Set-Content -LiteralPath $Path -Value ($trimmed + "`r`n`r`n" + $block + "`r`n") -Encoding UTF8
    }
}

function Install-DevTools {
    $tools = @(
        'Git.Git',
        'BurntSushi.ripgrep.MSVC',
        'sharkdp.fd',
        'junegunn.fzf',
        'ajeetdsouza.zoxide',
        'jqlang.jq',
        'eza-community.eza',
        'sharkdp.bat',
        'dandavison.delta',
        'GitHub.cli'
    )

    foreach ($id in $tools) {
        try {
            Install-WingetPackage -Id $id
        } catch {
            Write-WarnStep "Failed to install $id : $($_.Exception.Message)"
        }
    }
}

# --- main ---
Write-Step 'Starting professional terminal setup (Windows)...'
if (Test-IsAdmin) {
    Write-Step 'Running elevated (optional; CurrentUser installs do not require admin).'
} else {
    Write-WarnStep 'Not elevated. Continuing with CurrentUser / user-scope installs.'
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is required. Install App Installer from the Microsoft Store, then re-run.'
}

if ($PSVersionTable.PSVersion.Major -lt 7) {
    Install-WingetPackage -Id 'Microsoft.PowerShell'
    Write-WarnStep 'PowerShell 7 was installed. Re-run this script from pwsh.exe to finish setup.'
    exit 0
}

Install-WingetPackage -Id 'JanDeDobbeleer.OhMyPosh'
Refresh-Path

foreach ($module in @('PSReadLine', 'Terminal-Icons')) {
    Install-PsModule -Name $module
}

if (-not $SkipTools) {
    Install-DevTools
    Refresh-Path
}

if (-not $SkipFont) {
    try {
        Install-MesloFont
    } catch {
        Write-WarnStep "Font install failed: $($_.Exception.Message)"
        Write-WarnStep "You can install later with: oh-my-posh font install meslo"
    }
}

# Prefer PowerShell 7 profile path
$profilePath = $PROFILE.CurrentUserCurrentHost
if (-not $profilePath) { $profilePath = $PROFILE }

Backup-Profile -Path $profilePath
Write-Step "Updating profile: $profilePath"
Set-ManagedProfileBlock -Path $profilePath

Write-Host ''
Write-Host 'Setup complete.' -ForegroundColor Green
Write-Host ''
Write-Host 'Next steps:'
Write-Host '  1. Restart Windows Terminal / PowerShell'
Write-Host '  2. Set the font to "MesloLGS Nerd Font" (or MesloLGS NF)'
Write-Host '  3. Optional: oh-my-posh config export --output ~\.mytheme.omp.json'
Write-Host ''
Write-Host 'Tips for AI/dev workflows:'
Write-Host '  - Use rg / fd / fzf for search; zoxide (z) for project jumping'
Write-Host '  - Put machine-only config in Documents\PowerShell\Microsoft.PowerShell_profile.local.ps1'
Write-Host '  - Install CLI agents separately (claude, codex) as needed'
Write-Host ''
