param([switch]$ResetTestAppData)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s emulator-5554 @args
    if ($LASTEXITCODE -ne 0) { throw 'ADB failed' }
}
function Ui {
    Adb shell uiautomator dump /sdcard/qa-interests.xml | Out-Null
    [xml]((Adb shell cat /sdcard/qa-interests.xml) -join "`n")
}
function Center($node) {
    $b = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($b[0]+$b[2])/2), [int](($b[1]+$b[3])/2))
}
function TextNode($text) {
    for ($i=0; $i -lt 6; $i++) {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        Adb shell input swipe 540 1850 540 750 400 | Out-Null
    }
    throw "Missing text: $text"
}
function TapText($text) {
    $point = Center (TextNode $text)
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 900
}
function EnterField($index, $value) {
    $fields = @((Ui).SelectNodes('//node') | Where-Object class -eq 'android.widget.EditText')
    $point = Center $fields[$index]
    Adb shell input tap $point[0] $point[1] | Out-Null
    Adb shell input text $value | Out-Null
    Adb shell input keyevent 4 | Out-Null
}
function RestartApp {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}
if (-not $ResetTestAppData) { throw 'Requires -ResetTestAppData for the dedicated emulator' }
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Not the QA AVD' }
if ((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider -notin @('deterministic','scripted-qa')) { throw 'Not the isolated QA backend' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
RestartApp
TapText 'New student? Create a private account'
$email = 'interests-' + [Guid]::NewGuid().ToString('N') + '@example.com'
EnterField 0 $email
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
TapText "Grade`n8"
TapText 'Settings and account'
TapText 'Learning interests'
TextNode '0 of 3 selected' | Out-Null
TapText 'Select Sports'
TapText 'Select Music'
TapText 'Select Art'
$login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$email;password='qa-password-long-enough'} | ConvertTo-Json)
$headers = @{Authorization="Bearer $($login.access_token)"}
Invoke-RestMethod 'http://127.0.0.1:8000/__qa/interests/fail-next-response' -Method Post -Headers $headers | Out-Null
TapText 'Save interests'
TextNode 'The learning service is temporarily unavailable. Please try again.' | Out-Null
$uncertain = Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Headers $headers
if (($uncertain.interests -join ',') -ne 'sports,music,art') { throw 'Post-commit failure did not retain saved interests' }
TapText 'Try again'
TextNode '3 of 3 selected' | Out-Null
TapText 'Save interests'
TextNode 'Interests saved' | Out-Null
$profile = Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Headers $headers
if (($profile.interests -join ',') -ne 'sports,music,art') { throw 'Saved server interests differ from selection' }
RestartApp
TapText 'Settings and account'
TapText 'Learning interests'
TextNode '3 of 3 selected' | Out-Null
TextNode 'Remove Sports' | Out-Null
Adb shell screencap -p /sdcard/qa-interests.png | Out-Null
Adb pull /sdcard/qa-interests.png (Join-Path $repo 'artifacts\qa-interests.png') | Out-Null
TapText 'Clear all choices'
TapText 'Save interests'
TextNode 'Interests saved' | Out-Null
if ((Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Headers $headers).interests.Count -ne 0) { throw 'Clear was not persisted' }
RestartApp
TapText 'Settings and account'
TapText 'Learning interests'
TextNode '0 of 3 selected' | Out-Null
Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers $headers | Out-Null
Adb shell pm clear $package | Out-Null
Write-Output 'PASS: interests survive a post-commit 503 and idempotent retry, persist across restart, and clear durably without AI calls'
