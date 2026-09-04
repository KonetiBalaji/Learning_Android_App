param(
    [string]$Serial = 'emulator-5554',
    [string]$RuntimeDir = 'artifacts\qa-live-fresh-runtime',
    [switch]$ResetTestAppData
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$runtime = [IO.Path]::GetFullPath((Join-Path $repo $RuntimeDir))
$artifactRoot = [IO.Path]::GetFullPath((Join-Path $repo 'artifacts'))
if (-not $runtime.StartsWith($artifactRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'RuntimeDir must stay inside this repository artifacts directory.'
}
if (-not $ResetTestAppData) { throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.' }

$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" }
}
function Ui {
    for ($attempt = 0; $attempt -lt 4; $attempt++) {
        $dump = (Adb shell uiautomator dump /sdcard/qa-general-fresh.xml) -join "`n"
        if ($dump -match 'dumped to') { return [xml]((Adb shell cat /sdcard/qa-general-fresh.xml) -join "`n") }
        Start-Sleep -Milliseconds 500
    }
    throw 'Could not obtain a fresh Android UI hierarchy.'
}
function Center($node) {
    $values = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($values[0] + $values[2]) / 2), [int](($values[1] + $values[3]) / 2))
}
function FindText([string]$text, [int]$seconds = 60, [switch]$Scroll) {
    $until = (Get-Date).AddSeconds($seconds)
    do {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        if ($Scroll) { Adb shell input swipe 540 1850 540 750 350 | Out-Null }
        Start-Sleep -Milliseconds 750
    } while ((Get-Date) -lt $until)
    throw "UI text not found: $text"
}
function TapText([string]$text, [int]$seconds = 60) {
    $point = Center (FindText $text $seconds -Scroll)
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 900
}
function EnterField([int]$index, [string]$value) {
    $fields = @((Ui).SelectNodes('//node') | Where-Object class -eq 'android.widget.EditText')
    if ($fields.Count -le $index) { throw "Input field $index unavailable" }
    $point = Center $fields[$index]
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 600
    Adb shell input keycombination 113 29 | Out-Null
    Start-Sleep -Milliseconds 100
    foreach ($character in $value.ToCharArray()) {
        switch ($character) {
            ' ' { Adb shell input keyevent 62 | Out-Null }
            '@' { Adb shell input keyevent 77 | Out-Null }
            '.' { Adb shell input keyevent 56 | Out-Null }
            '?' { Adb shell input keycombination 59 76 | Out-Null }
            default { Adb shell input text ([string]$character) | Out-Null }
        }
        Start-Sleep -Milliseconds 35
    }
    Adb shell input keyevent 4 | Out-Null
    if ($fields[$index].password -ne 'true') {
        $entered = @((Ui).SelectNodes('//node') | Where-Object class -eq 'android.widget.EditText')[$index].text
        if ($entered -ne $value) { throw "Input field $index did not receive the exact scripted value" }
    }
}
function RestartApp {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}

$avd = (Adb emu avd name) -join "`n"
if ($avd -notmatch '^LearnSmart_API36') { throw 'Refusing to clear data outside the dedicated LearnSmart_API36 AVD.' }
$health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
if ($health.ai_provider -ne 'openai') { throw 'Run the isolated live-provider backend on port 8000 first.' }
if ([IO.Path]::GetFullPath($runtime) -ne $runtime) { throw 'Runtime path resolution failed.' }

Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
RestartApp
TapText 'New student? Create a private account'
$email = 'general-' + [Guid]::NewGuid().ToString('N') + '@example.com'
EnterField 0 $email
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
TapText "Grade`n8"
TapText 'Science'
$diagnosticReady = $false
foreach ($diagnosticAttempt in 1..3) {
    TapText 'Cells and Living Things'
    $deadline = (Get-Date).AddSeconds(120)
    do {
        $tree = Ui
        if ($tree.SelectNodes('//node') | Where-Object text -eq 'Question 1 of 3') {
            $diagnosticReady = $true
            break
        }
        if ($tree.SelectNodes('//node') | Where-Object text -eq 'We could not continue') { break }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    if ($diagnosticReady) { break }
    if ($diagnosticAttempt -lt 3) { TapText 'Try again' }
}
if (-not $diagnosticReady) { throw 'No reviewed Science diagnostic was available after three bounded attempts.' }

$login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{
    email = $email; password = 'qa-password-long-enough'
} | ConvertTo-Json)
$headers = @{Authorization = "Bearer $($login.access_token)"}
[xml]$preferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
$sessionId = ($preferences.map.ChildNodes | Where-Object name -eq "active_mastery:$email").InnerText
if (-not $sessionId) { throw 'Android did not persist the live mastery session.' }
$sessionUrl = "http://127.0.0.1:8000/v1/mastery/sessions/$sessionId"
$state = Invoke-RestMethod $sessionUrl -Headers $headers
$python = Join-Path $repo 'backend\.venv\Scripts\python.exe'
$database = Join-Path $runtime 'learning.sqlite3'
$correct = (& $python -c "import json,sqlite3,sys; row=sqlite3.connect(sys.argv[1]).execute('select questions_json from mastery_sessions where id=?',(sys.argv[2],)).fetchone(); print(json.loads(row[0])[0]['correct_option'])" $database $sessionId) -join "`n"
$wrong = @($state.question.options | Where-Object { $_ -ne $correct })[0]
if (-not $wrong) { throw 'Could not select a known wrong diagnostic choice.' }
TapText $wrong
TapText 'Submit answer'
FindText 'I understand — practise now' 90 -Scroll | Out-Null
$oldPrompt = (Invoke-RestMethod $sessionUrl -Headers $headers).tutor.practice_prompt
TapText 'I understand — practise now'
FindText $oldPrompt 20 -Scroll | Out-Null
EnterField 0 'definitely wrong'
TapText 'Check answer'

$newState = $null
$until = (Get-Date).AddSeconds(90)
do {
    Start-Sleep -Seconds 1
    $candidate = Invoke-RestMethod $sessionUrl -Headers $headers
    if ($candidate.status -eq 'practice' -and $candidate.tutor.practice_prompt -ne $oldPrompt) { $newState = $candidate; break }
} while ((Get-Date) -lt $until)
if (-not $newState) { throw 'Live provider did not persist a reviewed fresh practice question.' }
FindText $newState.tutor.practice_prompt 20 -Scroll | Out-Null
FindText $newState.tutor.hint 20 -Scroll | Out-Null
Adb shell screencap -p /sdcard/qa-general-fresh-practice.png | Out-Null
Adb pull /sdcard/qa-general-fresh-practice.png (Join-Path $repo 'artifacts\qa-general-fresh-practice.png') | Out-Null
RestartApp
FindText $newState.tutor.practice_prompt 30 -Scroll | Out-Null

$answer = (& $python -c "import json,sqlite3,sys; row=sqlite3.connect(sys.argv[1]).execute('select questions_json from mastery_sessions where id=?',(sys.argv[2],)).fetchone(); print(json.loads(row[0])[0]['practice_answers'][0])" $database $sessionId) -join "`n"
EnterField 0 $answer
TapText 'Check answer'
FindText 'Explain it in your own words' 30 -Scroll | Out-Null
Write-Output 'PASS: live Grade 8 Science practice was independently reviewed, replaced after a wrong answer, persisted across restart and accepted its saved reviewed key.'
