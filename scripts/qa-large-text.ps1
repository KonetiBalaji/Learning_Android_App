param([string]$Serial = 'emulator-5554')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw 'QA ADB command failed' }
}
function Ui {
    for ($i = 0; $i -lt 3; $i++) {
        $result = (Adb shell uiautomator dump /sdcard/qa-large-text.xml) -join "`n"
        if ($result -match 'dumped to') { return [xml]((Adb shell cat /sdcard/qa-large-text.xml) -join "`n") }
    }
    throw 'Fresh UI dump unavailable'
}
function FindText([string]$text) {
    for ($i = 0; $i -lt 20; $i++) {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        if ($i -lt 10) { Adb shell input swipe 540 1850 540 750 300 | Out-Null }
        else { Adb shell input swipe 540 750 540 1850 300 | Out-Null }
    }
    throw "Text not reachable: $text"
}
function Tap([string]$text) {
    $node = FindText $text
    $bounds = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    Adb shell input tap ([int](($bounds[0]+$bounds[2])/2)) ([int](($bounds[1]+$bounds[3])/2)) | Out-Null
    Start-Sleep -Milliseconds 900
}
function Capture([string]$name) {
    Adb shell screencap -p "/sdcard/$name.png" | Out-Null
    Adb pull "/sdcard/$name.png" (Join-Path $repo "artifacts\$name.png") | Out-Null
}
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Not the dedicated QA emulator' }
$originalScale = ((Adb shell settings get system font_scale) -join '').Trim()
if ($originalScale -ne 'null' -and $originalScale -notmatch '^\d+(\.\d+)?$') { throw 'Unexpected original font scale' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
try {
    Adb shell settings put system font_scale 2.0 | Out-Null
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
    # Prerequisite: synthetic QA account at completed quiz, study home or subjects.
    $initial = Ui
    if ($initial.SelectNodes('//node') | Where-Object text -eq 'Session complete') { Tap 'Study another document' }
    if (-not ((Ui).SelectNodes('//node') | Where-Object text -eq 'What would you like to learn?')) { Tap '‹ Back to learning path' }
    FindText 'What would you like to learn?' | Out-Null
    FindText 'Mathematics' | Out-Null
    Capture 'qa-large-text-subjects'
    FindText 'View parent & teacher progress' | Out-Null
    Capture 'qa-large-text-parent-button'
    Tap 'Settings and account'
    Tap 'Change grade · 8'
    FindText "Grade`n8" | Out-Null
    Capture 'qa-large-text-grades'
    Tap "Grade`n8"
    FindText 'What would you like to learn?' | Out-Null
    Write-Output 'PASS: 200% font allows subject/parent controls and Grade 8 navigation; screenshots need visual inspection'
} finally {
    if ($originalScale -eq 'null') { Adb shell settings delete system font_scale | Out-Null }
    else { Adb shell settings put system font_scale $originalScale | Out-Null }
    if (((Adb shell settings get system font_scale) -join '').Trim() -ne $originalScale) { throw 'Font scale restoration failed' }
    Write-Output 'Restored original QA emulator font scale'
}
