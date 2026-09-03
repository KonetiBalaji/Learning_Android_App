param([string]$Serial = 'emulator-5554')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
function Adb {
    & $adb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw 'QA ADB failed' }
}
function Ui {
    for ($i = 0; $i -lt 3; $i++) {
        if (((Adb shell uiautomator dump /sdcard/qa-google-disabled.xml) -join '') -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-google-disabled.xml) -join "`n")
        }
    }
    throw 'No fresh UI dump'
}
function FindText([string]$text) {
    for ($i = 0; $i -lt 10; $i++) {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        Adb shell input swipe 540 1850 540 750 300 | Out-Null
    }
    throw "Missing text: $text"
}
function Tap([string]$text) {
    $node = FindText $text
    $b = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    Adb shell input tap ([int](($b[0]+$b[2])/2)) ([int](($b[1]+$b[3])/2)) | Out-Null
    Start-Sleep -Milliseconds 900
}
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Requires dedicated QA AVD' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell am force-stop com.konetibalaji.learning | Out-Null
Adb shell am start -n com.konetibalaji.learning/.MainActivity | Out-Null
Start-Sleep -Seconds 3
# Precondition: synthetic QA account on subjects, or already signed out. Never clears app data.
if ((Ui).SelectNodes('//node') | Where-Object text -eq 'What would you like to learn?') {
    Tap 'Settings and account'
    Tap 'Sign out'
}
$google = FindText 'Sign in with Google'
$button = $google
while ($button -and $button.clickable -ne 'true') { $button = $button.ParentNode }
if (-not $button -or $button.enabled -ne 'false') { throw 'Unconfigured Google control is not disabled' }
FindText 'Google sign-in is not configured for this build. Use email sign-in.' | Out-Null
Adb shell screencap -p /sdcard/qa-google-disabled.png | Out-Null
Adb pull /sdcard/qa-google-disabled.png (Join-Path $repo 'artifacts\qa-google-disabled.png') | Out-Null
Write-Output 'PASS: unconfigured Google control disabled with explanatory text; screenshot needs inspection. No live Google exchange tested.'
