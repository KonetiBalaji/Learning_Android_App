param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$BackendUrl,
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 2100000000)]
    [int]$VersionCode,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?$')]
    [string]$VersionName,
    [string]$OutputDirectory = 'artifacts\private-release',
    [string]$SigningProfile = (Join-Path $env:USERPROFILE '.learnsmart\release\signing-profile.clixml')
)
$ErrorActionPreference = 'Stop'
$profileVariablesSet = @()
try {
$repo = Split-Path $PSScriptRoot -Parent
$output = [IO.Path]::GetFullPath((Join-Path $repo $OutputDirectory))
$artifactRoot = [IO.Path]::GetFullPath((Join-Path $repo 'artifacts'))
if (-not $output.StartsWith($artifactRoot + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputDirectory must stay inside this repository artifacts directory.'
}
$required = @(
    'LEARN_SMART_RELEASE_STORE_FILE',
    'LEARN_SMART_RELEASE_STORE_PASSWORD',
    'LEARN_SMART_RELEASE_KEY_ALIAS',
    'LEARN_SMART_RELEASE_KEY_PASSWORD'
)
$missing = @($required | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_)) })
if ($missing.Count -and (Test-Path -LiteralPath $SigningProfile -PathType Leaf)) {
    $profile = Import-Clixml -LiteralPath $SigningProfile
    $profileFields = @{
        LEARN_SMART_RELEASE_STORE_FILE = $profile.StoreFile
        LEARN_SMART_RELEASE_KEY_ALIAS = $profile.KeyAlias
    }
    foreach ($name in $profileFields.Keys) {
        if ([string]::IsNullOrWhiteSpace([string]$profileFields[$name])) {
            throw "Signing profile is missing $name."
        }
        [Environment]::SetEnvironmentVariable($name, [string]$profileFields[$name], 'Process')
        $profileVariablesSet += $name
    }
    foreach ($entry in @(
        @{ Name = 'LEARN_SMART_RELEASE_STORE_PASSWORD'; Value = $profile.StorePassword },
        @{ Name = 'LEARN_SMART_RELEASE_KEY_PASSWORD'; Value = $profile.KeyPassword }
    )) {
        if ($entry.Value -isnot [Security.SecureString]) {
            throw "Signing profile is missing $($entry.Name)."
        }
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($entry.Value)
        try {
            [Environment]::SetEnvironmentVariable(
                $entry.Name,
                [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer),
                'Process')
            $profileVariablesSet += $entry.Name
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        }
    }
    $missing = @($required | Where-Object { [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($_)) })
}
if ($missing.Count) { throw "Missing release signing environment: $($missing -join ', ')" }
$store = [IO.Path]::GetFullPath([Environment]::GetEnvironmentVariable('LEARN_SMART_RELEASE_STORE_FILE'))
if (-not (Test-Path -LiteralPath $store -PathType Leaf)) { throw 'Release keystore file does not exist.' }
$commit = (git -C $repo rev-parse HEAD) -join ''
$dirty = (git -C $repo status --porcelain --untracked-files=no) -join ''
if ($dirty) { throw 'Refusing to build a candidate from a modified tracked worktree.' }
$existingManifest = Join-Path $output 'candidate-manifest.json'
if (Test-Path -LiteralPath $existingManifest -PathType Leaf) {
    try { $previous = Get-Content -LiteralPath $existingManifest -Raw | ConvertFrom-Json }
    catch { throw 'Existing candidate manifest is unreadable; preserve or remove it deliberately before rebuilding.' }
    if ($previous.version_code -isnot [ValueType] -or [long]$previous.version_code -lt 1 -or $VersionCode -le [long]$previous.version_code) {
        throw "VersionCode must increase beyond the existing candidate value $($previous.version_code)."
    }
}

Push-Location (Join-Path $repo 'android')
try {
    & .\gradlew.bat clean assembleRelease "-PreleaseApiBaseUrl=$BackendUrl" "-PreleaseVersionCode=$VersionCode" "-PreleaseVersionName=$VersionName"
    if ($LASTEXITCODE -ne 0) { throw 'Release APK build failed.' }
} finally { Pop-Location }

$source = Join-Path $repo 'android\app\build\outputs\apk\release\app-release.apk'
if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw 'Signed release APK was not produced.' }
New-Item -ItemType Directory -Force -Path $output | Out-Null
$destination = Join-Path $output 'learn-smart-private-release.apk'
Copy-Item -LiteralPath $source -Destination $destination -Force
$sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk\build-tools'
$apksigner = Get-ChildItem -LiteralPath $sdk -Directory | Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName 'apksigner.bat' } | Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $apksigner) { throw 'Android apksigner was not found.' }
$verification = (& $apksigner verify --verbose --print-certs $destination 2>&1) -join "`n"
if ($LASTEXITCODE -ne 0 -or $verification -notmatch 'Verified') { throw 'APK signature verification failed.' }
$certificate = ([regex]::Match($verification, '(?:Signer #1|V2 Signer): certificate SHA-256 digest: ([0-9a-f]+)',
    [Text.RegularExpressions.RegexOptions]::IgnoreCase)).Groups[1].Value.ToLowerInvariant()
if (-not $certificate) { throw 'APK signing certificate digest was unavailable.' }
$hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
$aapt = Get-ChildItem -LiteralPath $sdk -Directory | Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName 'aapt2.exe' } | Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $aapt) { throw 'Android aapt2 was not found.' }
$badging = (& $aapt dump badging $destination 2>&1) -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'APK package metadata could not be read.' }
$package = [regex]::Match($badging, "package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']+)'" )
if (-not $package.Success -or $package.Groups[1].Value -ne 'com.konetibalaji.learning') {
    throw 'APK package identity or version metadata is invalid.'
}
if ([int]$package.Groups[2].Value -ne $VersionCode -or $package.Groups[3].Value -ne $VersionName) {
    throw 'APK version metadata does not match the requested release identity.'
}
$manifest = [ordered]@{
    product = 'Learn Smart AI'
    distribution = 'private APK'
    git_commit = $commit
    version_name = $package.Groups[3].Value
    version_code = [int]$package.Groups[2].Value
    backend_url = $BackendUrl.TrimEnd('/')
    apk_file = [IO.Path]::GetFileName($destination)
    apk_sha256 = $hash
    signing_certificate_sha256 = $certificate
    built_at_utc = [DateTime]::UtcNow.ToString('o')
    production_verified = $false
    uat_accepted = $false
}
$manifestPath = Join-Path $output 'candidate-manifest.json'
$manifest | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Output "APK=$destination"
Write-Output "MANIFEST=$manifestPath"
Write-Output "SHA256=$hash"
Write-Output "CERTIFICATE_SHA256=$certificate"
} finally {
    foreach ($name in $profileVariablesSet) {
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
}
