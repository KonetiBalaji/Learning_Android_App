param([switch]$ResetTestAppData)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
$apk = Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk'

function Adb {
    & $adb -s emulator-5554 @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" }
}
function Ui {
    for ($attempt = 0; $attempt -lt 5; $attempt++) {
        if (((Adb shell uiautomator dump /sdcard/qa-deterministic.xml) -join '') -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-deterministic.xml) -join "`n")
        }
        Start-Sleep -Milliseconds 500
    }
    throw 'Could not obtain a fresh Android UI hierarchy.'
}
function Center($node) {
    $bounds = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($bounds[0] + $bounds[2]) / 2), [int](($bounds[1] + $bounds[3]) / 2))
}
function FindText([string]$text, [int]$seconds = 30, [switch]$Scroll) {
    $until = (Get-Date).AddSeconds($seconds)
    do {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        if ($Scroll) { Adb shell input swipe 540 1850 540 700 350 | Out-Null }
        Start-Sleep -Milliseconds 500
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

if (-not $ResetTestAppData) { throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.' }
if (-not (Test-Path -LiteralPath $apk)) { throw 'Build the current debug APK first.' }
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Dedicated LearnSmart_API36 AVD required.' }
$health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
if ($health.ai_provider -notin @('deterministic', 'scripted-qa')) {
    throw 'Run the deterministic backend or the QA-only backend without content fixtures.'
}

$cases = @(
    [pscustomobject]@{ Key='math-decimals'; Subject='Mathematics'; Chapter='Decimals'; Prompt='What is 3.75 + 1.20?'; Option='4.95' },
    [pscustomobject]@{ Key='science-cells'; Subject='Science'; Chapter='Cells and Living Things'; Prompt='Which cell structure controls what enters and leaves the cell?'; Option='Cell membrane' },
    [pscustomobject]@{ Key='english-grammar'; Subject='English'; Chapter='Grammar'; Prompt='Which sentence has correct subject-verb agreement?'; Option='The basket of apples is heavy.' },
    [pscustomobject]@{ Key='social-geography'; Subject='Social Studies'; Chapter='Geography'; Prompt='Which coordinate gives latitude before longitude?'; Option=('20' + [char]176 + 'N, 75' + [char]176 + 'E') }
)

$passed = @()
foreach ($case in $cases) {
    $email = 'fallback-' + [Guid]::NewGuid().ToString('N').Substring(0, 10) + '@x.co'
    $password = 'qa-password-long-enough'
    try {
        & $adb -s emulator-5554 uninstall $package | Out-Null
        Adb install $apk | Out-Null
        RestartApp
        TapText 'New student? Create a private account'
        EnterField 0 $email
        EnterField 1 $password
        TapText 'Create account'
        TapText "Grade`n8"
        TapText $case.Subject 30 -Scroll
        TapText $case.Chapter 30 -Scroll
        FindText 'Diagnostic quiz' | Out-Null
        FindText $case.Prompt 30 -Scroll | Out-Null
        FindText $case.Option 30 -Scroll | Out-Null
        $capture = "qa-deterministic-$($case.Key).png"
        Adb shell screencap -p "/sdcard/$capture" | Out-Null
        Adb pull "/sdcard/$capture" (Join-Path $repo "artifacts\$capture") | Out-Null
        $passed += $case.Key
    } finally {
        try {
            $login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{
                email=$email; password=$password
            } | ConvertTo-Json)
            Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers @{
                Authorization="Bearer $($login.access_token)"
            } | Out-Null
        } catch {
            if ($_.Exception.Response.StatusCode.value__ -ne 401) { Write-Warning "Account cleanup failed for $($case.Key): $($_.Exception.Message)" }
        }
        Adb shell pm clear $package | Out-Null
    }
}

Write-Output "PASS: rendered deterministic diagnostics for $($passed -join ', ')"
