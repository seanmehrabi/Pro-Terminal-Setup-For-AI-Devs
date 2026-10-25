#Requires -Version 5.1
<#
.SYNOPSIS
  Optional AI workstation installer for Windows (feature parity with setup_ai.sh).

.DESCRIPTION
  Locates the repo root, requires Python, and runs `python -m ai` with translated flags.
  Automated installs use the shared catalog and WinGet on Windows behind the same
  planning engine as macOS/Linux (Homebrew/apt); this script does not require admin.
#>
[CmdletBinding()]
param(
    [switch]$Help,
    [switch]$List,
    [switch]$Check,
    [switch]$DryRun,
    [switch]$All,
    [string[]]$Profile,
    [switch]$Update,
    [switch]$Repair,
    [switch]$Uninstall,
    [switch]$Yes,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Remaining
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    $root = $PSScriptRoot
    if (-not $root) {
        $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    }
    return (Resolve-Path -LiteralPath $root).Path
}

function Get-PythonCommand {
    foreach ($name in @('python3', 'python')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
    }
    return $null
}

function ConvertFrom-DashArgs {
    param([string[]]$DashArgs)
    $out = @{
        Help        = $false
        List        = $false
        Check       = $false
        DryRun      = $false
        All         = $false
        Profile     = @()
        Update      = $false
        Repair      = $false
        Uninstall   = $false
        Yes         = $false
        Positionals = @()
    }
    $command = 'help'
    $i = 0
    while ($i -lt $DashArgs.Count) {
        $a = $DashArgs[$i]
        switch -Regex ($a) {
            '^(-h|--help)$' { $out.Help = $true; $i++; continue }
            '^(--list)$' { $out.List = $true; $i++; continue }
            '^(--check)$' { $out.Check = $true; $i++; continue }
            '^(--dry-run)$' { $out.DryRun = $true; $i++; continue }
            '^(--all)$' { $out.All = $true; $i++; continue }
            '^(--profile)$' {
                if ($i + 1 -ge $DashArgs.Count) { throw "Missing value for --profile" }
                $out.Profile += $DashArgs[$i + 1]
                $i += 2
                continue
            }
            '^(--update)$' { $out.Update = $true; $i++; continue }
            '^(--repair)$' { $out.Repair = $true; $i++; continue }
            '^(--uninstall)$' { $out.Uninstall = $true; $i++; continue }
            '^(--yes)$' { $out.Yes = $true; $i++; continue }
            '^(install|update|repair|uninstall|list|check|status|dry-run|help|recommend-models)$' {
                $command = $Matches[1]
                $i++
                continue
            }
            '^--' { $i++; continue }
            default {
                $out.Positionals += $a
                $i++
            }
        }
    }
    return @{ Command = $command; Opts = $out }
}

$parsed = ConvertFrom-DashArgs -DashArgs @($Remaining)
if ($Help) { $parsed.Command = 'help' }
if ($List) { $parsed.Command = 'list' }
if ($Check) { $parsed.Command = 'check' }
if ($DryRun) { $parsed.Command = 'dry-run' }
if ($Update) { $parsed.Command = 'update' }
if ($Repair) { $parsed.Command = 'repair' }
if ($Uninstall) { $parsed.Command = 'uninstall' }

$repoRoot = Get-RepoRoot
$python = Get-PythonCommand
if (-not $python) {
    Write-Error 'python3 or python is required but was not found in PATH.'
    exit 1
}

$aiArgs = @($parsed.Command)
if ($Yes -or $parsed.Opts.Yes) { $aiArgs += '--yes' }
if ($All -or $parsed.Opts.All) { $aiArgs += '--all' }
$profiles = @()
if ($Profile) { $profiles += $Profile }
if ($parsed.Opts.Profile) { $profiles += $parsed.Opts.Profile }
foreach ($p in $profiles) {
    $aiArgs += '--profile'
    $aiArgs += $p
}
$positionals = @()
if ($parsed.Opts.Positionals) { $positionals += $parsed.Opts.Positionals }
if ($positionals.Count -gt 0) { $aiArgs += $positionals }

Push-Location -LiteralPath $repoRoot
try {
    & $python -m ai @aiArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
