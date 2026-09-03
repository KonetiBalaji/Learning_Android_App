param([string]$Serial = 'emulator-5554', [switch]$ResetTestAppData, [switch]$VerifyLibrary, [switch]$VerifyMultiChapter, [switch]$VerifyQuestionCount)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
$expectedCount = if ($VerifyQuestionCount) { 7 } else { 10 }
function Adb {
    & $adb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" }
}
function Ui {
    Adb shell uiautomator dump /sdcard/qa-document.xml | Out-Null
    [xml]((Adb shell cat /sdcard/qa-document.xml) -join "`n")
}
function Center($node) {
    $bounds = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($bounds[0]+$bounds[2])/2), [int](($bounds[1]+$bounds[3])/2))
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
    if ($fields.Count -le $index) { throw "Missing input $index" }
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
if (-not $ResetTestAppData) { throw 'Supply -ResetTestAppData for the dedicated QA emulator only.' }
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Not the dedicated QA emulator.' }
$health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
if ($health.ai_provider -notin @('deterministic','scripted-qa')) { throw 'Use the isolated QA backend.' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
Adb push (Join-Path $PSScriptRoot 'fixtures\qa-biology.txt') /sdcard/Download/qa-biology.txt | Out-Null
RestartApp
TapText 'New student? Create a private account'
$qaEmail = 'document-' + [Guid]::NewGuid().ToString('N') + '@example.com'
EnterField 0 $qaEmail
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
TapText "Grade`n8"
TapText 'Study from my own document'
TapText 'My uploaded documents'
TextNode 'No uploaded documents yet. Return to your study space to upload one.' | Out-Null
TapText '‹ Back to study space'
TapText 'Choose document'
$roots = (Ui).SelectNodes('//node') | Where-Object { $_.'content-desc' -eq 'Show roots' } | Select-Object -First 1
if (-not $roots) { throw 'Missing Android document-picker roots' }
$point = Center $roots
Adb shell input tap $point[0] $point[1] | Out-Null
$downloads = (Ui).SelectNodes('//node') | Where-Object { $_.text -eq 'Downloads' -and $_.'resource-id' -eq 'android:id/title' } | Select-Object -Last 1
if (-not $downloads) { throw 'Missing Downloads provider in picker drawer' }
$point = Center $downloads
Adb shell input tap $point[0] $point[1] | Out-Null
Start-Sleep -Milliseconds 900
TapText 'qa-biology.txt'
TapText 'Entire document'
TextNode '2 of 2 chapters selected' | Out-Null
RestartApp
TextNode '2 of 2 chapters selected' | Out-Null
TapText 'Clear selection'
RestartApp
TextNode '0 of 2 chapters selected' | Out-Null
$generate = TextNode 'Generate 10 questions'
# Disabled semantics may be merged into the text node or attached to its ancestor.
if ($generate.enabled -ne 'false' -and -not $generate.SelectSingleNode("ancestor::node[@enabled='false']")) { throw 'Generation is not marked disabled with no selected chapters' }
Write-Output 'PASS: entire-document and cleared selections survive restart; empty selection disables generation'
TapText 'Chapter 2 Plants'
if ($VerifyMultiChapter) { TapText 'Chapter 1 Cells' }
RestartApp
TextNode 'Choose chapters' | Out-Null
$login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
$headers = @{Authorization="Bearer $($login.access_token)"}
$documents = Invoke-RestMethod 'http://127.0.0.1:8000/v1/documents' -Headers $headers
if ($documents.Count -ne 1) { throw 'Expected exactly one uploaded document' }
$document = $documents[0]
$selectedChapter = $document.chapters | Where-Object title -eq 'Chapter 2 Plants'
[xml]$preferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
$chapterPointer = $preferences.map.ChildNodes | Where-Object name -eq "active_document_chapter:$qaEmail"
$selectedIds = @($chapterPointer.InnerText | ConvertFrom-Json)
if ($VerifyMultiChapter) {
    if ($selectedIds.Count -ne 2 -or @($document.chapters | Where-Object { $_.id -notin $selectedIds }).Count -ne 0) { throw 'Both selected chapter IDs were not restored' }
    TextNode '2 of 2 chapters selected' | Out-Null
} elseif ($selectedIds.Count -ne 1 -or $selectedIds[0] -ne $selectedChapter.id) { throw 'Chapter selection was not restored' }
Adb shell screencap -p /sdcard/qa-document-chapters.png | Out-Null
$selectionScreenshot = if ($VerifyMultiChapter) { 'artifacts\qa-document-multi-chapters.png' } else { 'artifacts\qa-document-chapters.png' }
Adb pull /sdcard/qa-document-chapters.png (Join-Path $repo $selectionScreenshot) | Out-Null
Write-Output 'PASS: real picker upload and selected chapter survive process restart, with one server document'
if ($VerifyQuestionCount) {
    foreach ($preset in @(5, 10, 15, 20)) {
        TapText "$preset"
        TextNode "Generate $preset questions" | Out-Null
    }
    EnterField 0 '21'
    TextNode 'Enter a whole number from 5 to 20.' | Out-Null
    $invalidGenerate = TextNode 'Generate quiz'
    if ($invalidGenerate.enabled -ne 'false' -and -not $invalidGenerate.SelectSingleNode("ancestor::node[@enabled='false']")) { throw 'Invalid question count did not disable generation' }
    EnterField 0 '7'
    RestartApp
    TextNode 'Generate 7 questions' | Out-Null
    Adb shell screencap -p /sdcard/qa-document-count.png | Out-Null
    Adb pull /sdcard/qa-document-count.png (Join-Path $repo 'artifacts\qa-document-count.png') | Out-Null
    Write-Output 'PASS: count presets update generation; invalid 21 is rejected; custom 7 survives restart'
}
TapText "Generate $expectedCount questions"
TextNode "QUESTION 1 OF $expectedCount" | Out-Null
RestartApp
TextNode "QUESTION 1 OF $expectedCount" | Out-Null
[xml]$preferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
$quizId = ($preferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail").InnerText
if (-not $quizId) { throw 'Quiz pointer is missing' }
if ($preferences.map.ChildNodes | Where-Object name -eq "active_document:$qaEmail") { throw 'Upload pointer was not replaced by quiz pointer' }
$quizPath = "http://127.0.0.1:8000/v1/quizzes/$quizId"
$state = Invoke-RestMethod $quizPath -Headers $headers
if ($state.total -ne $expectedCount) { throw 'Generated quiz total does not match requested count' }
if (-not $VerifyMultiChapter -and $state.question.source_reference -notlike 'Chapter 2 Plants*') { throw 'Selected chapter was not used after restart' }
$sourceReferences = [System.Collections.Generic.List[string]]::new()
$sourceReferences.Add($state.question.source_reference)
# Simulate another device answering the visible question with a different choice.
$question = $state.question
$winningChoice = $question.options[1]
Invoke-RestMethod "$quizPath/questions/$($question.id)/answer" -Method Post -Headers $headers -ContentType 'application/json' -Body (@{selected_option=$winningChoice} | ConvertTo-Json) | Out-Null
TapText $question.options[0]
TapText 'Check answer'
TextNode 'Study feedback' | Out-Null
$state = Invoke-RestMethod $quizPath -Headers $headers
if ($state.answered -ne 1 -or $state.last_feedback.selected_option -ne $winningChoice) { throw 'Conflict overwrote the committed answer' }
RestartApp
TextNode 'Study feedback' | Out-Null
TapText 'Next question'
TextNode "QUESTION 2 OF $expectedCount" | Out-Null
Adb shell screencap -p /sdcard/qa-document-resumed-question.png | Out-Null
Adb pull /sdcard/qa-document-resumed-question.png (Join-Path $repo 'artifacts\qa-document-resumed-question.png') | Out-Null
Write-Output 'PASS: quiz resumes after restart; conflicting answer refreshes saved feedback without overwriting it'
# Complete only this disposable quiz through the public API, then verify app restoration.
while ($state.question) {
    $question = $state.question
    $sourceReferences.Add($question.source_reference)
    Invoke-RestMethod "$quizPath/questions/$($question.id)/answer" -Method Post -Headers $headers -ContentType 'application/json' -Body (@{selected_option=$question.options[0]} | ConvertTo-Json) | Out-Null
    $state = Invoke-RestMethod $quizPath -Headers $headers
}
if ($VerifyMultiChapter) {
    if ($sourceReferences.Count -ne $expectedCount) { throw 'Expected source evidence for every requested question' }
    foreach ($chapter in $document.chapters) {
        if (-not ($sourceReferences | Where-Object { $_.StartsWith($chapter.title + ' (source characters ') })) { throw 'Generated quiz omitted a selected fixture chapter' }
    }
    if ($sourceReferences | Where-Object { $_ -notmatch '^Chapter [12] (Cells|Plants) \(source characters \d+-\d+\)$' }) { throw 'Unexpected source outside the selected fixture chapters' }
    Write-Output "PASS: Android multi-chapter generation produced $expectedCount questions with sources from both selected chapters"
}
RestartApp
TextNode 'Session complete' | Out-Null
Write-Output 'PASS: completed quiz restores results after restart (remaining answers submitted by API fixture)'
if ($VerifyLibrary) {
TapText 'Study another document'
TapText 'My uploaded documents'
TextNode 'qa-biology.txt' | Out-Null
Adb shell screencap -p /sdcard/qa-document-library.png | Out-Null
Adb pull /sdcard/qa-document-library.png (Join-Path $repo 'artifacts\qa-document-library.png') | Out-Null
TapText 'Open qa-biology.txt'
TextNode 'Choose chapters' | Out-Null
RestartApp
TextNode 'Choose chapters' | Out-Null
$documents = Invoke-RestMethod 'http://127.0.0.1:8000/v1/documents' -Headers $headers
if ($documents.Count -ne 1) { throw 'Opening the library unexpectedly duplicated the document' }
if ((Invoke-RestMethod $quizPath -Headers $headers).answered -ne $expectedCount) { throw 'Reopening material changed the previous quiz' }
Write-Output 'PASS: empty library is clear; saved material reopens without upload, survives restart and preserves the old quiz'
}
