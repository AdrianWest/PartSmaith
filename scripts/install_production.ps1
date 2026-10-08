param(
    [string]$Archive = (Join-Path $PSScriptRoot '../dist/partsmith-0.3.2-pcm.zip'),
    [string]$Python = (Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'),
    [string]$SettingsDir,
    [string]$ThirdPartyDir,
    [switch]$Uninstall,
    [switch]$DryRun
)

# Repository helper. Customer installation uses KiCad PCM and online preparation.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw 'A prepared Python 3.11 or 3.12 project environment is required. Customers use KiCad PCM.'
}
$arguments = @((Join-Path $PSScriptRoot 'install_kicad.py'), '--no-pause')
if ($Uninstall) { $arguments += '--uninstall' }
else { $arguments += @('--archive', $Archive) }
if ($SettingsDir) { $arguments += @('--settings-dir', $SettingsDir) }
if ($ThirdPartyDir) { $arguments += @('--third-party-dir', $ThirdPartyDir) }
if ($DryRun) { $arguments += '--dry-run' }
& $Python @arguments
exit $LASTEXITCODE
