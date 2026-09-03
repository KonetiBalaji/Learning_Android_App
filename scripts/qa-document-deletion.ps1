# Requires the disposable account left by qa-document-recovery.ps1 -VerifyLibrary.
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb {
    & $adb -s emulator-5554 @args
    if ($LASTEXITCODE -ne 0) { throw 'ADB failed' }
}
function Ui {
    Adb shell uiautomator dump /sdcard/qa-delete.xml | Out-Null
    [xml]((Adb shell cat /sdcard/qa-delete.xml) -join "`n")
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
    $node = TextNode $text
    $b = [regex]::Matches($node.bounds, '\d+') | ForEach-Object { [int]$_.Value }
    Adb shell input tap ([int](($b[0]+$b[2])/2)) ([int](($b[1]+$b[3])/2)) | Out-Null
    Start-Sleep -Milliseconds 900
}
function RestartApp {
    Adb shell am force-stop $package | Out-Null
    Adb shell am start -n "$package/.MainActivity" | Out-Null
    Start-Sleep -Seconds 3
}
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Not the QA AVD' }
if ((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider -notin @('deterministic','scripted-qa')) { throw 'Not the isolated QA backend' }
[xml]$prefs = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
$email = ($prefs.map.ChildNodes | Where-Object name -eq 'email').InnerText
if ($email -notmatch '^document-[a-f0-9]{32}@example\.com$') { throw 'Not a disposable document QA account' }
$login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$email;password='qa-password-long-enough'} | ConvertTo-Json)
$headers = @{Authorization="Bearer $($login.access_token)"}
$documents = Invoke-RestMethod 'http://127.0.0.1:8000/v1/documents' -Headers $headers
if ($documents.Count -ne 1 -or $documents[0].original_name -ne 'qa-biology.txt') { throw 'Expected exactly one synthetic biology fixture' }
$id = $documents[0].id
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk') | Out-Null
RestartApp
TapText '‹ Back to study space'
TapText 'My uploaded documents'
TapText 'Delete qa-biology.txt'
TextNode 'Delete this document?' | Out-Null
TapText 'Cancel'
if ((Invoke-RestMethod "http://127.0.0.1:8000/v1/documents/$id" -Headers $headers).id -ne $id) { throw 'Cancel removed the document' }
TapText 'Delete qa-biology.txt'
TapText 'Delete document permanently'
TextNode 'No uploaded documents yet. Return to your study space to upload one.' | Out-Null
$remaining = Invoke-RestMethod 'http://127.0.0.1:8000/v1/documents' -Headers $headers
if ($remaining.Count -ne 0) { throw 'Deleted document remained in server library' }
RestartApp
TapText 'Study from my own document'
TapText 'My uploaded documents'
TextNode 'No uploaded documents yet. Return to your study space to upload one.' | Out-Null
Adb shell screencap -p /sdcard/qa-deleted-document.png | Out-Null
Adb pull /sdcard/qa-deleted-document.png (Join-Path $repo 'artifacts\qa-deleted-document.png') | Out-Null
Write-Output 'PASS: cancel preserves the fixture; confirmed deletion removes it; restart does not restore deleted material'
