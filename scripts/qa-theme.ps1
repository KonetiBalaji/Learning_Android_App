# Run after qa-document-recovery.ps1; uses its disposable completed quiz account.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
function Adb {
    & $adb -s emulator-5554 @args
    if ($LASTEXITCODE -ne 0) { throw 'ADB failed' }
}
function Ui {
    Adb shell uiautomator dump /sdcard/qa-theme.xml | Out-Null
    [xml]((Adb shell cat /sdcard/qa-theme.xml) -join "`n")
}
function Tap($node) {
    if (-not $node) { throw 'Missing UI target' }
    $b = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    Adb shell input tap ([int](($b[0]+$b[2])/2)) ([int](($b[1]+$b[3])/2)) | Out-Null
    Start-Sleep -Milliseconds 900
}
function TapText($text) {
    for ($i=0; $i -lt 6; $i++) {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { Tap $node; return }
        Adb shell input swipe 540 1850 540 750 400 | Out-Null
    }
    throw "Missing text: $text"
}
function Capture($name) {
    Adb shell screencap -p /sdcard/qa-theme.png | Out-Null
    Adb pull /sdcard/qa-theme.png (Join-Path $repo "artifacts\$name.png") | Out-Null
}
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Not the QA AVD' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell am force-stop com.konetibalaji.learning | Out-Null
Adb shell am start -n com.konetibalaji.learning/.MainActivity | Out-Null
Start-Sleep -Seconds 3
TapText 'Return to learning path'
TapText 'Settings and account'
Capture 'qa-theme-light'
$switch = (Ui).SelectNodes('//node') | Where-Object checkable -eq 'true' | Select-Object -First 1
if ($switch.checked -ne 'false') { throw 'Expected light theme from document QA' }
Tap $switch
Capture 'qa-theme-dark'
Adb shell am force-stop com.konetibalaji.learning | Out-Null
Adb shell am start -n com.konetibalaji.learning/.MainActivity | Out-Null
Start-Sleep -Seconds 3
TapText 'Return to learning path'
TapText 'Settings and account'
$switch = (Ui).SelectNodes('//node') | Where-Object checkable -eq 'true' | Select-Object -First 1
if ($switch.checked -ne 'true') { throw 'Dark mode did not survive restart' }
Capture 'qa-theme-dark-restarted'
Tap $switch
Write-Output 'PASS: theme toggle persists across process restart; screenshots captured for visual inspection'
