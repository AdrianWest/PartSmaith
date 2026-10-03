param(
    [string]$Version = "10.0.5"
)

$ErrorActionPreference = "Stop"
$cli = "C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"

if (-not (Test-Path -LiteralPath $cli)) {
    winget install --id KiCad.KiCad --version $Version --exact `
        --source winget --silent --accept-package-agreements `
        --accept-source-agreements
}

if (-not (Test-Path -LiteralPath $cli)) {
    throw "KiCad CLI was not installed at the required location: $cli"
}

$installedVersion = (& $cli version).Trim()
if ($installedVersion -ne $Version) {
    throw "KiCad $Version is required; found $installedVersion"
}

Write-Output "KiCad $installedVersion is ready at $cli"
