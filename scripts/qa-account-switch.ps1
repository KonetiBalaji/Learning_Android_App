param([switch]$ResetTestAppData)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s emulator-5554 @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" }
}
function Ui {
    for ($attempt = 0; $attempt -lt 4; $attempt++) {
        if (((Adb shell uiautomator dump /sdcard/qa-account-switch.xml) -join '') -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-account-switch.xml) -join "`n")
        }
        Start-Sleep -Milliseconds 400
    }
    throw 'Could not obtain a fresh Android UI hierarchy.'
}
function Center($node) {
    $bounds = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($bounds[0] + $bounds[2]) / 2), [int](($bounds[1] + $bounds[3]) / 2))
}
function FindText([string]$text, [int]$seconds = 30, [switch]$Scroll) {
    $until = (Get-Date).AddSeconds($seconds)
    $attempt = 0
    do {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        if ($Scroll) {
            if (($attempt % 8) -lt 4) { Adb shell input swipe 540 1850 540 750 350 | Out-Null }
            else { Adb shell input swipe 540 750 540 1850 350 | Out-Null }
            $attempt++
        }
        Start-Sleep -Milliseconds 600
    } while ((Get-Date) -lt $until)
    throw "UI text not found: $text"
}
function TapText([string]$text, [int]$seconds = 30, [switch]$Scroll) {
    $point = Center (FindText $text $seconds -Scroll:$Scroll)
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 900
}
function EnterField([int]$index, [string]$value) {
    $fields = @((Ui).SelectNodes('//node') | Where-Object class -eq 'android.widget.EditText')
    if ($fields.Count -le $index) { throw "Input field $index unavailable" }
    $point = Center $fields[$index]
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 300
    Adb shell input keycombination 113 29 | Out-Null
    foreach ($character in $value.ToCharArray()) {
        switch ($character) {
            '@' { Adb shell input keyevent 77 | Out-Null }
            '.' { Adb shell input keyevent 56 | Out-Null }
            '-' { Adb shell input keyevent 69 | Out-Null }
            default { Adb shell input text ([string]$character) | Out-Null }
        }
    }
    Adb shell input keyevent 4 | Out-Null
}
function RestartApp {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}
function CreateAccount([string]$email, [string]$interest) {
    TapText 'New student? Create a private account'
    EnterField 0 $email
    EnterField 1 'qa-password-long-enough'
    TapText 'Create account'
    TapText "Grade`n8" 30
    TapText 'Settings and account' 30 -Scroll
    TapText 'Learning interests' 30 -Scroll
    FindText '0 of 3 selected' 30 | Out-Null
    TapText "Select $interest" 30 -Scroll
    TapText 'Save interests' 30 -Scroll
    FindText 'Interests saved' 30 -Scroll | Out-Null
    TapText '‹ Back to settings' 30 -Scroll
    TapText 'Sign out' 30 -Scroll
}
function Login([string]$email) {
    EnterField 0 $email
    EnterField 1 'qa-password-long-enough'
    TapText 'Sign in'
    TapText "Grade`n8" 30
}
if (-not $ResetTestAppData) { throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.' }
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Dedicated LearnSmart_API36 AVD required.' }
$health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
if ($health.ai_provider -notin @('deterministic', 'scripted-qa')) { throw 'Isolated deterministic QA backend required.' }
& $adb -s emulator-5554 uninstall $package | Out-Null
Adb install (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
RestartApp
$suffix = [Guid]::NewGuid().ToString('N')
$firstEmail = "switch-a-$suffix@example.com"
$secondEmail = "switch-b-$suffix@example.com"
CreateAccount $firstEmail 'Sports'
CreateAccount $secondEmail 'Music'
Login $firstEmail
TapText 'Settings and account' 30 -Scroll
TapText 'Learning interests' 30 -Scroll
FindText '1 of 3 selected' 30 | Out-Null
FindText 'Remove Sports' 30 -Scroll | Out-Null
FindText 'Select Music' 30 -Scroll | Out-Null
RestartApp
TapText 'Settings and account' 30 -Scroll
FindText $firstEmail 30 -Scroll | Out-Null
TapText 'Learning interests' 30 -Scroll
FindText 'Remove Sports' 30 -Scroll | Out-Null
FindText 'Select Music' 30 -Scroll | Out-Null
Adb shell screencap -p /sdcard/qa-account-switch.png | Out-Null
Adb pull /sdcard/qa-account-switch.png (Join-Path $repo 'artifacts\qa-account-switch.png') | Out-Null

$profiles = @{}
foreach ($email in @($firstEmail, $secondEmail)) {
    $login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{
        email = $email; password = 'qa-password-long-enough'
    } | ConvertTo-Json)
    $headers = @{Authorization = "Bearer $($login.access_token)"}
    $profiles[$email] = Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Headers $headers
    Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers $headers | Out-Null
}
if (($profiles[$firstEmail].interests -join ',') -ne 'sports') { throw 'First account preference isolation failed.' }
if (($profiles[$secondEmail].interests -join ',') -ne 'music') { throw 'Second account preference isolation failed.' }
Adb shell pm clear $package | Out-Null
Write-Output 'PASS: two Android accounts kept distinct server preferences across sign-out, sign-in and restart; both disposable accounts were deleted.'
