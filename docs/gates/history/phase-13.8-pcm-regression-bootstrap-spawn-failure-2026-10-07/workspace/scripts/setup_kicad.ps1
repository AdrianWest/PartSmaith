param(
    [string]$Version = "10.0.6",
    [switch]$AddToGitHubEnvironment
)

$ErrorActionPreference = "Stop"

function Find-KiCadCli([string]$RequiredVersion) {
    $candidates = @()
    $command = Get-Command kicad-cli.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        $candidates += $command.Source
    }

    $roots = @(
        (Join-Path $env:ProgramFiles "KiCad"),
        (Join-Path $env:LOCALAPPDATA "Programs\KiCad")
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }
        $candidates += Get-ChildItem -LiteralPath $root `
            -Filter kicad-cli.exe `
            -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName |
            Select-Object -ExpandProperty FullName
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        try {
            if ((& $candidate version).Trim() -eq $RequiredVersion) {
                return $candidate
            }
        }
        catch {
            continue
        }
    }
    return $null
}

$cli = Find-KiCadCli $Version
if ($null -eq $cli) {
    winget install --id KiCad.KiCad --version $Version --exact `
        --source winget --silent --accept-package-agreements `
        --accept-source-agreements
    $cli = Find-KiCadCli $Version
}

if ($null -eq $cli) {
    throw "KiCad CLI was not found after installing KiCad $Version"
}

$installedVersion = (& $cli version).Trim()
if ($installedVersion -ne $Version) {
    throw "KiCad $Version is required; found $installedVersion"
}

if ($AddToGitHubEnvironment) {
    if ([string]::IsNullOrWhiteSpace($env:GITHUB_ENV)) {
        throw "GITHUB_ENV is required when AddToGitHubEnvironment is set"
    }
    [System.IO.File]::AppendAllText(
        $env:GITHUB_ENV,
        "PARTSMITH_KICAD_CLI=$cli`n",
        [System.Text.UTF8Encoding]::new($false)
    )
}

Write-Output "KiCad $installedVersion is ready at $cli"
