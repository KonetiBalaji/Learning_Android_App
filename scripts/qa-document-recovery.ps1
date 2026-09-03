param([string]$Serial = 'emulator-5554', [switch]$ResetTestAppData, [switch]$VerifyLibrary, [switch]$VerifyMultiChapter, [switch]$VerifyQuestionCount, [switch]$VerifyDifficulty, [switch]$VerifyQuestionType, [ValidateSet('true_false','yes_no')][string]$BinaryFixtureType, [switch]$VerifyCreationRetry, [switch]$VerifyStructureRepair, [switch]$VerifyPreview)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
$fixtureName = if ($VerifyPreview) { 'qa-preview-biology.txt' } else { 'qa-biology.txt' }
if ($VerifyPreview -and (-not $VerifyCreationRetry -or $VerifyStructureRepair)) { throw 'Preview check requires creation retry and cannot combine with the legacy repair fixture' }
$expectedCount = if ($VerifyQuestionCount) { 7 } else { 10 }
$expectedFormat = if ($BinaryFixtureType) { $BinaryFixtureType } else { 'multiple_choice' }
$formatLabel = switch ($expectedFormat) { 'true_false' { 'True / False' } 'yes_no' { 'Yes / No' } default { 'Multiple choice' } }
if ($VerifyStructureRepair -and -not $VerifyCreationRetry) { throw 'Structure repair check requires -VerifyCreationRetry to verify pending identity preservation' }
if ($BinaryFixtureType -and ($VerifyQuestionType -or $VerifyDifficulty -or $VerifyMultiChapter)) { throw 'Binary fixture run cannot be combined with offline or source coverage checks' }
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
    for ($attempt=0; $attempt -lt 10; $attempt++) {
        $node = (Ui).SelectNodes('//node') | Where-Object { $_.text -eq $text } | Select-Object -First 1
        if ($node) { return $node }
        if ($attempt -lt 4) { Adb shell input swipe 540 1850 540 750 400 | Out-Null }
        else { Adb shell input swipe 540 750 540 1850 400 | Out-Null }
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
if ($BinaryFixtureType) {
    if ($health.ai_provider -ne 'scripted-binary-qa') { throw 'Use the explicit isolated binary fixture backend' }
} elseif ($health.ai_provider -notin @('deterministic','scripted-qa')) { throw 'Use the isolated QA backend.' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
Adb push (Join-Path $PSScriptRoot "fixtures\$fixtureName") "/sdcard/Download/$fixtureName" | Out-Null
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
TapText $fixtureName
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
if ($VerifyDifficulty) {
    TapText 'Hard · combine facts'
    RestartApp
    $hard = TextNode 'Hard · combine facts'
    if ($hard.checked -ne 'true' -and -not $hard.SelectSingleNode("ancestor::node[@checked='true']")) { throw 'Hard difficulty did not restore as selected' }
    TapText "Generate $expectedCount questions"
    TextNode 'Please check your input or selected document and try again.' | Out-Null
    TapText 'Try again'
    [xml]$failedPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if ($failedPreferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail") { throw 'Unsupported difficulty created a quiz pointer' }
    TapText 'Easy · recall a fact'
    Write-Output 'PASS: Hard preference restores; offline generation rejects it; learner can change to Easy'
}
if ($VerifyQuestionType) {
    foreach ($format in @(@{value='true_false';label='True / False'}, @{value='yes_no';label='Yes / No'})) {
        TapText $format.label
        RestartApp
        $selectedFormat = TextNode $format.label
        if ($selectedFormat.checked -ne 'true' -and -not $selectedFormat.SelectSingleNode("ancestor::node[@checked='true']")) { throw 'Question format did not restore as selected' }
        [xml]$formatPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
        $savedFormat = ($formatPreferences.map.ChildNodes | Where-Object name -eq "document_question_type:$qaEmail").InnerText
        if ($savedFormat -ne $format.value) { throw 'Stored format does not match selection' }
        Adb shell screencap -p /sdcard/qa-document-format.png | Out-Null
        Adb pull /sdcard/qa-document-format.png (Join-Path $repo "artifacts\qa-document-format-$($format.value).png") | Out-Null
        TapText "Generate $expectedCount questions"
        TextNode 'Please check your input or selected document and try again.' | Out-Null
        TapText 'Try again'
        [xml]$failedPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
        if ($failedPreferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail") { throw 'Unsupported binary format created a quiz pointer' }
        Write-Output "PASS: $($format.label) restores selection and is safely rejected by offline generation"
    }
    TapText 'Multiple choice'
}
if ($BinaryFixtureType) { TapText $formatLabel }
if ($VerifyCreationRetry) {
    $creationAudit = "http://127.0.0.1:8000/__qa/documents/$($document.id)/created-quizzes"
    if (@((Invoke-RestMethod $creationAudit -Headers $headers).quiz_ids).Count -ne 0) { throw 'Expected no quiz before creation fault test' }
    Invoke-RestMethod "http://127.0.0.1:8000/__qa/documents/$($document.id)/fail-next-creation-response" -Method Post -Headers $headers | Out-Null
    TapText "Generate $expectedCount questions"
    TextNode 'The learning service is temporarily unavailable. Please try again.' | Out-Null
    [xml]$failedCreationPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $pendingCreation = ($failedCreationPreferences.map.ChildNodes | Where-Object name -eq "pending_quiz_creation:$qaEmail").InnerText
    if (-not $pendingCreation -or $pendingCreation -notmatch '^[0-9a-f-]{36}\|[0-9a-f]{64}$') { throw 'Creation request identity was not persisted' }
    if ($failedCreationPreferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail") { throw 'Failed response was prematurely accepted' }
    $committedIds = @((Invoke-RestMethod $creationAudit -Headers $headers).quiz_ids)
    if ($committedIds.Count -ne 1) { throw 'Expected exactly one committed quiz behind failed response' }
    $committedQuizId = $committedIds[0]
    RestartApp
    TextNode 'Choose chapters' | Out-Null
    [xml]$restoredCreationPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if (($restoredCreationPreferences.map.ChildNodes | Where-Object name -eq "pending_quiz_creation:$qaEmail").InnerText -ne $pendingCreation) { throw 'Creation identity changed across restart' }
    Write-Output 'PASS: committed creation returns 503; pending identity survives restart without accepting the failed response'
}
if ($VerifyPreview) {
    $previewPath = "http://127.0.0.1:8000/v1/documents/$($document.id)/chapters/$($selectedChapter.id)/preview"
    $firstPart = Invoke-RestMethod $previewPath -Headers $headers
    if ($firstPart.total_pages -lt 2) { throw 'Preview fixture must exercise pagination' }
    TapText 'Preview: Chapter 2 Plants'
    TextNode 'Source preview' | Out-Null
    TextNode "Part 1 of $($firstPart.total_pages) · Characters $($firstPart.start_character)–$($firstPart.end_character)" | Out-Null
    TextNode ($firstPart.text.Replace("`r`n", "`n")) | Out-Null
    $previous = TextNode 'Previous part'
    if ($previous.enabled -ne 'false' -and -not $previous.SelectSingleNode("ancestor::node[@enabled='false']")) { throw 'Previous part should be disabled on the first part' }
    for ($part = 1; $part -lt $firstPart.total_pages; $part++) {
        TapText 'Next part'
        $expectedPart = Invoke-RestMethod "$($previewPath)?page=$part" -Headers $headers
        TextNode "Part $($part + 1) of $($firstPart.total_pages) · Characters $($expectedPart.start_character)–$($expectedPart.end_character)" | Out-Null
        TextNode ($expectedPart.text.Replace("`r`n", "`n")) | Out-Null
    }
    $next = TextNode 'Next part'
    if ($next.enabled -ne 'false' -and -not $next.SelectSingleNode("ancestor::node[@enabled='false']")) { throw 'Next part should be disabled on the final part' }
    Adb shell screencap -p /sdcard/qa-source-preview.png | Out-Null
    Adb pull /sdcard/qa-source-preview.png (Join-Path $repo 'artifacts\qa-source-preview.png') | Out-Null
    for ($part = $firstPart.total_pages - 2; $part -ge 0; $part--) { TapText 'Previous part' }
    TextNode ($firstPart.text.Replace("`r`n", "`n")) | Out-Null
    TapText '‹ Back to chapter selection'
    TextNode "$($selectedIds.Count) of 2 chapters selected" | Out-Null
    TapText 'Preview: Chapter 2 Plants'
    RestartApp
    TextNode 'Choose chapters' | Out-Null
    [xml]$previewPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if (($previewPreferences.map.ChildNodes | Where-Object name -eq "pending_quiz_creation:$qaEmail").InnerText -ne $pendingCreation) { throw 'Preview changed pending creation identity' }
    $previewSelection = @(($previewPreferences.map.ChildNodes | Where-Object name -eq "active_document_chapter:$qaEmail").InnerText | ConvertFrom-Json)
    if (@(Compare-Object $selectedIds $previewSelection).Count -ne 0) { throw 'Preview changed selection' }
    Write-Output 'PASS: exact source preview parts and boundary buttons verified; backward navigation, return and restart preserve selection and pending quiz identity'
}
if ($VerifyStructureRepair) {
    $beforeRepairQuiz = Invoke-RestMethod "http://127.0.0.1:8000/v1/quizzes/$committedQuizId" -Headers $headers | ConvertTo-Json -Depth 20 -Compress
    Invoke-RestMethod "http://127.0.0.1:8000/__qa/documents/$($document.id)/omit-tail-and-fail-repair-response" -Method Post -Headers $headers | Out-Null
    TapText 'Check for omitted text'
    TextNode 'The learning service is temporarily unavailable. Please try again.' | Out-Null
    TapText 'Try again'
    TextNode "$($selectedIds.Count) of 2 chapters selected" | Out-Null
    $repaired = Invoke-RestMethod "http://127.0.0.1:8000/v1/documents/$($document.id)" -Headers $headers
    if ($repaired.chapters.Count -ne 3) { throw 'Repair did not commit the omitted range behind the failed response' }
    TapText 'Check for omitted text'
    TextNode '1 omitted text ranges added, not selected. Review them before adding them to your quiz.' | Out-Null
    TextNode "$($selectedIds.Count) of 3 chapters selected" | Out-Null
    TextNode 'Low-confidence text range: review before selecting' | Out-Null
    Adb shell screencap -p /sdcard/qa-structure-repair.png | Out-Null
    Adb pull /sdcard/qa-structure-repair.png (Join-Path $repo 'artifacts\qa-structure-repair.png') | Out-Null
    RestartApp
    TextNode "$($selectedIds.Count) of 3 chapters selected" | Out-Null
    TapText 'Check for omitted text'
    TextNode 'No omitted text ranges found. Your selection is unchanged.' | Out-Null
    [xml]$repairPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if (($repairPreferences.map.ChildNodes | Where-Object name -eq "pending_quiz_creation:$qaEmail").InnerText -ne $pendingCreation) { throw 'Repair changed pending quiz identity' }
    $repairSelection = @(($repairPreferences.map.ChildNodes | Where-Object name -eq "active_document_chapter:$qaEmail").InnerText | ConvertFrom-Json)
    if (@(Compare-Object $selectedIds $repairSelection).Count -ne 0) { throw 'Repair changed selected chapter IDs' }
    $afterRepairQuiz = Invoke-RestMethod "http://127.0.0.1:8000/v1/quizzes/$committedQuizId" -Headers $headers | ConvertTo-Json -Depth 20 -Compress
    # The quiz response embeds the current document, so compare its question and progress separately.
    $beforeQuizState = $beforeRepairQuiz | ConvertFrom-Json
    $afterQuizState = $afterRepairQuiz | ConvertFrom-Json
    if (($beforeQuizState.question | ConvertTo-Json -Depth 20 -Compress) -ne ($afterQuizState.question | ConvertTo-Json -Depth 20 -Compress) -or $beforeQuizState.answered -ne $afterQuizState.answered) { throw 'Repair changed the existing quiz question or progress' }
    Write-Output 'PASS: committed repair 503 recovered; unselected range and original selection survive restart; pending quiz identity and question unchanged'
}
TapText "Generate $expectedCount questions"
TextNode "QUESTION 1 OF $expectedCount" | Out-Null
RestartApp
TextNode "QUESTION 1 OF $expectedCount" | Out-Null
[xml]$preferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
$quizId = ($preferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail").InnerText
if (-not $quizId) { throw 'Quiz pointer is missing' }
if ($VerifyCreationRetry) {
    if ($quizId -ne $committedQuizId) { throw 'Creation retry opened a different quiz' }
    if ($preferences.map.ChildNodes | Where-Object name -eq "pending_quiz_creation:$qaEmail") { throw 'Accepted quiz retained pending identity' }
    $afterRetryIds = @((Invoke-RestMethod $creationAudit -Headers $headers).quiz_ids)
    if ($afterRetryIds.Count -ne 1 -or $afterRetryIds[0] -ne $quizId) { throw 'Creation retry duplicated the saved quiz' }
    Adb shell screencap -p /sdcard/qa-creation-retry.png | Out-Null
    Adb pull /sdcard/qa-creation-retry.png (Join-Path $repo 'artifacts\qa-creation-retry.png') | Out-Null
    Write-Output 'PASS: retry resumes the original quiz; exactly one server quiz exists and pending identity is cleared'
}
if ($preferences.map.ChildNodes | Where-Object name -eq "active_document:$qaEmail") { throw 'Upload pointer was not replaced by quiz pointer' }
$quizPath = "http://127.0.0.1:8000/v1/quizzes/$quizId"
$state = Invoke-RestMethod $quizPath -Headers $headers
if ($VerifyQuestionType -or $BinaryFixtureType) {
    if ($state.question_type -ne $expectedFormat -or $state.question.question_type -ne $expectedFormat) { throw 'Saved quiz format differs from the selected format' }
    TextNode "Question type: $formatLabel" | Out-Null
    if ($BinaryFixtureType -and $state.question.options.Count -ne 2) { throw 'Expected exactly two answer choices' }
}
if ($VerifyDifficulty) {
    if ($state.difficulty -ne 'easy') { throw 'Saved quiz difficulty is not Easy' }
    TextNode 'Requested difficulty: Easy · recall a fact' | Out-Null
    Adb shell screencap -p /sdcard/qa-document-difficulty.png | Out-Null
    Adb pull /sdcard/qa-document-difficulty.png (Join-Path $repo 'artifacts\qa-document-difficulty.png') | Out-Null
}
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
if ($BinaryFixtureType) {
    $second = $state.question
    TapText $second.options[0]
    TapText 'Check answer'
    TextNode 'Study feedback' | Out-Null
    $state = Invoke-RestMethod $quizPath -Headers $headers
    if ($state.answered -ne 2 -or $state.last_feedback.correct -ne $false -or $state.last_feedback.correct_option -ne $second.options[1]) { throw 'Binary Android answer or feedback was incorrect' }
    RestartApp
    TextNode 'Study feedback' | Out-Null
    TapText 'Next question'
    TextNode "QUESTION 3 OF $expectedCount" | Out-Null
    TextNode "Question type: $formatLabel" | Out-Null
    Adb shell screencap -p /sdcard/qa-binary-question.png | Out-Null
    Adb pull /sdcard/qa-binary-question.png (Join-Path $repo "artifacts\qa-binary-$BinaryFixtureType.png") | Out-Null
    Write-Output "PASS: Android $formatLabel answer commits; wrong-answer feedback and next question survive restart"
}
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
if ($VerifyQuestionType -or $BinaryFixtureType) { TextNode "Question type: $formatLabel" | Out-Null }
if ($VerifyDifficulty) { TextNode 'Requested difficulty: Easy · recall a fact' | Out-Null }
Write-Output 'PASS: completed quiz restores results after restart (remaining answers submitted by API fixture)'
if ($VerifyLibrary) {
TapText 'Study another document'
TapText 'My uploaded documents'
TextNode $fixtureName | Out-Null
Adb shell screencap -p /sdcard/qa-document-library.png | Out-Null
Adb pull /sdcard/qa-document-library.png (Join-Path $repo 'artifacts\qa-document-library.png') | Out-Null
TapText "Open $fixtureName"
TextNode 'Choose chapters' | Out-Null
RestartApp
TextNode 'Choose chapters' | Out-Null
$documents = Invoke-RestMethod 'http://127.0.0.1:8000/v1/documents' -Headers $headers
if ($documents.Count -ne 1) { throw 'Opening the library unexpectedly duplicated the document' }
if ((Invoke-RestMethod $quizPath -Headers $headers).answered -ne $expectedCount) { throw 'Reopening material changed the previous quiz' }
Write-Output 'PASS: empty library is clear; saved material reopens without upload, survives restart and preserves the old quiz'
}
