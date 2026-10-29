param([switch]$ConnectedTests)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (-not $env:JAVA_HOME) {
    $jdk = Get-ChildItem (Join-Path $root 'work\toolchain\jdk') -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($jdk) { $env:JAVA_HOME = $jdk.FullName }
}
if (-not $env:ANDROID_HOME -and (Test-Path (Join-Path $root 'work\toolchain\sdk'))) {
    $env:ANDROID_HOME = Join-Path $root 'work\toolchain\sdk'
}
if (-not $env:JAVA_HOME) { throw 'Install JDK 17 and set JAVA_HOME, or use Android Studio.' }
if (-not $env:ANDROID_HOME) { throw 'Install Android SDK 35 and set ANDROID_HOME, or use Android Studio.' }
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
Push-Location (Join-Path $root 'android')
try {
    $tasks = @('assembleDebug', 'testDebugUnitTest', 'lintDebug', '--console', 'plain')
    if ($ConnectedTests) { $tasks += 'connectedDebugAndroidTest' }
    & .\gradlew.bat @tasks
    if ($LASTEXITCODE -ne 0) { throw 'Android checks failed.' }
} finally { Pop-Location }
