param(
    [string]$Archive = (Join-Path $PSScriptRoot '../dist/partsmith-0.2.2-pcm.zip'),
    [string]$SettingsDir,
    [string]$ThirdPartyDir,
    [string]$StageDirectory,
    [switch]$Uninstall,
    [switch]$StageOnly
)

# Uses Windows PowerShell and the embedded runtime; no customer Python or pip.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
if ([string]::IsNullOrWhiteSpace($StageDirectory)) {
    $StageDirectory = Join-Path $env:LOCALAPPDATA `
        ('PartSmith/install-staging/' + [guid]::NewGuid().ToString('N'))
}
$stage = [System.IO.Path]::GetFullPath($StageDirectory)
if (Test-Path -LiteralPath $stage) {
    throw 'Staging requires a new directory.'
}
$package = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    if ($package.Entries.Count -gt 50000) { throw 'Package file limit exceeded.' }
    $names = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )
    [long]$total = 0
    foreach ($entry in $package.Entries) {
        $name = $entry.FullName
        $invalidSegment = $name.Split('/') | Where-Object {
            $_ -eq '' -or $_ -eq '.' -or $_ -eq '..' -or
            $_ -match '[ .]$' -or $_ -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)'
        }
        if ($name -match '[\\<>:"|?*\x00-\x1f]' -or
            $name.StartsWith('/') -or $name.EndsWith('/') -or
            $invalidSegment) {
            throw 'Package contains an unsafe path.'
        }
        if (-not $names.Add($name)) { throw 'Duplicate package path.' }
        if ($entry.Length -gt 256MB) { throw 'Package member limit exceeded.' }
        $total += $entry.Length
        if ($total -gt 3GB) { throw 'Package total limit exceeded.' }
        if (($entry.ExternalAttributes -band 0xF0000000) -ne 0x80000000) {
            throw 'Package member is not a regular file.'
        }
    }
    $inventoryEntry = $package.GetEntry('plugins/inventory.json')
    if ($null -eq $inventoryEntry -or $inventoryEntry.Length -gt 16MB) {
        throw 'Package inventory is missing or oversized.'
    }
    $reader = [System.IO.StreamReader]::new($inventoryEntry.Open())
    try { $inventory = $reader.ReadToEnd() | ConvertFrom-Json }
    finally { $reader.Dispose() }
    if ($inventory.identifier -ne 'com.boardforgetools.partsmith' -or
        $inventory.schema_version -ne 'partsmith-pcm-inventory-1.0') {
        throw 'Package inventory identity differs.'
    }
    $expectedNames = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::Ordinal
    )
    foreach ($property in $inventory.files.PSObject.Properties) {
        $name = 'plugins/' + $property.Name
        [void]$expectedNames.Add($name)
        $entry = $package.GetEntry($name)
        if ($null -eq $entry -or $entry.Length -ne $property.Value.size) {
            throw 'Package file is missing or resized.'
        }
        $stream = $entry.Open()
        $hasher = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hash = [System.BitConverter]::ToString($hasher.ComputeHash($stream))
            $hash = $hash.Replace('-', '').ToLowerInvariant()
        }
        finally { $stream.Dispose(); $hasher.Dispose() }
        if ($hash -ne $property.Value.sha256) { throw 'Package file changed.' }
    }
    foreach ($name in @('plugins/inventory.json', 'metadata.json', 'resources/icon.png')) {
        [void]$expectedNames.Add($name)
    }
    if ($expectedNames.Count -ne $names.Count) { throw 'Undeclared package files.' }
    foreach ($name in $names) {
        if (-not $expectedNames.Contains($name)) { throw 'Undeclared package path.' }
    }
    # Verify every owned byte before starting any packaged executable.
    [void][System.IO.Directory]::CreateDirectory($stage)
    foreach ($entry in $package.Entries) {
        if ($entry.FullName.StartsWith('plugins/')) {
            $relative = $entry.FullName.Substring(8)
            $target = [System.IO.Path]::GetFullPath((Join-Path $stage $relative))
            if (-not $target.StartsWith($stage + '\', [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Extraction target escapes staging.'
            }
            [void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($target))
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target)
        }
    }
}
finally { $package.Dispose() }
$launcher = Join-Path $stage 'PartSmith-diagnostics.exe'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'Executable runtime is missing.'
}
if ($StageOnly) { Write-Output $stage; exit 0 }
$arguments = if ($Uninstall) { @('--uninstall') } else { @('--install-archive', $archivePath) }
if ($SettingsDir) { $arguments += @('--settings-dir', $SettingsDir) }
if ($ThirdPartyDir) { $arguments += @('--third-party-dir', $ThirdPartyDir) }
& $launcher @arguments
exit $LASTEXITCODE
