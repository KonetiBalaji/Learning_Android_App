param(
    [string]$Serial = 'emulator-5554',
    [switch]$ResetTestAppData,
    [switch]$ExpectRubricFeedback,
    [switch]$VerifyDeletedSession,
    [switch]$VerifyWeeklyReport,
    [switch]$VerifyFractionModel,
    [switch]$VerifyStaleSubmission,
    [switch]$VerifyFailedResponse,
    [switch]$MalformedResponse
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" }
}
function Ui {
    Adb shell uiautomator dump /sdcard/qa-mastery.xml | Out-Null
    [xml]((Adb shell cat /sdcard/qa-mastery.xml) -join "`n")
}
function Center($node) {
    $coordinates = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($coordinates[0] + $coordinates[2])/2), [int](($coordinates[1] + $coordinates[3])/2))
}
function TextNode([string]$text) {
    for ($attempt=0; $attempt -lt 5; $attempt++) {
        $node = (Ui).SelectNodes('//node') | Where-Object { $_.text -eq $text } | Select-Object -First 1
        if ($node) { return $node }
        Adb shell input swipe 540 1850 540 750 400 | Out-Null
        Start-Sleep -Milliseconds 500
    }
    throw "UI text not found: $text"
}
function TapText([string]$text) {
    $point = Center (TextNode $text)
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 900
}
function EnterField([int]$index, [string]$value) {
    $fields = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })
    if ($fields.Count -le $index) { throw "Input field $index unavailable" }
    $point = Center $fields[$index]
    Adb shell input tap $point[0] $point[1] | Out-Null
    Adb shell input keycombination 113 29 | Out-Null
    Adb shell input text ($value.Replace(' ', '%s')) | Out-Null
    Adb shell input keyevent 4 | Out-Null
}
function RestartApp {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}

if (-not $ResetTestAppData) { throw 'This isolated QA script requires -ResetTestAppData; it clears only the test emulator app.' }
$avd = (Adb emu avd name) -join "`n"
if ($avd -notmatch '^LearnSmart_API36') { throw 'Refusing to clear data outside the dedicated LearnSmart_API36 AVD.' }
$health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
if ($health.ai_provider -notin @('deterministic', 'scripted-qa')) { throw 'Run an isolated deterministic or scripted-qa backend on port 8000 first.' }
if ($ExpectRubricFeedback -and $health.ai_provider -ne 'scripted-qa') { throw 'Rubric display checks require scripts/serve_qa.py --qa-only.' }
if ($VerifyFailedResponse -and ($VerifyStaleSubmission -or $health.ai_provider -ne 'scripted-qa')) { throw 'Failed-response QA requires scripted-qa and cannot combine with stale-submission QA.' }
if ($MalformedResponse -and -not $VerifyFailedResponse) { throw '-MalformedResponse requires -VerifyFailedResponse' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
RestartApp
TapText 'New student? Create a private account'
$qaEmail = "resume-" + [Guid]::NewGuid().ToString('N') + '@example.com'
EnterField 0 $qaEmail
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
TapText "Grade`n8"
TextNode 'No assessment yet' | Out-Null
TapText 'Mathematics'
TapText 'Fractions'
TextNode 'Question 1 of 3' | Out-Null
TapText '1/2'
TapText 'Submit answer'
TextNode 'Your answer: 1/2' | Out-Null
RestartApp
TextNode 'Your answer: 1/2' | Out-Null
Write-Output 'PASS: forced process restart restores the tutor and selected answer'
$savedPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
[xml]$savedXml = $savedPreferences
$savedNames = @($savedXml.map.ChildNodes | ForEach-Object { $_.name })
$sealedSession = @($savedXml.map.ChildNodes | Where-Object name -eq 'session_ciphertext')
if ($savedNames -contains 'token' -or $sealedSession.Count -ne 1 -or -not $sealedSession[0].InnerText.StartsWith('v1:')) {
    throw 'Session is not stored exclusively as a versioned encrypted envelope'
}
Write-Output 'PASS: restarted session uses encrypted storage with no legacy plaintext token (secret values omitted)'
if ($VerifyFractionModel) {
    TextNode 'Explore equal-sized parts' | Out-Null
    TextNode 'Reset fraction model' | Out-Null
    TextNode 'First fraction: 3/4' | Out-Null
    $slider = (Ui).SelectNodes('//node') | Where-Object { $_.'content-desc' -eq 'First numerator' } | Select-Object -First 1
    if (-not $slider) { throw 'First numerator slider is not accessible' }
    $bounds = [regex]::Matches($slider.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    $sliderWidth = $bounds[2] - $bounds[0]
    $sliderY = [int](($bounds[1] + $bounds[3])/2)
    Adb shell input swipe ([int]($bounds[0] + $sliderWidth * 0.75)) $sliderY ([int]($bounds[0] + $sliderWidth * 0.05)) $sliderY 400 | Out-Null
    TextNode 'First fraction: 0/4' | Out-Null
    TextNode '0/4 + 1/4 = 1/4 = 1/4' | Out-Null
    TapText 'Reset fraction model'
    TextNode '3/4 + 1/4 = 4/4 = 1' | Out-Null
    Adb shell screencap -p /sdcard/qa-fraction-model.png | Out-Null
    Adb pull /sdcard/qa-fraction-model.png (Join-Path $repo 'artifacts\qa-fraction-model.png') | Out-Null
    Write-Output 'PASS: fraction slider changes the sum and reset restores the original model'
}
TapText 'I understand — practise now'
EnterField 0 '6/8'
TapText 'Check answer'
TapText 'Explain it in your own words'
EnterField 0 'We add the numerator parts with the same denominator to make one whole'
TapText 'Submit my explanation'
if ($ExpectRubricFeedback) { TextNode 'Last explanation: 4 / 4' | Out-Null }
TextNode 'Question 2 of 3' | Out-Null
RestartApp
if ($ExpectRubricFeedback) {
    TextNode 'Last explanation: 4 / 4' | Out-Null
    TextNode 'Scripted QA feedback: the display and recovery contract are working.' | Out-Null
    Adb shell screencap -p /sdcard/qa-rubric-feedback.png | Out-Null
    Adb pull /sdcard/qa-rubric-feedback.png (Join-Path $repo 'artifacts\qa-rubric-feedback.png') | Out-Null
    Write-Output 'PASS: scripted rubric points and feedback render after process restart (not an AI quality evaluation)'
}
TextNode 'Question 2 of 3' | Out-Null
Write-Output 'PASS: remediation advances to question 2 and survives restart, without early mastery'
if ($VerifyStaleSubmission -or $VerifyFailedResponse) {
    # Advance this disposable session through another client while Android keeps Q2.
    [xml]$sessionPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $activeKey = "active_mastery:$($qaEmail.ToLowerInvariant())"
    $sessionId = ($sessionPreferences.map.ChildNodes | Where-Object name -eq $activeKey).InnerText
    if (-not $sessionId) { throw 'Disposable mastery session pointer unavailable' }
    $qaLogin = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail; password='qa-password-long-enough'} | ConvertTo-Json)
    $qaHeaders = @{Authorization="Bearer $($qaLogin.access_token)"}
    $sessionUrl = "http://127.0.0.1:8000/v1/mastery/sessions/$sessionId"
    $beforeStale = Invoke-RestMethod $sessionUrl -Headers $qaHeaders
    if ($beforeStale.question.ordinal -ne 2 -or -not $beforeStale.state_token) { throw 'Expected token-bearing question 2' }
    if ($VerifyStaleSubmission) {
        $otherAnswer = Invoke-RestMethod "$sessionUrl/diagnostic-answer" -Method Post -Headers $qaHeaders -ContentType 'application/json' -Body (@{selected_option='3/6'; expected_state=$beforeStale.state_token} | ConvertTo-Json)
        if ($otherAnswer.next_question.ordinal -ne 3) { throw 'Second client did not advance to question 3' }
    } else {
        $faultMode = if ($MalformedResponse) { 'malformed' } else { '503' }
        $armed = Invoke-RestMethod "http://127.0.0.1:8000/__qa/mastery/$sessionId/fail-next-response?mode=$faultMode" -Method Post -Headers $qaHeaders
        if (-not $armed.armed) { throw 'QA response fault was not armed' }
    }
}
TapText '3/6'
TapText 'Submit answer'
if ($VerifyFailedResponse) {
    $expectedError = if ($MalformedResponse) { 'Something went wrong. Please try again.' } else { 'The learning service is temporarily unavailable. Please try again.' }
    TextNode $expectedError | Out-Null
    $committed = Invoke-RestMethod $sessionUrl -Headers $qaHeaders
    if ($committed.question.ordinal -ne 3 -or $committed.state_token -eq $beforeStale.state_token) { throw 'Failed response did not follow a committed answer' }
    TapText 'Try again'
    TextNode 'Question 2 of 3' | Out-Null
    TapText 'Submit answer'
}
TextNode 'Question 3 of 3' | Out-Null
if ($VerifyFailedResponse) {
    $recovered = Invoke-RestMethod $sessionUrl -Headers $qaHeaders
    if ($recovered.state_token -ne $committed.state_token) { throw 'Retry after failed response changed server state' }
    RestartApp
    TextNode 'Question 3 of 3' | Out-Null
    Write-Output "PASS: post-commit $faultMode response retains old submission state; retry resumes Q3 without another answer"
}
if ($VerifyStaleSubmission) {
    $afterStale = Invoke-RestMethod $sessionUrl -Headers $qaHeaders
    if ($afterStale.state_token -ne $otherAnswer.state_token -or $afterStale.status -ne 'diagnostic') { throw 'Stale Android answer changed server state' }
    Adb shell screencap -p /sdcard/qa-mastery-stale.png | Out-Null
    Adb pull /sdcard/qa-mastery-stale.png (Join-Path $repo 'artifacts\qa-mastery-stale.png') | Out-Null
    RestartApp
    TextNode 'Question 3 of 3' | Out-Null
    Write-Output 'PASS: stale Android Q2 submission recovers Q3 without mutation and survives restart'
}
TapText '4/8'
TapText 'Submit answer'
TextNode 'Concept mastered' | Out-Null
TapText 'Continue learning'
TextNode '100%' | Out-Null
Adb shell screencap -p /sdcard/qa-mastery-progress.png | Out-Null
Adb pull /sdcard/qa-mastery-progress.png (Join-Path $repo 'artifacts\qa-mastery-progress.png') | Out-Null
Write-Output 'PASS: all questions are completed before mastery; chapter progress is 100% from backend evidence'
if ($VerifyWeeklyReport) {
    TapText '‹ All subjects'
    TapText 'View parent & teacher progress'
    TextNode 'Uncalibrated heuristic, not a prediction of exam performance.' | Out-Null
    TextNode 'Learning responses' | Out-Null
    TextNode 'Unique chapters mastered' | Out-Null
    $reportLogin = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail; password='qa-password-long-enough'} | ConvertTo-Json)
    $report = Invoke-RestMethod 'http://127.0.0.1:8000/v1/progress/weekly-report?grade=8' -Headers @{Authorization="Bearer $($reportLogin.access_token)"}
    if ($report.questions_answered -ne 5 -or $report.mastered_chapters -ne 1 -or $report.readiness_is_calibrated -ne $false) { throw 'Weekly report did not match the scripted five responses and one unique mastered chapter' }
    Adb shell screencap -p /sdcard/qa-weekly-report.png | Out-Null
    Adb pull /sdcard/qa-weekly-report.png (Join-Path $repo 'artifacts\qa-weekly-report.png') | Out-Null
    TapText '‹ Back to subjects'
    TapText 'Mathematics'
    Write-Output 'PASS: weekly report labels the heuristic and includes five learning responses, one unique chapter'
}
if ($VerifyDeletedSession) {
    # Delete only this run's disposable account via the public API. Never print its token.
    $loginBody = @{ email = $qaEmail; password = 'qa-password-long-enough' } | ConvertTo-Json
    $login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body $loginBody
    Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers @{Authorization = "Bearer $($login.access_token)"} | Out-Null
    TapText '‹ All subjects'
    TapText 'View parent & teacher progress'
    TextNode 'Your session has expired or is no longer valid. Please sign in again.' | Out-Null
    TapText 'Try again'
    TextNode 'Sign in' | Out-Null
    [xml]$afterExpiry = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $remainingNames = @($afterExpiry.map.ChildNodes | ForEach-Object { $_.name })
    if ($remainingNames -contains 'token' -or $remainingNames -contains 'session_ciphertext') { throw 'Invalid session credentials remained on disk' }
    RestartApp
    TextNode 'Sign in' | Out-Null
    EnterField 0 $qaEmail
    EnterField 1 'qa-password-long-enough'
    TapText 'Sign in'
    TextNode 'Email or password is incorrect. Please try again.' | Out-Null
    TapText 'Try again'
    TextNode 'Sign in' | Out-Null
    Write-Output 'PASS: deleted-account 401 returns to sign-in, clears tokens across restart, and rejects invalid login safely'
}
