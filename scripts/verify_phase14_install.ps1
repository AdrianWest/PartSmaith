param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [Parameter(Mandatory=$true)][string]$UpgradeArchive,
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [switch]$GuiSmoke
)

# Run on a disposable Windows acceptance host with KiCad closed.
$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $root) { throw 'Acceptance output must be new.' }
[void](New-Item -ItemType Directory -Path $root)
$settings = Join-Path $root 'settings'
$thirdParty = Join-Path $root 'KiCad path with spaces/3rdparty'
[void](New-Item -ItemType Directory -Path $settings)
'{"environment":{"vars":null}}' | Set-Content -LiteralPath (Join-Path $settings 'kicad_common.json')
$registry = Join-Path $settings 'installed_packages.json'
'{"unknown_setting":"preserve","packages":[{"package":{"identifier":"other.package"},"pinned":true}]}' |
    Set-Content -LiteralPath $registry
$other = Join-Path $thirdParty 'plugins/other_package'
[void](New-Item -ItemType Directory -Path $other)
$otherFile = Join-Path $other 'keep.txt'
'Unrelated original payload' | Set-Content -LiteralPath $otherFile
$otherHash = (Get-FileHash -LiteralPath $otherFile -Algorithm SHA256).Hash
$spare = Join-Path $root 'spare bundle with spaces'
& (Join-Path $PSScriptRoot 'install_production.ps1') -Archive $Archive `
    -StageDirectory $spare -StageOnly | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
$installer = Join-Path $spare 'PartSmith-diagnostics.exe'
$plugin = Join-Path $thirdParty 'plugins/com_boardforgetools_partsmith'
$launcher = Join-Path $plugin 'PartSmith-diagnostics.exe'
$env:PYTHONHOME = 'C:\nonexistent-customer-python'
$env:PYTHONPATH = 'C:\nonexistent-customer-python'
$env:PYTHONUSERBASE = 'C:\nonexistent-customer-python'
$env:PATH = Join-Path $env:SystemRoot 'System32'
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
$runs = @()
foreach ($candidate in @((Resolve-Path $Archive).Path, (Resolve-Path $UpgradeArchive).Path)) {
    $install = & $installer --install-archive $candidate --settings-dir $settings --third-party-dir $thirdParty
    if ($LASTEXITCODE -ne 0) { throw "Install rejected: $install" }
    $receipt = $install | ConvertFrom-Json
    if ($receipt.status -ne 'INSTALLED') { throw 'Installation receipt differs.' }
    $diagnostic = & $launcher --diagnostics
    if ($LASTEXITCODE -ne 0) { throw "Diagnostics failed: $diagnostic" }
    $ready = $diagnostic | ConvertFrom-Json
    if ($ready.state -ne 'READY') { throw 'Runtime is not ready.' }
    $diagnostic | Set-Content -LiteralPath (Join-Path $root ('diagnostics-' + $ready.package_version + '.json'))
    if ($GuiSmoke) {
        $guiOutput = Join-Path $root ('gui-' + $ready.package_version + '.json')
        $guiProcess = Start-Process -FilePath $launcher -ArgumentList '--gui-smoke' `
            -WindowStyle Hidden -RedirectStandardOutput $guiOutput -Wait -PassThru
        $gui = Get-Content -LiteralPath $guiOutput -Raw
        if ($guiProcess.ExitCode -ne 0 -or ($gui | ConvertFrom-Json).gui_smoke -ne 'PASS') {
            throw 'GUI launch failed.'
        }
    }
    $runs += @{version=$ready.package_version; install='PASS'; diagnostics='READY'; gui_smoke=[bool]$GuiSmoke}
}
if ($runs[0].version -eq $runs[1].version) { throw 'Upgrade requires a different version.' }
$corpus = & $launcher --self-test --output (Join-Path $root 'corpus.json')
if ($LASTEXITCODE -ne 0 -or ($corpus | ConvertFrom-Json).state -ne 'PASS') {
    throw 'Installed eight-variant corpus failed.'
}
$embeddedPython = Join-Path $plugin 'runtime/python.exe'
& $embeddedPython -I -B (Join-Path $PSScriptRoot 'verify_production_engines.py') `
    --root $plugin --output (Join-Path $root 'engines.json')
if ($LASTEXITCODE -ne 0) { throw 'Bundled PDF/OCR execution failed.' }
# Preserve the exact license bytes after independently exercising corruption.
$notice = Join-Path $plugin 'runtime/LICENSE.txt'
$original = [System.IO.File]::ReadAllBytes($notice)
try {
    [System.IO.File]::WriteAllBytes($notice, [byte[]]@(0))
    $broken = & $launcher --diagnostics
    if ($LASTEXITCODE -eq 0 -or ($broken | ConvertFrom-Json).code -ne 'BUNDLED_RUNTIME_RESOURCE_CHANGED') {
        throw 'Corrupt original notice was not rejected.'
    }
}
finally { [System.IO.File]::WriteAllBytes($notice, $original) }
$model = Join-Path $plugin 'ocr/tessdata/eng.traineddata'
$heldModel = Join-Path $root 'held-eng.traineddata'
try {
    [System.IO.File]::Move($model, $heldModel)
    $missing = & $launcher --diagnostics
    if ($LASTEXITCODE -eq 0 -or ($missing | ConvertFrom-Json).code -ne 'BUNDLED_RUNTIME_RESOURCE_MISSING') {
        throw 'Missing bundled OCR model was not rejected.'
    }
}
finally {
    if (Test-Path -LiteralPath $heldModel) { [System.IO.File]::Move($heldModel, $model) }
}
$bytecode = Join-Path $plugin 'unowned.pyc'
try {
    [System.IO.File]::WriteAllBytes($bytecode, [byte[]]@(0))
    $cached = & $launcher --diagnostics
    if ($LASTEXITCODE -eq 0 -or ($cached | ConvertFrom-Json).code -ne 'BUNDLE_BYTECODE_FORBIDDEN') {
        throw 'Unverified bytecode was not rejected before application imports.'
    }
}
finally { [System.IO.File]::Delete($bytecode) }
$removed = & $installer --uninstall --settings-dir $settings --third-party-dir $thirdParty
if ($LASTEXITCODE -ne 0 -or ($removed | ConvertFrom-Json).status -ne 'UNINSTALLED') {
    throw 'Uninstall failed.'
}
if (Test-Path -LiteralPath $plugin) { throw 'Plugin remains discoverable after uninstall.' }
$after = Get-Content -LiteralPath $registry -Raw | ConvertFrom-Json
if ($after.unknown_setting -ne 'preserve' -or $after.packages.Count -ne 1 -or
    $after.packages[0].package.identifier -ne 'other.package' -or
    (Get-FileHash -LiteralPath $otherFile -Algorithm SHA256).Hash -ne $otherHash) {
    throw 'Unrelated package or registration changed.'
}
@{schema_version='partsmith-install-acceptance-1.0'; state='PASS';
    scope='isolated-profile runtime acceptance; clean-host provenance is separate';
    runs=$runs; corpus='PASS'; engines='PASS'; corrupted_notice='REJECTED'; missing_model='REJECTED'; untracked_bytecode='REJECTED'; uninstall='PASS';
    unrelated_package='UNCHANGED'; python_environment='BLOCKED'} |
    ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $root 'acceptance.json')
