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
    [switch]$VerifyFreshPractice,
    [switch]$VerifyRejectedRewrite,
    [switch]$VerifyReadAloud,
    [switch]$VerifyVoiceInput,
    [switch]$VerifyTutorConversation,
    [switch]$VerifyTutorResponseLoss,
    [switch]$VerifyBadges
)
$ErrorActionPreference = 'Stop'
if ($VerifyTutorResponseLoss) { $VerifyTutorConversation = $true }
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
function TextPattern([string]$pattern) {
    for ($attempt=0; $attempt -lt 5; $attempt++) {
        $node = (Ui).SelectNodes('//node') | Where-Object { $_.text -match $pattern } | Select-Object -First 1
        if ($node) { return $node }
        Adb shell input swipe 540 1850 540 750 400 | Out-Null
        Start-Sleep -Milliseconds 500
    }
    throw "UI text pattern not found: $pattern"
}
function TapText([string]$text) {
    $point = Center (TextNode $text)
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 900
}
function DescriptionNode([string]$description) {
    for ($attempt=0; $attempt -lt 5; $attempt++) {
        $node = (Ui).SelectNodes('//node') | Where-Object { $_.'content-desc' -eq $description } | Select-Object -First 1
        if ($node) { return $node }
        Start-Sleep -Milliseconds 500
    }
    throw "UI description not found: $description"
}
function EnterField([int]$index, [string]$value) {
    $fields = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })
    if ($fields.Count -le $index) { throw "Input field $index unavailable" }
    $point = Center $fields[$index]
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 600
    Adb shell input keycombination 113 29 | Out-Null
    Start-Sleep -Milliseconds 100
    # Compose can recompose between injected key events and silently drop the
    # tail of a bulk `input text` command. Pace individual characters instead.
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
        $entered = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })[$index].text
        if ($entered -ne $value) { throw "Input field $index did not receive the exact scripted value" }
    }
}
function RestartApp {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}
function VerifyTalkBackVoiceReview([string]$expectedDraft) {
    $oldServices = ((Adb shell settings get secure enabled_accessibility_services) -join '').Trim()
    $oldEnabled = ((Adb shell settings get secure accessibility_enabled) -join '').Trim()
    $talkBackPackage = 'com.google.android.marvin.talkback'
    $notificationWasGranted = ((Adb shell dumpsys package $talkBackPackage) -join "`n") -match 'android\.permission\.POST_NOTIFICATIONS: granted=true'
    try {
        if (-not $notificationWasGranted) { Adb shell pm grant $talkBackPackage android.permission.POST_NOTIFICATIONS | Out-Null }
        Adb shell settings put secure enabled_accessibility_services "$talkBackPackage/$talkBackPackage.TalkBackService" | Out-Null
        Adb shell settings put secure accessibility_enabled 1 | Out-Null
        Start-Sleep -Seconds 2
        $accessibility = (Adb shell dumpsys accessibility) -join "`n"
        if ($accessibility -notmatch 'com\.google\.android\.marvin\.talkback/.+TalkBackService') { throw 'TalkBack service did not become active' }
        foreach ($label in @(
            'Talk with your tutor',
            $expectedDraft,
            '🎙 Speak my tutor question',
            "Uses your device's speech service, which may process audio online.",
            'Review the recognized text before submitting.',
            'Send question',
            'No questions in this lesson conversation yet.'
        )) {
            try { TextNode $label | Out-Null } catch { throw "TalkBack tree omitted voice-review element: $label" }
        }
    } finally {
        if ([string]::IsNullOrWhiteSpace($oldServices) -or $oldServices -eq 'null') {
            Adb shell settings delete secure enabled_accessibility_services | Out-Null
        } else { Adb shell settings put secure enabled_accessibility_services $oldServices | Out-Null }
        if ([string]::IsNullOrWhiteSpace($oldEnabled) -or $oldEnabled -eq 'null') {
            Adb shell settings delete secure accessibility_enabled | Out-Null
        } else { Adb shell settings put secure accessibility_enabled $oldEnabled | Out-Null }
        if (-not $notificationWasGranted) { Adb shell pm revoke $talkBackPackage android.permission.POST_NOTIFICATIONS | Out-Null }
        Start-Sleep -Seconds 1
    }
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
if ($VerifyRejectedRewrite -and -not $VerifyFreshPractice) { throw 'Rejected rewrite QA requires -VerifyFreshPractice' }
if ($VerifyTutorConversation -and ($health.ai_provider -ne 'scripted-qa' -or $VerifyReadAloud)) { throw 'Conversation QA requires scripted-qa and runs separately from read-aloud QA.' }
if ($VerifyVoiceInput -and $VerifyTutorConversation) { throw 'Voice-input recovery runs separately from the tutor-conversation journey.' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
RestartApp
DescriptionNode 'AI teacher available after sign in' | Out-Null
TapText 'New student? Create a private account'
$qaEmail = "resume-" + [Guid]::NewGuid().ToString('N') + '@example.com'
EnterField 0 $qaEmail
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
DescriptionNode 'AI teacher ready' | Out-Null
TapText "Grade`n8"
DescriptionNode 'AI teacher ready' | Out-Null
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
DescriptionNode 'AI teacher ready' | Out-Null
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
if ($VerifyVoiceInput) {
    TapText 'Ask the tutor a question'
    TextNode 'Talk with your tutor' | Out-Null
    $draft = 'Keep my typed question'
    EnterField 0 $draft
    TapText '🎙 Speak my tutor question'
    Start-Sleep -Seconds 2
    Adb shell input keyevent 4 | Out-Null
    TextNode 'Voice input cancelled. Your typed answer is unchanged.' | Out-Null
    $field = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })[0]
    if ($field.text -ne $draft) { throw 'Cancelling speech replaced the typed tutor question.' }
    try {
        Adb shell pm disable-user --user 0 com.google.android.tts | Out-Null
        TapText '🎙 Speak my tutor question'
        TextNode 'Voice input is unavailable on this device. Please type your answer.' | Out-Null
        $field = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })[0]
        if ($field.text -ne $draft) { throw 'Unavailable speech service replaced the typed tutor question.' }
        Adb shell screencap -p /sdcard/qa-voice-input-recovery.png | Out-Null
        Adb pull /sdcard/qa-voice-input-recovery.png (Join-Path $repo 'artifacts\qa-voice-input-recovery.png') | Out-Null
    } finally {
        Adb shell pm enable com.google.android.tts | Out-Null
    }
    try {
        Adb shell am broadcast -a "$package.debug.ENABLE_SPEECH_FIXTURE" -n "$package/.DebugSpeechFixtureReceiver" | Out-Null
        $componentState = (Adb shell dumpsys package $package) -join "`n"
        if ($componentState -notmatch 'enabledComponents:[\s\S]*DebugSpeechRecognitionActivity') { throw 'Debug speech-result fixture did not enable itself' }
        Adb shell pm disable-user --user 0 com.google.android.tts | Out-Null
        TapText '🎙 Speak my tutor question'
        TextNode 'Review the recognized text before submitting.' | Out-Null
        $field = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })[0]
        $expectedDraft = "$draft Why does the denominator stay?"
        if ($field.text -ne $expectedDraft) { throw "Recognized text was not safely admitted for review: $($field.text)" }
        TextNode 'No questions in this lesson conversation yet.' | Out-Null
        VerifyTalkBackVoiceReview $expectedDraft
        Adb shell screencap -p /sdcard/qa-voice-input-success.png | Out-Null
        Adb pull /sdcard/qa-voice-input-success.png (Join-Path $repo 'artifacts\qa-voice-input-success.png') | Out-Null
    } finally {
        Adb shell pm enable com.google.android.tts | Out-Null
        Adb shell am broadcast -a "$package.debug.DISABLE_SPEECH_FIXTURE" -n "$package/.DebugSpeechFixtureReceiver" | Out-Null
    }
    $auth = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
    Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers @{Authorization="Bearer $($auth.access_token)"} | Out-Null
    Adb shell pm clear $package | Out-Null
    Write-Output 'PASS: speech cancellation/unavailable recovery preserves the draft; a successful debug activity result skips unusable alternatives, normalizes text and exposes the unsent review state to TalkBack.'
    return
}
if ($VerifyTutorConversation) {
    TapText 'Ask the tutor a question'
    TextNode 'Talk with your tutor' | Out-Null
    TextNode 'No questions in this lesson conversation yet.' | Out-Null
    EnterField 0 'Why keep the denominator?'
    if ($VerifyTutorResponseLoss) {
        $auth = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
        $chatHeaders = @{Authorization="Bearer $($auth.access_token)"}
        $chatSession = ($savedXml.map.ChildNodes | Where-Object name -eq "active_mastery:$qaEmail").InnerText
        $chatPath = "http://127.0.0.1:8000/v1/mastery/sessions/$chatSession"
        Invoke-RestMethod "http://127.0.0.1:8000/__qa/mastery/$chatSession/fail-next-tutor-response" -Method Post -Headers $chatHeaders | Out-Null
    }
    TapText 'Send question'
    if ($VerifyTutorResponseLoss) {
        TextNode 'We could not continue' | Out-Null
        TapText 'Try again'
        TextNode 'Pending question: Why keep the denominator?' | Out-Null
        TextNode 'Check reply' | Out-Null
        $beforeRecovery = Invoke-RestMethod "$chatPath/tutor-questions" -Headers $chatHeaders
        if ($beforeRecovery.Count -ne 1 -or $beforeRecovery[0].status -ne 'complete') { throw 'Lost response did not leave exactly one complete server turn' }
        Adb shell screencap -p /sdcard/qa-tutor-response-recovery.png | Out-Null
        Adb pull /sdcard/qa-tutor-response-recovery.png (Join-Path $repo 'artifacts\qa-tutor-response-recovery.png') | Out-Null
        TapText 'Check reply'
        $afterRecovery = Invoke-RestMethod "$chatPath/tutor-questions" -Headers $chatHeaders
        if ($afterRecovery.Count -ne 1 -or $afterRecovery[0].request_id -ne $beforeRecovery[0].request_id) { throw 'Check reply did not reuse the saved request identity' }
        Write-Output 'PASS: post-commit 503 recovery reuses the single saved tutor request'
    }
    TextNode 'Scripted QA reply: equal denominators describe equal-sized parts.' | Out-Null
    Adb shell screencap -p /sdcard/qa-tutor-conversation.png | Out-Null
    Adb pull /sdcard/qa-tutor-conversation.png (Join-Path $repo 'artifacts\qa-tutor-conversation.png') | Out-Null
    RestartApp
    TextNode 'Your answer: 1/2' | Out-Null
    TapText 'Ask the tutor a question'
    TextNode 'You: Why keep the denominator?' | Out-Null
    TextNode 'Scripted QA reply: equal denominators describe equal-sized parts.' | Out-Null
    EnterField 0 'QA unavailable'
    TapText 'Send question'
    TextNode 'The tutor could not reply. Retry only when you are ready; it counts as a new request.' | Out-Null
    TapText 'Use this question again'
    $draft = @((Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' })
    if ($draft.Count -ne 1 -or $draft[0].text -ne 'QA unavailable') { throw 'Failed question was not restored to the draft' }
    $auth = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
    $chatHeaders = @{Authorization="Bearer $($auth.access_token)"}
    $chatSession = ($savedXml.map.ChildNodes | Where-Object name -eq "active_mastery:$qaEmail").InnerText
    $chatPath = "http://127.0.0.1:8000/v1/mastery/sessions/$chatSession"
    $turns = Invoke-RestMethod "$chatPath/tutor-questions" -Headers $chatHeaders
    if ($turns.Count -ne 2 -or $turns[0].status -ne 'complete' -or $turns[1].status -ne 'failed') { throw 'Unexpected persisted conversation or automatic retry' }
    $mastery = Invoke-RestMethod $chatPath -Headers $chatHeaders
    if ($mastery.status -ne 'tutor' -or $mastery.mastery_score -ne 0) { throw 'Conversation changed mastery state' }
    Adb shell screencap -p /sdcard/qa-tutor-conversation-failure.png | Out-Null
    Adb pull /sdcard/qa-tutor-conversation-failure.png (Join-Path $repo 'artifacts\qa-tutor-conversation-failure.png') | Out-Null
    Write-Output 'PASS: tutor question/reply, restart history, unavailable reply, draft-only retry and unchanged mastery. Scripted content; no live answer-quality claim.'
    return
}
if ($VerifyReadAloud) {
    DescriptionNode 'AI teacher ready' | Out-Null
    $readLabel = TextNode 'Read explanation aloud'
    $readButton = $readLabel.SelectSingleNode("ancestor-or-self::node[@clickable='true'][1]")
    if (-not $readButton -or $readButton.enabled -ne 'true') {
        Adb shell screencap -p /sdcard/qa-read-aloud-unavailable.png | Out-Null
        Adb pull /sdcard/qa-read-aloud-unavailable.png (Join-Path $repo 'artifacts\qa-read-aloud-unavailable.png') | Out-Null
        throw 'Speech engine not ready; cannot verify playback lifecycle on this device.'
    }
    TapText 'Read explanation aloud'
    DescriptionNode 'AI teacher is speaking' | Out-Null
    Adb shell screencap -p /sdcard/qa-ai-teacher-speaking.png | Out-Null
    Adb pull /sdcard/qa-ai-teacher-speaking.png (Join-Path $repo 'artifacts\qa-ai-teacher-speaking.png') | Out-Null
    Adb shell input keyevent 3 | Out-Null
    Start-Sleep -Seconds 2
    # Resume the same activity, without process death, to exercise ON_STOP.
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 2
    TextNode 'Reading stopped. Tap Read explanation aloud to restart.' | Out-Null
    DescriptionNode 'AI teacher ready' | Out-Null
    $stop = (TextNode 'Stop reading').SelectSingleNode("ancestor-or-self::node[@clickable='true'][1]")
    if (-not $stop -or $stop.enabled -ne 'false') { throw 'Stop remains enabled after background cancellation' }
    Adb shell screencap -p /sdcard/qa-read-aloud-background.png | Out-Null
    Adb pull /sdcard/qa-read-aloud-background.png (Join-Path $repo 'artifacts\qa-read-aloud-background.png') | Out-Null
    TapText 'Read explanation aloud'
    TextNode 'Reading explanation…' | Out-Null
    TapText 'Stop reading'
    TextNode 'Reading stopped.' | Out-Null
    TapText 'Read explanation aloud'
    $finished = $false
    for ($speechWait = 0; $speechWait -lt 30; $speechWait++) {
        if ((Ui).SelectNodes('//node') | Where-Object text -eq 'Finished reading.') { $finished = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $finished) { throw 'Speech did not report completion within the bounded wait' }
    DescriptionNode 'AI teacher ready' | Out-Null
    Adb shell screencap -p /sdcard/qa-read-aloud-complete.png | Out-Null
    Adb pull /sdcard/qa-read-aloud-complete.png (Join-Path $repo 'artifacts\qa-read-aloud-complete.png') | Out-Null
    Write-Output 'PASS: accessible AI teacher follows real speaking/ready lifecycle; speech callbacks, background stop, explicit restart/stop and completion UI passed. Audible quality not verified.'
    return
}
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
if ($VerifyRejectedRewrite) {
    $beforeRewrite = Invoke-RestMethod $practicePath -Headers $practiceHeaders
    EnterField 0 'I do not know'
    TapText 'Submit my explanation'
    $rejectedState = Invoke-RestMethod $practicePath -Headers $practiceHeaders
    if ($rejectedState.status -ne 'tutor' -or $rejectedState.tutor.practice_prompt -eq $beforeRewrite.tutor.practice_prompt) { throw 'Rejected explanation did not return to tutor with fresh practice' }
    TextNode $rejectedState.tutor.explanation | Out-Null
    RestartApp
    TextNode $rejectedState.tutor.explanation | Out-Null
    $restoredRewrite = Invoke-RestMethod $practicePath -Headers $practiceHeaders
    if ($restoredRewrite.state_token -ne $rejectedState.state_token -or $restoredRewrite.tutor.practice_prompt -ne $rejectedState.tutor.practice_prompt) { throw 'Restart changed rejected-rewrite recovery state' }
    TapText 'I understand — practise now'
    TextNode $rejectedState.tutor.practice_prompt | Out-Null
    Adb shell screencap -p /sdcard/qa-rejected-rewrite.png | Out-Null
    Adb pull /sdcard/qa-rejected-rewrite.png (Join-Path $repo 'artifacts\qa-rejected-rewrite.png') | Out-Null
    $rewriteTerms = [regex]::Matches($rejectedState.tutor.practice_prompt, '(\d+)/(\d+)')
    if ($rewriteTerms.Count -ne 2 -or $rewriteTerms[0].Groups[2].Value -ne $rewriteTerms[1].Groups[2].Value) { throw 'Unexpected fresh addition shape after rejected explanation' }
    $rewriteNumerator = [int]$rewriteTerms[0].Groups[1].Value + [int]$rewriteTerms[1].Groups[1].Value
    EnterField 0 "$rewriteNumerator/$($rewriteTerms[0].Groups[2].Value)"
    TapText 'Check answer'
    TapText 'Explain it in your own words'
    Write-Output 'PASS: rejected explanation returns to tutoring with new saved practice; restart preserves coaching and the next answer returns to rewrite'
}
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
    if ($MalformedResponse) { TextNode $expectedError | Out-Null }
    else { TextPattern '^The learning service is temporarily unavailable\. Please try again\.\s+Support ID: [0-9a-f-]{36}$' | Out-Null }
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
    Write-Output "PASS: post-commit $faultMode response retains old submission state; identical retry replays Q3 without another answer"
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
if ($VerifyBadges) {
    TapText '‹ All subjects'
    TextNode 'Earned badges' | Out-Null
    foreach ($title in @('First answer', 'Learn from mistakes', 'Chapter master')) { TextNode $title | Out-Null }
    $badgeLogin = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail; password='qa-password-long-enough'} | ConvertTo-Json)
    $badgeDashboard = Invoke-RestMethod 'http://127.0.0.1:8000/v1/progress/dashboard?grade=8' -Headers @{Authorization="Bearer $($badgeLogin.access_token)"}
    $badgeIds = @($badgeDashboard.badges | ForEach-Object id)
    if (($badgeIds -join ',') -ne 'first_answer,learn_from_mistakes,chapter_master') { throw "Unexpected durable badge evidence: $($badgeIds -join ',')" }
    Adb shell screencap -p /sdcard/qa-learning-badges.png | Out-Null
    Adb pull /sdcard/qa-learning-badges.png (Join-Path $repo 'artifacts\qa-learning-badges.png') | Out-Null
    RestartApp
    foreach ($title in @('First answer', 'Learn from mistakes', 'Chapter master')) { TextNode $title | Out-Null }
    Write-Output 'PASS: three evidence-based badges match the owner-scoped server dashboard and survive process restart'
}
if ($VerifyWeeklyReport) {
    if (-not $VerifyBadges) { TapText '‹ All subjects' }
    TapText 'View my progress report'
    TextNode 'Uncalibrated heuristic, not a prediction of exam performance.' | Out-Null
    TextNode 'Learning responses' | Out-Null
    TextNode 'Unique chapters mastered' | Out-Null
    $reportLogin = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail; password='qa-password-long-enough'} | ConvertTo-Json)
    $report = Invoke-RestMethod 'http://127.0.0.1:8000/v1/progress/weekly-report?grade=8' -Headers @{Authorization="Bearer $($reportLogin.access_token)"}
    $expectedResponses = 5 + $(if ($VerifyFreshPractice) { 2 } else { 0 }) + $(if ($VerifyRejectedRewrite) { 2 } else { 0 })
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
    TapText 'View my progress report'
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
