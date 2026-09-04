param([string]$Serial = 'emulator-5554', [string]$BackendUrl = 'http://127.0.0.1:8000', [switch]$ResetTestAppData, [switch]$VerifyLibrary, [switch]$VerifyMultiChapter, [switch]$VerifyQuestionCount, [switch]$VerifyDifficulty, [switch]$VerifyQuestionType, [ValidateSet('true_false','yes_no')][string]$BinaryFixtureType, [switch]$VerifyCreationRetry, [switch]$VerifyStructureRepair, [switch]$VerifyPreview, [switch]$VerifyExcerpts, [switch]$VerifySourceSearch, [switch]$VerifySemanticSearch, [switch]$VerifyPdfPages, [switch]$VerifyUploadProgress, [switch]$VerifySavedUploadFailure, [switch]$VerifyResultActions, [switch]$VerifyDocumentProgress)
$ErrorActionPreference = 'Stop'
$BackendUrl = $BackendUrl.TrimEnd('/')
if ($BackendUrl -notmatch '^http://127\.0\.0\.1:\d{2,5}$') { throw 'Document QA backend must be an explicit loopback HTTP port' }
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
if ($VerifySavedUploadFailure) { $VerifyUploadProgress = $true }
if ($VerifyDocumentProgress) { $VerifyResultActions = $true }
if ($VerifyUploadProgress -and ($VerifyLibrary -or $VerifyMultiChapter -or $VerifyQuestionCount -or $VerifyDifficulty -or $VerifyQuestionType -or $BinaryFixtureType -or $VerifyCreationRetry -or $VerifyStructureRepair -or $VerifyPreview -or $VerifyExcerpts -or $VerifySourceSearch -or $VerifyPdfPages)) { throw 'Upload progress QA is a standalone check' }
if ($VerifySemanticSearch) { $VerifySourceSearch = $true }
if ($VerifySourceSearch) { $VerifyExcerpts = $true }
$fixtureName = if ($VerifyPdfPages) { 'page-boundary-fixture.pdf' } elseif ($VerifyPreview -or $VerifyExcerpts) { 'qa-preview-biology.txt' } else { 'qa-biology.txt' }
if ($VerifyPdfPages -and (-not $VerifyCreationRetry -or $VerifyExcerpts -or $VerifyPreview -or $VerifyMultiChapter -or $VerifyStructureRepair -or $VerifyQuestionCount -or $BinaryFixtureType)) { throw 'PDF page QA requires creation retry and cannot combine with other source fixture or question-count modes' }
$fixturePath = if ($VerifyPdfPages) { Join-Path $repo 'artifacts\tmp\pdfs\page-boundary-fixture.pdf' } else { Join-Path $PSScriptRoot "fixtures\$fixtureName" }
if (-not (Test-Path -LiteralPath $fixturePath)) { throw 'Missing QA fixture; for PDF pages run create-pdf-page-fixture.py with the documented output path first' }
if ($VerifyExcerpts -and (-not $VerifySemanticSearch) -and (-not $VerifyCreationRetry -or $VerifyPreview -or $VerifyMultiChapter -or $VerifyStructureRepair -or $BinaryFixtureType)) { throw 'Excerpt QA requires creation retry and cannot combine with preview, multi-chapter, repair or binary modes' }
if ($VerifyPreview -and (-not $VerifyCreationRetry -or $VerifyStructureRepair)) { throw 'Preview check requires creation retry and cannot combine with the legacy repair fixture' }
$expectedCount = if ($VerifyPdfPages) { 5 } elseif ($VerifyQuestionCount) { 7 } else { 10 }
$expectedFormat = if ($BinaryFixtureType) { $BinaryFixtureType } else { 'multiple_choice' }
$formatLabel = switch ($expectedFormat) { 'true_false' { 'True / False' } 'yes_no' { 'Yes / No' } default { 'Multiple choice' } }
if ($VerifyStructureRepair -and -not $VerifyCreationRetry) { throw 'Structure repair check requires -VerifyCreationRetry to verify pending identity preservation' }
if ($BinaryFixtureType -and ($VerifyQuestionType -or $VerifyDifficulty -or $VerifyMultiChapter)) { throw 'Binary fixture run cannot be combined with offline or source coverage checks' }
function Adb {
    & $adb -s $Serial @args
    if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" }
}
function Ui {
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        $dump = (Adb shell uiautomator dump /sdcard/qa-document.xml) -join "`n"
        if ($dump -match 'dumped to') { return [xml]((Adb shell cat /sdcard/qa-document.xml) -join "`n") }
        Start-Sleep -Milliseconds 500
    }
    throw 'Could not capture fresh document UI state'
}
function Center($node) {
    $bounds = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    @([int](($bounds[0]+$bounds[2])/2), [int](($bounds[1]+$bounds[3])/2))
}
function TextNode([string]$text) {
    # Long result screens can contain one source action per mistake. Sweep to
    # both ends so lookup does not oscillate around the middle of tall content.
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        $node = (Ui).SelectNodes('//node') | Where-Object {
            $_.text -eq $text -or $_.text -like "$text`n`nSupport ID: *"
        } | Select-Object -First 1
        if ($node) { return $node }
        if ($attempt -lt 15) { Adb shell input swipe 540 750 540 1850 400 | Out-Null }
        else { Adb shell input swipe 540 1850 540 750 400 | Out-Null }
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
function VerifyTalkBackSourceResult([string]$status) {
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
        # The result card can be taller than the viewport. Verify each semantic
        # node with the same bounded two-way scroll used by the rest of this QA.
        foreach ($label in @($status, 'Result 1: Chapter 2 Plants', 'Use passage 1 as excerpt')) {
            try { TextNode $label | Out-Null } catch { throw "TalkBack tree omitted source-result element: $label" }
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
function VerifyTalkBackResultActions([string]$retryLabel) {
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
        $nodes = @((Ui).SelectNodes('//node'))
        if (-not ($nodes | Where-Object { $_.text -match '^Which word completes.+\nYour answer: .+\nCorrect answer: .+\nWhy: .+\nSource: .+' })) { throw 'TalkBack tree omitted the complete mistake teaching record' }
        if (-not ($nodes | Where-Object { $_.text -match '^View source: .+\(source characters \d+-\d+\)$' })) { throw 'TalkBack tree omitted the source passage action' }
        foreach ($label in @($retryLabel, 'Configure another quiz', 'Increase to Medium', 'Study another document', 'Return to learning path')) {
            try { TextNode $label | Out-Null } catch { throw "TalkBack tree omitted result action after scrolling: $label" }
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
function SelectFixtureForUpload {
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
}
if (-not $ResetTestAppData) { throw 'Supply -ResetTestAppData for the dedicated QA emulator only.' }
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Not the dedicated QA emulator.' }
$health = Invoke-RestMethod "$BackendUrl/health"
if ($VerifySemanticSearch) {
    if ($health.ai_provider -ne 'openai') { throw 'Semantic-search QA requires the explicit OpenAI backend' }
} elseif ($BinaryFixtureType) {
    if ($health.ai_provider -ne 'scripted-binary-qa') { throw 'Use the explicit isolated binary fixture backend' }
} elseif ($health.ai_provider -notin @('deterministic','scripted-qa')) { throw 'Use the isolated QA backend.' }
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
Adb shell pm clear $package | Out-Null
Adb push $fixturePath "/sdcard/Download/$fixtureName" | Out-Null
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
SelectFixtureForUpload
if ($VerifyUploadProgress) {
    # Run the explicit QA server with --upload-response-delay 20. Small fixture
    # bytes transfer too quickly to claim visual percentage coverage.
    TextNode 'Waiting for document analysis…' | Out-Null
    TextNode 'The file was sent. Waiting for the service to validate it and detect chapters.' | Out-Null
    Adb shell screencap -p /sdcard/qa-upload-analysis-wait.png | Out-Null
    Adb pull /sdcard/qa-upload-analysis-wait.png (Join-Path $repo 'artifacts\qa-upload-analysis-wait.png') | Out-Null
    Start-Sleep -Seconds 20
}
if ($VerifySavedUploadFailure) {
    TextNode 'Upload could not be confirmed. Check My uploaded documents before trying again; the file may already be saved.' | Out-Null
    if ((Ui).SelectNodes('//node') | Where-Object text -eq 'Waiting for document analysis…') { throw 'Wait overlay remained behind upload error' }
    Adb shell screencap -p /sdcard/qa-upload-uncertain-error.png | Out-Null
    Adb pull /sdcard/qa-upload-uncertain-error.png (Join-Path $repo 'artifacts\qa-upload-uncertain-error.png') | Out-Null
    $savedPreferences = [xml]((Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n")
    $pendingUpload = ($savedPreferences.map.ChildNodes | Where-Object name -eq "pending_document_upload:$($qaEmail.ToLowerInvariant())").InnerText
    if ($pendingUpload -notmatch '^[0-9a-f-]{36}\|[0-9a-f]{64}$') { throw 'Durable pending upload identity was not saved before submission' }
    TapText 'Try again'
    SelectFixtureForUpload
    TextNode 'Waiting for document analysis…' | Out-Null
    Start-Sleep -Seconds 20
    TextNode 'Entire document' | Out-Null
    $completedPreferences = [xml]((Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n")
    if ($completedPreferences.map.ChildNodes | Where-Object name -eq "pending_document_upload:$($qaEmail.ToLowerInvariant())") { throw 'Completed upload identity was not cleared' }
    # The retry must replay the committed document instead of creating a duplicate.
    $login = Invoke-RestMethod "$BackendUrl/v1/auth/login" -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
    $saved = @(Invoke-RestMethod "$BackendUrl/v1/documents" -Headers @{Authorization="Bearer $($login.access_token)"})
    if ($saved.Count -ne 1) { throw 'Uncertain response created duplicate or missing documents' }
}
TapText 'Entire document'
TextNode '2 of 2 chapters selected' | Out-Null
if ($VerifyUploadProgress) {
    if ((Ui).SelectNodes('//node') | Where-Object text -eq 'Waiting for document analysis…') { throw 'Upload wait remained after success' }
    Adb shell screencap -p /sdcard/qa-upload-analysis-complete.png | Out-Null
    Adb pull /sdcard/qa-upload-analysis-complete.png (Join-Path $repo 'artifacts\qa-upload-analysis-complete.png') | Out-Null
    if ($VerifySavedUploadFailure) { Write-Output 'PASS: saved-upload 503 retains a durable request identity; explicit same-file retry replays one document, opens it, and clears the identity.' }
    else { Write-Output 'PASS: real picker upload shows analysis-wait copy during delayed response, then clears it and opens selectable chapters. Not transfer percentage or failure QA.' }
    return
}
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
$login = Invoke-RestMethod "$BackendUrl/v1/auth/login" -Method Post -ContentType 'application/json' -Body (@{email=$qaEmail;password='qa-password-long-enough'} | ConvertTo-Json)
$headers = @{Authorization="Bearer $($login.access_token)"}
$documents = Invoke-RestMethod "$BackendUrl/v1/documents" -Headers $headers
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
if ($VerifyPdfPages) {
    function EnterPage([string]$label, [string]$value) {
        TapText $label
        Adb shell input keycombination 113 29 | Out-Null
        Adb shell input text $value | Out-Null
        Adb shell input keyevent 4 | Out-Null
    }
    $excerptKey = "document_excerpts:$($document.id):$qaEmail"
    function AssertNoPageConfirmation {
        [xml]$pagePrefs = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
        if ($pagePrefs.map.ChildNodes | Where-Object name -eq $excerptKey) { throw 'PDF review changed selection before confirmation' }
        $pageIds = @(($pagePrefs.map.ChildNodes | Where-Object name -eq "active_document_chapter:$qaEmail").InnerText | ConvertFrom-Json)
        if (@(Compare-Object $selectedIds $pageIds).Count -ne 0) { throw 'PDF review changed checked chapters' }
    }
    TapText 'Load original PDF page index'
    TextNode '3 physical pages. Blank or scanned pages without extracted text cannot provide quiz content; OCR is not available.' | Out-Null
    EnterPage 'First physical PDF page' '3'
    EnterPage 'Last physical PDF page (inclusive)' '3'
    TapText 'Review original page range'
    TextNode 'These PDF pages have no extracted text. Choose pages with text; scanned pages need OCR, which is not available. Your selection is unchanged.' | Out-Null
    Adb shell screencap -p /sdcard/qa-pdf-empty-error.png | Out-Null
    Adb pull /sdcard/qa-pdf-empty-error.png (Join-Path $repo 'artifacts\qa-pdf-empty-error.png') | Out-Null
    AssertNoPageConfirmation
    TapText 'Try again'
    EnterPage 'First physical PDF page' '4'
    $reviewButton = TextNode 'Review original page range'
    if ($reviewButton.enabled -ne 'false' -and -not $reviewButton.SelectSingleNode("ancestor::node[@enabled='false']")) { throw 'Invalid PDF range did not disable review' }
    EnterPage 'First physical PDF page' '2'
    TapText 'Review original page range'
    TextNode 'Review pages 2 to 3. Your current selection has not changed.' | Out-Null
    TextNode 'No extracted text on pages: 3' | Out-Null
    AssertNoPageConfirmation
    EnterPage 'Last physical PDF page (inclusive)' '2'
    # Inspect the bottom of the form, where any stale confirmation would appear.
    TextNode 'Generate 10 questions' | Out-Null
    if ((Ui).SelectNodes('//node') | Where-Object text -eq 'Use these PDF pages instead of current selection') { throw 'Editing page input retained stale confirmation' }
    TapText 'Review original page range'
    $pageScope = Invoke-RestMethod "$BackendUrl/v1/documents/$($document.id)/pdf-pages/selection" -Method Post -Headers $headers -ContentType 'application/json' -Body '{"first_page":2,"last_page":2}'
    $excerptPart = $pageScope.source_ranges[0]
    if ($pageScope.source_ranges.Count -ne 1 -or $excerptPart.chapter_id -ne $selectedChapter.id) { throw 'PDF fixture did not resolve page 2 exclusively to Plants' }
    TextNode "Chapter 2 Plants: source characters $($excerptPart.start_character)–$($excerptPart.end_character)" | Out-Null
    AssertNoPageConfirmation
    Adb shell screencap -p /sdcard/qa-pdf-page-review.png | Out-Null
    Adb pull /sdcard/qa-pdf-page-review.png (Join-Path $repo 'artifacts\qa-pdf-page-review.png') | Out-Null
    TapText 'Use these PDF pages instead of current selection'
    Write-Output 'PASS: PDF blank-only range fails without selection changes; invalid input disables review; mixed blank warning and edited-review invalidation verified'
}
if ($VerifyExcerpts) {
    if ($VerifySourceSearch) {
        function SearchSource([string]$query) {
            TapText 'Topic or source phrase (2–120 characters)'
            Adb shell input keycombination 113 29 | Out-Null
            Adb shell input text ($query.Replace(' ', '%s')) | Out-Null
            Adb shell input keyevent 4 | Out-Null
            TapText 'Search selected chapters'
        }
        if ($VerifySemanticSearch) {
            $query = 'plant food production'
            SearchSource $query
            $expectedStatus = '1 semantically related source passage found. Verify the wording before using a passage as an excerpt.'
        } else {
            SearchSource 'zznomatchfixture'
            TextNode 'No relevant source passage was found. Try different words or chapters; no selection was changed.' | Out-Null
            [xml]$searchPrefs = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
            $afterSearchIds = @(($searchPrefs.map.ChildNodes | Where-Object name -eq "active_document_chapter:$qaEmail").InnerText | ConvertFrom-Json)
            if (@(Compare-Object $selectedIds $afterSearchIds).Count -ne 0) { throw 'No-match search changed selected chapters' }
            if ($searchPrefs.map.ChildNodes | Where-Object name -eq "document_excerpts:$($document.id):$qaEmail") { throw 'No-match search selected an excerpt' }
            $query = 'light photosynthesis'
            SearchSource $query
            $expectedSearch = Invoke-RestMethod "$BackendUrl/v1/documents/$($document.id)/search" -Method Post -Headers $headers -ContentType 'application/json' -Body (@{chapter_ids=@($selectedChapter.id); query=$query; limit=20} | ConvertTo-Json)
            if ($expectedSearch.match_mode -ne 'all_query_terms_case_insensitive') { throw 'Topic fixture did not exercise all-query-terms fallback' }
            $expectedStatus = '1 source passage found by all topic words. Read a passage before using it as an excerpt.'
        }
        if (-not $VerifySemanticSearch -and $expectedSearch.matches.Count -lt 1) { throw 'Search fixture did not return a source passage' }
        TextNode 'Result 1: Chapter 2 Plants' | Out-Null
        if (-not $VerifySemanticSearch) {
            $excerptPart = $expectedSearch.matches[0]
            TextNode "Source characters $($excerptPart.start_character)–$($excerptPart.end_character)" | Out-Null
        }
        VerifyTalkBackSourceResult $expectedStatus
        Adb shell screencap -p /sdcard/qa-source-search.png | Out-Null
        Adb pull /sdcard/qa-source-search.png (Join-Path $repo 'artifacts\qa-source-search.png') | Out-Null
        TapText 'Use passage 1 as excerpt'
        Write-Output 'PASS: no-match search preserves selection; multi-term topic passage and confirmation are exposed to TalkBack before explicit use'
    } else {
    $excerptPart = Invoke-RestMethod "$BackendUrl/v1/documents/$($document.id)/chapters/$($selectedChapter.id)/preview" -Headers $headers
    if ($excerptPart.total_pages -lt 2) { throw 'Excerpt fixture must leave some chapter text unselected' }
    TapText 'Preview: Chapter 2 Plants'
    TextNode 'Source preview' | Out-Null
    $sourceField = (Ui).SelectNodes('//node') | Where-Object { $_.class -eq 'android.widget.EditText' } | Select-Object -First 1
    if (-not $sourceField) { throw 'Missing read-only source selection field' }
    $point = Center $sourceField
    Adb shell input tap $point[0] $point[1] | Out-Null
    # Select the displayed source part through Android's text selection command,
    # not through an API or direct preference write.
    Adb shell input keycombination 113 29 | Out-Null
    TextNode "Selected source characters $($excerptPart.start_character)–$($excerptPart.end_character)" | Out-Null
    TapText 'Use highlighted excerpt instead of whole chapters'
    }
}
if ($VerifyExcerpts -or $VerifyPdfPages) {
    TextNode 'Excerpt mode: 1 selected text ranges only' | Out-Null
    [xml]$excerptPrefs = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $excerptKey = "document_excerpts:$($document.id):$qaEmail"
    $savedExcerpt = ($excerptPrefs.map.ChildNodes | Where-Object name -eq $excerptKey).InnerText
    if (-not $savedExcerpt) { throw 'Confirmed excerpt was not saved' }
    RestartApp
    TextNode 'Excerpt mode: 1 selected text ranges only' | Out-Null
    [xml]$restoredExcerpts = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if (($restoredExcerpts.map.ChildNodes | Where-Object name -eq $excerptKey).InnerText -ne $savedExcerpt) { throw 'Restart changed confirmed excerpt selection' }
    Adb shell screencap -p /sdcard/qa-document-excerpt.png | Out-Null
    Adb pull /sdcard/qa-document-excerpt.png (Join-Path $repo 'artifacts\qa-document-excerpt.png') | Out-Null
    Write-Output 'PASS: Android excerpt confirmation enters excerpt mode; saved boundaries survive restart'
    if ($VerifySemanticSearch) {
        Write-Output 'PASS: live semantic synonym result was reviewed, TalkBack-exposed, explicitly selected and restored after process restart'
        exit 0
    }
}
if ($VerifyPdfPages) {
    # This physical page has five distinct source sentences, not ten. Verify the
    # normal admission failure before choosing a count the source can support.
    TapText 'Generate 10 questions'
    TextNode 'This selection cannot support that many distinct questions. Choose fewer questions or select more source text. Your selection is unchanged.' | Out-Null
    Adb shell screencap -p /sdcard/qa-pdf-count-error.png | Out-Null
    Adb pull /sdcard/qa-pdf-count-error.png (Join-Path $repo 'artifacts\qa-pdf-count-error.png') | Out-Null
    TapText 'Try again'
    [xml]$shortPagePrefs = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if (($shortPagePrefs.map.ChildNodes | Where-Object name -eq $excerptKey).InnerText -ne $savedExcerpt) { throw 'Unsupported count changed PDF selection' }
    TapText '5'
    RestartApp
    TextNode 'Generate 5 questions' | Out-Null
    Write-Output 'PASS: insufficient page material rejects ten questions; exact selection survives and five-question count restores'
}
if ($VerifyCreationRetry) {
    $creationAudit = "$BackendUrl/__qa/documents/$($document.id)/created-quizzes"
    if (@((Invoke-RestMethod $creationAudit -Headers $headers).quiz_ids).Count -ne 0) { throw 'Expected no quiz before creation fault test' }
    Invoke-RestMethod "$BackendUrl/__qa/documents/$($document.id)/fail-next-creation-response" -Method Post -Headers $headers | Out-Null
    TapText "Generate $expectedCount questions"
    # The error surface is intentionally transient and may disappear while slow
    # UIAutomator dumps retry. Durable state plus the server audit proves the
    # client did not accept the substituted 503 response.
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
    $previewPath = "$BackendUrl/v1/documents/$($document.id)/chapters/$($selectedChapter.id)/preview"
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
    $beforeRepairQuiz = Invoke-RestMethod "$BackendUrl/v1/quizzes/$committedQuizId" -Headers $headers | ConvertTo-Json -Depth 20 -Compress
    Invoke-RestMethod "$BackendUrl/__qa/documents/$($document.id)/omit-tail-and-fail-repair-response" -Method Post -Headers $headers | Out-Null
    TapText 'Check for omitted text'
    TextNode 'The learning service is temporarily unavailable. Please try again.' | Out-Null
    TapText 'Try again'
    TextNode "$($selectedIds.Count) of 2 chapters selected" | Out-Null
    $repaired = Invoke-RestMethod "$BackendUrl/v1/documents/$($document.id)" -Headers $headers
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
    $afterRepairQuiz = Invoke-RestMethod "$BackendUrl/v1/quizzes/$committedQuizId" -Headers $headers | ConvertTo-Json -Depth 20 -Compress
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
$quizPath = "$BackendUrl/v1/quizzes/$quizId"
$state = Invoke-RestMethod $quizPath -Headers $headers
if ($VerifyExcerpts -or $VerifyPdfPages) {
    $ranges = @($state.source_ranges)
    if ($ranges.Count -ne 1 -or $ranges[0].chapter_id -ne $selectedChapter.id -or $ranges[0].start_character -ne $excerptPart.start_character -or $ranges[0].end_character -ne $excerptPart.end_character) { throw 'Recovered quiz changed the requested excerpt boundaries' }
    if ($preferences.map.ChildNodes | Where-Object name -eq $excerptKey) { throw 'Accepted quiz retained local pending excerpt metadata' }
    Write-Output 'PASS: committed-response failure and restart recover the same quiz with exact saved source boundaries'
}
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
$sourceButton = "View source: $($state.last_feedback.source_reference)"
TapText $sourceButton
TextNode 'Source passage' | Out-Null
$sourceEvidence = Invoke-RestMethod "$quizPath/questions/$($state.last_feedback.question_id)/source" -Headers $headers
$sourceTree = Ui
if (-not ($sourceTree.SelectNodes('//node') | Where-Object { $_.text -eq $sourceEvidence.text })) { throw 'Source dialog did not show the exact extracted evidence' }
if (-not ($sourceTree.SelectNodes('//node') | Where-Object { $_.text -eq "Exact extracted source characters $($sourceEvidence.start_character)–$($sourceEvidence.end_character). This is not AI-generated." })) { throw 'Source dialog did not identify the exact evidence range' }
if ($VerifyPdfPages) {
    $renderedPages = @($sourceEvidence.original_pdf_pages)
    if ($renderedPages.Count -ne 1 -or $renderedPages[0].page -ne 2 -or $renderedPages[0].mime_type -ne 'image/png') { throw 'Question source did not return its original physical PDF page' }
    TextNode 'Original PDF page 2' | Out-Null
    $sourceTree = Ui
    if (-not ($sourceTree.SelectNodes('//node') | Where-Object { $_.'content-desc' -eq 'Original PDF page 2' })) { throw 'Original PDF page image is not exposed to accessibility' }
}
Adb shell screencap -p /sdcard/qa-question-source.png | Out-Null
Adb pull /sdcard/qa-question-source.png (Join-Path $repo 'artifacts\qa-question-source.png') | Out-Null
TapText 'Close'
TextNode 'Study feedback' | Out-Null
TapText 'Next question'
TextNode "QUESTION 2 OF $expectedCount" | Out-Null
Adb shell screencap -p /sdcard/qa-document-resumed-question.png | Out-Null
Adb pull /sdcard/qa-document-resumed-question.png (Join-Path $repo 'artifacts\qa-document-resumed-question.png') | Out-Null
Write-Output 'PASS: quiz resumes after restart; conflicting answer refreshes saved feedback and opens its exact source without overwriting it'
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
    $third = $state.question
    TapText $third.options[0]
    TapText 'Check answer'
    TextNode 'Study feedback' | Out-Null
    $state = Invoke-RestMethod $quizPath -Headers $headers
    if ($state.answered -ne 3 -or $state.last_feedback.correct -ne $true -or $state.last_feedback.selected_option -ne $third.options[0]) { throw 'Correct binary Android answer or feedback was not committed' }
    RestartApp
    TextNode 'Study feedback' | Out-Null
    TapText 'Next question'
    TextNode "QUESTION 4 OF $expectedCount" | Out-Null
    Write-Output "PASS: Android $formatLabel correct answer commits; correct feedback and next question survive restart"
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
if ($VerifyExcerpts -or $VerifyPdfPages) {
    if ($sourceReferences.Count -ne $expectedCount) { throw 'Expected source evidence for every requested question' }
    foreach ($reference in $sourceReferences) {
        $match = [regex]::Match($reference, '^Chapter 2 Plants \(selected excerpt\) \(source characters (\d+)-(\d+)\)$')
        if (-not $match.Success -or [int]$match.Groups[1].Value -lt $excerptPart.start_character -or
            [int]$match.Groups[2].Value -gt $excerptPart.end_character -or
            [int]$match.Groups[1].Value -ge [int]$match.Groups[2].Value) {
            throw 'A quiz question referenced material outside the selected excerpt'
        }
    }
    Write-Output "PASS: all $expectedCount question references remain within the confirmed excerpt"
}
RestartApp
TextNode 'Session complete' | Out-Null
if ($VerifyQuestionType -or $BinaryFixtureType) { TextNode "Question type: $formatLabel" | Out-Null }
if ($VerifyDifficulty) { TextNode 'Requested difficulty: Easy · recall a fact' | Out-Null }
Write-Output 'PASS: completed quiz restores results after restart (remaining answers submitted by API fixture)'
if ($VerifyResultActions) {
    $completed = Invoke-RestMethod "$quizPath/results" -Headers $headers
    $mistakes = @($completed.mistakes)
    if ($mistakes.Count -lt 1) { throw 'Deterministic result fixture unexpectedly produced no mistakes' }
    $mistake = $mistakes[0]
    TextNode "Review question $($mistake.ordinal)" | Out-Null
    $teachingRecord = "$($mistake.prompt)`nYour answer: $($mistake.selected_option)`nCorrect answer: $($mistake.correct_option)`nWhy: $($mistake.explanation)`nSource: $($mistake.source_reference)"
    TextNode $teachingRecord | Out-Null
    $retryLabel = "Retry $($mistakes.Count) incorrect $(if ($mistakes.Count -eq 1) { 'question' } else { 'questions' })"
    TextNode $retryLabel | Out-Null
    TextNode 'Configure another quiz' | Out-Null
    TextNode 'Increase to Medium' | Out-Null
    VerifyTalkBackResultActions $retryLabel
    Adb shell screencap -p /sdcard/qa-document-result-actions.png | Out-Null
    Adb pull /sdcard/qa-document-result-actions.png (Join-Path $repo 'artifacts\qa-document-result-actions.png') | Out-Null

    TapText $retryLabel
    TextNode "QUESTION 1 OF $($mistakes.Count)" | Out-Null
    [xml]$retryPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $retryQuizId = ($retryPreferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail").InnerText
    if (-not $retryQuizId -or $retryQuizId -eq $quizId) { throw 'Retry action did not persist a fresh active quiz' }
    if ($retryPreferences.map.ChildNodes | Where-Object name -eq "pending_mistake_retry:$($quizId):$qaEmail") { throw 'Accepted retry retained its pending request identity' }
    $retryPath = "$BackendUrl/v1/quizzes/$retryQuizId"
    $retryState = Invoke-RestMethod $retryPath -Headers $headers
    if ($retryState.total -ne $mistakes.Count -or $retryState.answered -ne 0) { throw 'Retry quiz does not contain fresh unanswered mistakes only' }
    RestartApp
    TextNode "QUESTION 1 OF $($mistakes.Count)" | Out-Null
    while ($retryState.question) {
        $retryQuestion = $retryState.question
        Invoke-RestMethod "$retryPath/questions/$($retryQuestion.id)/answer" -Method Post -Headers $headers -ContentType 'application/json' -Body (@{selected_option=$retryQuestion.options[0]} | ConvertTo-Json) | Out-Null
        $retryState = Invoke-RestMethod $retryPath -Headers $headers
    }
    RestartApp
    TextNode 'Session complete' | Out-Null
    TapText 'Configure another quiz'
    TextNode 'Choose chapters' | Out-Null
    TextNode '1 of 2 chapters selected' | Out-Null
    if ((Invoke-RestMethod $quizPath -Headers $headers).answered -ne $expectedCount) { throw 'Configuring another quiz changed the completed source quiz' }

    TapText 'Generate 10 questions'
    TextNode 'QUESTION 1 OF 10' | Out-Null
    [xml]$nextPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $nextQuizId = ($nextPreferences.map.ChildNodes | Where-Object name -eq "active_document_quiz:$qaEmail").InnerText
    $nextPath = "$BackendUrl/v1/quizzes/$nextQuizId"
    $nextState = Invoke-RestMethod $nextPath -Headers $headers
    while ($nextState.question) {
        $nextQuestion = $nextState.question
        Invoke-RestMethod "$nextPath/questions/$($nextQuestion.id)/answer" -Method Post -Headers $headers -ContentType 'application/json' -Body (@{selected_option=$nextQuestion.options[0]} | ConvertTo-Json) | Out-Null
        $nextState = Invoke-RestMethod $nextPath -Headers $headers
    }
    RestartApp
    TextNode 'Session complete' | Out-Null
    TapText 'Increase to Medium'
    TextNode 'Choose chapters' | Out-Null
    TextNode 'Medium · apply a principle' | Out-Null
    if ($VerifyDocumentProgress) {
        $progress = Invoke-RestMethod "$BackendUrl/v1/documents/$($document.id)/progress" -Headers $headers
        if ($progress.quizzes_created -ne 3 -or $progress.quizzes_completed -ne 3) { throw 'Document progress omitted completed quiz attempts' }
        if ($progress.questions_answered -ne ($expectedCount + $mistakes.Count + 10)) { throw 'Document progress answer total is incorrect' }
        if (@($progress.attempts | Where-Object { -not $_.complete -or -not $_.completed_at }).Count -ne 0) { throw 'Completed attempt history lacks completion evidence' }
        $retryAttempt = $progress.attempts | Where-Object quiz_id -eq $retryQuizId | Select-Object -First 1
        if (-not $retryAttempt -or $retryAttempt.retry_of -ne $quizId) { throw 'Retry attempt provenance is missing from document history' }
        $accuracyPercent = [int][Math]::Truncate([double]$progress.accuracy * 100)
        TextNode "$($progress.quizzes_completed) completed quizzes • $($progress.questions_answered) answers • $accuracyPercent% accuracy" | Out-Null
        $trendText = switch ($progress.trend) {
            'improving' { "Improving by $([int]$progress.improvement_percentage_points) percentage points since your previous completed quiz" }
            'declining' { "Down $([Math]::Abs([int]$progress.improvement_percentage_points)) percentage points since your previous completed quiz" }
            'steady' { 'Accuracy is steady since your previous completed quiz' }
            default { throw 'Three completed attempts produced no document improvement trend' }
        }
        TextNode $trendText | Out-Null
        if (@($progress.chapters).Count -ne @($document.chapters).Count) { throw 'Document progress omitted a detected chapter' }
        if (($progress.chapters | Measure-Object questions_answered -Sum).Sum -ne $progress.questions_answered) { throw 'Chapter totals do not reconcile with document totals' }
        foreach ($chapter in $progress.chapters) {
            $chapterText = if ($null -eq $chapter.accuracy) { "$($chapter.title) • Not started" } else {
                "$($chapter.title) • $([int][Math]::Truncate([double]$chapter.accuracy * 100))% accuracy from $($chapter.questions_answered) answers"
            }
            TextNode $chapterText | Out-Null
        }
        if (@($progress.weak_concepts).Count -eq 0 -or @($progress.strongest_concepts).Count -eq 0) { throw 'Grounded concept evidence is missing' }
        TextNode "Review next: $($progress.weak_concepts[0])" | Out-Null
        TextNode "Strongest concept: $($progress.strongest_concepts[0])" | Out-Null
        Adb shell screencap -p /sdcard/qa-document-progress.png | Out-Null
        Adb pull /sdcard/qa-document-progress.png (Join-Path $repo 'artifacts\qa-document-progress.png') | Out-Null
        Write-Output 'PASS: Android displays reconciled chapter accuracy, grounded concepts and multi-attempt improvement evidence'
    }
    [xml]$difficultyPreferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    if (($difficultyPreferences.map.ChildNodes | Where-Object name -eq "document_difficulty:$qaEmail").InnerText -ne 'medium') { throw 'Increased difficulty was not persisted' }
    Adb shell screencap -p /sdcard/qa-document-increased-difficulty.png | Out-Null
    Adb pull /sdcard/qa-document-increased-difficulty.png (Join-Path $repo 'artifacts\qa-document-increased-difficulty.png') | Out-Null
    Write-Output 'PASS: result teaching record, mistake-only retry, restart, configure-another and persisted difficulty increase work through Android'
}
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
$documents = Invoke-RestMethod "$BackendUrl/v1/documents" -Headers $headers
if ($documents.Count -ne 1) { throw 'Opening the library unexpectedly duplicated the document' }
if ((Invoke-RestMethod $quizPath -Headers $headers).answered -ne $expectedCount) { throw 'Reopening material changed the previous quiz' }
Write-Output 'PASS: empty library is clear; saved material reopens without upload, survives restart and preserves the old quiz'
}
