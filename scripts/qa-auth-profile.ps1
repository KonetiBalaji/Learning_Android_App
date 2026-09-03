$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s emulator-5554 @args
    if ($LASTEXITCODE -ne 0) { throw 'QA ADB failed' }
}
function Ui {
    for ($i=0; $i -lt 3; $i++) {
        if (((Adb shell uiautomator dump /sdcard/qa-auth-profile.xml) -join '') -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-auth-profile.xml) -join "`n")
        }
    }
    throw 'No fresh UI dump'
}
function FindText([string]$text) {
    for ($i=0; $i -lt 12; $i++) {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        if ($i -lt 6) { Adb shell input swipe 540 1850 540 750 300 | Out-Null }
        else { Adb shell input swipe 540 750 540 1850 300 | Out-Null }
    }
    throw "Missing text: $text"
}
function TapNode($node) {
    $b = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    Adb shell input tap ([int](($b[0]+$b[2])/2)) ([int](($b[1]+$b[3])/2)) | Out-Null
    Start-Sleep -Milliseconds 700
}
function Tap([string]$text) { TapNode (FindText $text) }
function EnterField([int]$index, [string]$value) {
    Adb shell input swipe 540 750 540 1850 300 | Out-Null
    $fields = @((Ui).SelectNodes('//node') | Where-Object class -eq 'android.widget.EditText')
    if ($fields.Count -ne 2) { throw 'Expected exactly two sign-in fields' }
    TapNode $fields[$index]
    Adb shell input keyevent KEYCODE_MOVE_END | Out-Null
    Adb shell input keycombination KEYCODE_CTRL_LEFT KEYCODE_A | Out-Null
    Adb shell input text $value | Out-Null
    Adb shell input keyevent 4 | Out-Null
}
function Restart {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Dedicated QA AVD required' }
if ((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider -notin @('deterministic','scripted-qa')) { throw 'Isolated QA backend required' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Restart
# Precondition: already signed out. No app data is cleared.
Tap 'New student? Create a private account'
$email = 'Profile-' + [Guid]::NewGuid().ToString('N') + '@EXAMPLE.COM'
EnterField 0 $email
EnterField 1 'qa-password-long-enough'
Tap 'Create account'
Tap "Grade`n8"
Tap 'Settings and account'
FindText $email.ToLowerInvariant() | Out-Null
Tap 'Sign out'
EnterField 0 $email
EnterField 1 'wrong-password-long-enough'
Tap 'Sign in'
FindText 'Email or password is incorrect. Please try again.' | Out-Null
Tap 'Try again'
EnterField 1 'qa-password-long-enough'
Tap 'Sign in'
Tap "Grade`n8"
Restart
Tap 'Settings and account'
FindText $email.ToLowerInvariant() | Out-Null
Adb shell screencap -p /sdcard/qa-auth-profile.png | Out-Null
Adb pull /sdcard/qa-auth-profile.png (Join-Path $repo 'artifacts\qa-auth-profile.png') | Out-Null
Write-Output 'PASS: registration and password login use normalized server identity; wrong-password recovery and persisted-session restart pass. No live AI call.'
