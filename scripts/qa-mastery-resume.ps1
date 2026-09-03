param(
    [string]$Serial = 'emulator-5554',
    [switch]$ResetTestAppData,
    [switch]$ExpectRubricFeedback,
    [switch]$VerifyDeletedSession,
    [switch]$VerifyWeeklyReport,
    [switch]$VerifyFractionModel,
    [switch]$VerifyStaleSubmission,
    [switch]$VerifyFailedResponse,
    [switch]$MalformedResponse,
    [switch]$VerifyUnlocks,
    [switch]$VerifyStudyTime,
    [switch]$VerifyFreshPractice
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
    for ($dumpAttempt = 0; $dumpAttempt -lt 3; $dumpAttempt++) {
        $dumpOutput = (Adb shell uiautomator dump /sdcard/qa-mastery.xml) -join "`n"
        if ($dumpOutput -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-mastery.xml) -join "`n")
        }
        # A failed dump can leave the prior screen's XML on disk. Never tap it.
        Start-Sleep -Milliseconds 500
    }
    throw 'Could not obtain a fresh Android UI hierarchy'
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
if ($VerifyUnlocks -and ($health.ai_provider -ne 'scripted-qa' -or $VerifyWeeklyReport)) { throw 'Unlock QA requires scripted-qa and cannot combine with weekly-count assertions' }
if ($VerifyStudyTime -and -not $VerifyWeeklyReport) { throw 'Study time QA requires -VerifyWeeklyReport to verify the displayed total' }
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
if ($VerifyUnlocks) {
    function ChapterCard([string]$title) {
        $node = TextNode $title
        return $node.SelectSingleNode("ancestor::node[@clickable='true' or @enabled='false'][1]")
    }
    $geometry = ChapterCard 'Geometry'
    if (-not $geometry -or $geometry.enabled -ne 'false') { throw 'Geometry is not initially disabled' }
    $auth = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
    $unlockHeaders = @{Authorization="Bearer $($auth.access_token)"}
    Invoke-RestMethod 'http://127.0.0.1:8000/__qa/learning-path/algebra?state=mastered' -Method Post -Headers $unlockHeaders | Out-Null
    # TextNode's normal lookup scrolls down; explicitly return to the top controls.
    Adb shell input swipe 540 600 540 1900 400 | Out-Null
    TapText 'Refresh progress'
    $geometry = ChapterCard 'Geometry'
    if (-not $geometry -or $geometry.enabled -ne 'true') { throw 'Geometry did not unlock after server refresh' }
    Invoke-RestMethod 'http://127.0.0.1:8000/__qa/learning-path/algebra?state=diagnostic' -Method Post -Headers $unlockHeaders | Out-Null
    TapText 'Geometry'
    TextNode 'This chapter is currently locked. Complete its prerequisite in this grade, then use Refresh progress. Your saved learning is unchanged.' | Out-Null
    TapText 'Try again'
    $geometry = ChapterCard 'Geometry'
    if (-not $geometry -or $geometry.enabled -ne 'false') { throw 'Denied stale unlock was not cleared' }
    $audit = Invoke-RestMethod 'http://127.0.0.1:8000/__qa/learning-path/geometry-count' -Headers $unlockHeaders
    if ($audit.sessions -ne 0) { throw 'Denied Geometry start created a session' }
    Adb shell screencap -p /sdcard/qa-chapter-unlock.png | Out-Null
    Adb pull /sdcard/qa-chapter-unlock.png (Join-Path $repo 'artifacts\qa-chapter-unlock.png') | Out-Null
    RestartApp
    TapText 'Mathematics'
    $geometry = ChapterCard 'Geometry'
    if (-not $geometry -or $geometry.enabled -ne 'false') { throw 'Relocked state did not survive restart' }
    Invoke-RestMethod 'http://127.0.0.1:8000/__qa/learning-path/algebra?state=mastered' -Method Post -Headers $unlockHeaders | Out-Null
    Adb shell input swipe 540 600 540 1900 400 | Out-Null
    TapText 'Refresh progress'
    $geometry = ChapterCard 'Geometry'
    if (-not $geometry -or $geometry.enabled -ne 'true') { throw 'Refresh did not restore eligible Geometry access' }
    Adb shell input swipe 540 600 540 1900 400 | Out-Null
    Write-Output 'PASS: server refresh unlocks Geometry; stale start denied with no new session; relock survives restart and eligibility refresh restores access'
}
TapText 'Fractions'
TextNode 'Question 1 of 3' | Out-Null
if ($VerifyStudyTime) {
    $timeLogin = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
    $timeHeaders = @{Authorization="Bearer $($timeLogin.access_token)"}
    function RecordedTime {
        $snapshot = Invoke-RestMethod 'http://127.0.0.1:8000/v1/progress/weekly-report?grade=8' -Headers $timeHeaders
        if ($null -eq $snapshot.observed_study_seconds) { throw 'Backend lacks observed study time support' }
        return [long]$snapshot.observed_study_seconds
    }
    Start-Sleep -Seconds 30
    $foregroundTime = RecordedTime
    if ($foregroundTime -lt 10 -or $foregroundTime -gt 50) { throw "Unexpected foreground presence: $foregroundTime seconds" }
    Write-Output "PASS: foreground learning recorded $foregroundTime seconds without synthetic duration injection"
    Adb shell input keyevent 3 | Out-Null
    Start-Sleep -Seconds 5
    $backgroundBaseline = RecordedTime
    Start-Sleep -Seconds 30
    if ((RecordedTime) -ne $backgroundBaseline) { throw 'Study time accrued while backgrounded' }
    RestartApp
    TextNode 'Question 1 of 3' | Out-Null
    Start-Sleep -Seconds 3
    if ((RecordedTime) -ne $backgroundBaseline) { throw 'Restart credited the background gap' }
    Write-Output 'PASS: background time is excluded and restart begins a fresh interval'
    Start-Sleep -Seconds 50
    $idleBaseline = RecordedTime
    Start-Sleep -Seconds 20
    if ((RecordedTime) -ne $idleBaseline) { throw 'Study time accrued after the idle threshold' }
    Write-Output 'PASS: idle foreground screen stops accruing recorded study presence'
}
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
$practiceAnswer = '6/8'
if ($VerifyFreshPractice) {
    $practiceLogin = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
    $practiceHeaders = @{Authorization="Bearer $($practiceLogin.access_token)"}
    [xml]$practicePreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $practiceSession = ($practicePreferences.map.ChildNodes | Where-Object name -eq "active_mastery:$qaEmail").InnerText
    if (-not $practiceSession) { throw 'Missing saved mastery session' }
    $practicePath = "http://127.0.0.1:8000/v1/mastery/sessions/$practiceSession"
    $previousPrompt = (Invoke-RestMethod $practicePath -Headers $practiceHeaders).tutor.practice_prompt
    foreach ($round in 1..2) {
        EnterField 0 '0'
        TapText 'Check answer'
        $freshState = Invoke-RestMethod $practicePath -Headers $practiceHeaders
        $freshPrompt = $freshState.tutor.practice_prompt
        if ($freshState.status -ne 'practice' -or $freshPrompt -eq $previousPrompt) { throw 'Incorrect practice did not persist a fresh question' }
        TextNode $freshPrompt | Out-Null
        TextNode $freshState.tutor.hint | Out-Null
        $field = (Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' } | Select-Object -First 1
        if (-not $field -or $field.text -eq '0') { throw 'Old practice answer was not cleared' }
        RestartApp
        TextNode $freshPrompt | Out-Null
        $afterRestart = Invoke-RestMethod $practicePath -Headers $practiceHeaders
        if ($afterRestart.state_token -ne $freshState.state_token) { throw 'Restart changed the saved practice version' }
        $previousPrompt = $freshPrompt
    }
    $terms = [regex]::Matches($freshPrompt, '(\d+)/(\d+)')
    if ($terms.Count -ne 2 -or $terms[0].Groups[2].Value -ne $terms[1].Groups[2].Value) { throw 'Unexpected addition fixture shape' }
    $numerator = [int]$terms[0].Groups[1].Value + [int]$terms[1].Groups[1].Value
    $practiceAnswer = "$numerator/$($terms[0].Groups[2].Value)"
    Adb shell screencap -p /sdcard/qa-fresh-practice.png | Out-Null
    Adb pull /sdcard/qa-fresh-practice.png (Join-Path $repo 'artifacts\qa-fresh-practice.png') | Out-Null
    Write-Output 'PASS: two incorrect practice answers produce distinct persisted prompts/hints; old input clears and each variant survives restart'
}
EnterField 0 $practiceAnswer
TapText 'Check answer'
TapText 'Explain it in your own words'
EnterField 0 'We add the numerator parts with the same denominator and keep the denominator unchanged'
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
    $expectedResponses = if ($VerifyFreshPractice) { 7 } else { 5 }
    if ($report.questions_answered -ne $expectedResponses -or $report.mastered_chapters -ne 1 -or $report.readiness_is_calibrated -ne $false) { throw 'Weekly report did not match the scripted response count and one unique mastered chapter' }
    if ($VerifyStudyTime) {
        $seconds = [long]$report.observed_study_seconds
        if ($seconds -le 0) { throw 'Weekly study total is missing' }
        $timeLabel = if ($seconds -lt 60) { "${seconds}s" } elseif ($seconds -lt 3600) { "$([math]::Floor($seconds / 60))m $($seconds % 60)s" } else { "$([math]::Floor($seconds / 3600))h $([math]::Floor(($seconds % 3600) / 60))m" }
        TextNode 'Recorded study presence' | Out-Null
        TextNode $timeLabel | Out-Null
        TextNode 'Last 7 days, selected grade. Counts recorded activity on learning screens only, not total study time or proof of attention. Idle, offline and older untracked activity may be missing.' | Out-Null
        $completedBaseline = RecordedTime
        Start-Sleep -Seconds 20
        if ((RecordedTime) -ne $completedBaseline) { throw 'Non-learning report screen accrued study time' }
        Adb shell screencap -p /sdcard/qa-study-time.png | Out-Null
        Adb pull /sdcard/qa-study-time.png (Join-Path $repo 'artifacts\qa-study-time.png') | Out-Null
        Write-Output "PASS: weekly UI matches server total ($timeLabel) and report screen does not accrue time"
    }
    Adb shell screencap -p /sdcard/qa-weekly-report.png | Out-Null
    Adb pull /sdcard/qa-weekly-report.png (Join-Path $repo 'artifacts\qa-weekly-report.png') | Out-Null
    TapText '‹ Back to subjects'
    TapText 'Mathematics'
    Write-Output "PASS: weekly report labels the heuristic and includes $expectedResponses learning responses, one unique chapter"
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
