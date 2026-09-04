param(
    [switch]$ResetTestAppData,
    [switch]$VerifyTalkBack,
    [string[]]$Route = @()
)
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
        if (((Adb shell uiautomator dump /sdcard/qa-chapter-explorers.xml) -join '') -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-chapter-explorers.xml) -join "`n")
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
    $attempt = 0
    do {
        $node = (Ui).SelectNodes('//node') | Where-Object text -eq $text | Select-Object -First 1
        if ($node) { return $node }
        if ($Scroll) {
            if (($attempt % 8) -lt 5) { Adb shell input swipe 540 1900 540 650 350 | Out-Null }
            else { Adb shell input swipe 540 650 540 1900 350 | Out-Null }
            $attempt++
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $until)
    throw "UI text not found: $text"
}
function TapText([string]$text, [int]$seconds = 30, [switch]$Scroll) {
    $point = Center (FindText $text $seconds -Scroll:$Scroll)
    Adb shell input tap $point[0] $point[1] | Out-Null
    Start-Sleep -Milliseconds 800
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
function VerifyTalkBackExplorer([string]$heading, [string]$selected, [string]$descriptionPattern) {
    $oldServices = ((Adb shell settings get secure enabled_accessibility_services) -join '').Trim()
    $oldEnabled = ((Adb shell settings get secure accessibility_enabled) -join '').Trim()
    $talkBackPackage = 'com.google.android.marvin.talkback'
    $notificationPermission = 'android.permission.POST_NOTIFICATIONS'
    if (-not ((Adb shell pm path $talkBackPackage) -join '')) { throw 'TalkBack is not installed on the dedicated QA emulator.' }
    $notificationWasGranted = ((& $adb -s emulator-5554 shell cmd package check-permission $notificationPermission $talkBackPackage) -join '').Trim() -eq 'granted'
    try {
        if (-not $notificationWasGranted) { Adb shell pm grant $talkBackPackage $notificationPermission | Out-Null }
        Adb shell settings put secure enabled_accessibility_services "$talkBackPackage/$talkBackPackage.TalkBackService" | Out-Null
        Adb shell settings put secure accessibility_enabled 1 | Out-Null
        Start-Sleep -Seconds 2
        if (((Adb shell dumpsys accessibility) -join "`n") -notmatch 'com\.google\.android\.marvin\.talkback/.+TalkBackService') {
            throw 'TalkBack service did not become active.'
        }
        $tree = Ui
        $nodes = @($tree.SelectNodes('//node'))
        if (-not ($nodes | Where-Object text -eq $heading)) { throw "TalkBack tree omitted heading: $heading" }
        if (-not ($nodes | Where-Object text -eq $selected)) { throw "TalkBack tree omitted selected control: $selected" }
        $semanticNode = $nodes | Where-Object { $_.'content-desc' -match $descriptionPattern } | Select-Object -First 1
        for ($attempt = 0; -not $semanticNode -and $attempt -lt 4; $attempt++) {
            Adb shell input swipe 540 1800 540 750 400 | Out-Null
            Start-Sleep -Milliseconds 500
            $semanticNode = (Ui).SelectNodes('//node') | Where-Object { $_.'content-desc' -match $descriptionPattern } | Select-Object -First 1
        }
        if (-not $semanticNode) {
            throw "TalkBack tree omitted instructional semantics matching: $descriptionPattern"
        }
    } finally {
        if ($oldServices -in @('', 'null')) { Adb shell settings delete secure enabled_accessibility_services | Out-Null }
        else { Adb shell settings put secure enabled_accessibility_services $oldServices | Out-Null }
        if ($oldEnabled -in @('', 'null')) { Adb shell settings delete secure accessibility_enabled | Out-Null }
        else { Adb shell settings put secure accessibility_enabled $oldEnabled | Out-Null }
        if (-not $notificationWasGranted) { Adb shell pm revoke $talkBackPackage $notificationPermission | Out-Null }
        Start-Sleep -Seconds 1
    }
}

if (-not $ResetTestAppData) { throw 'This destructive QA script requires -ResetTestAppData and clears only the dedicated QA emulator app.' }
if (-not (Test-Path $apk)) { throw 'Build android/app/build/outputs/apk/debug/app-debug.apk first.' }
if (((Adb emu avd name) -join "`n") -notmatch '^LearnSmart_API36') { throw 'Dedicated LearnSmart_API36 AVD required.' }
$health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
if ($health.ai_provider -ne 'scripted-catalog-qa') { throw 'Run serve_qa.py --qa-only --catalog-fixture first.' }

$examples = @(
    [pscustomobject]@{ Key='math/decimals'; Subject='Mathematics'; Chapter='Decimals'; Heading='Explore decimal place value'; Action='Explore Ones'; Selected='Selected: Ones'; Accessible='42 point 375.*ones place highlighted'; Prerequisite=$null },
    [pscustomobject]@{ Key='math/percentages'; Subject='Mathematics'; Chapter='Percentages'; Heading='Explore percentages'; Action='Show 50%'; Selected='Selected: 50%'; Accessible='100-square grid with 50 squares highlighted'; Prerequisite=$null },
    [pscustomobject]@{ Key='math/algebra'; Subject='Mathematics'; Chapter='Algebra'; Heading='Balance an equation'; Action='Subtract 3 from both sides'; Selected='Selected: Subtract 3 from both sides'; Accessible='2x equals 8'; Prerequisite=$null },
    [pscustomobject]@{ Key='math/geometry'; Subject='Mathematics'; Chapter='Geometry'; Heading='Explore triangle area'; Action='Base 8, height 5'; Selected='Selected: Base 8, height 5'; Accessible='Triangle with base 8.*height 5.*area 20'; Prerequisite='math/algebra' },
    [pscustomobject]@{ Key='science/matter'; Subject='Science'; Chapter='Matter and Materials'; Heading='Explore particle models'; Action='Liquid'; Selected='Selected: Liquid'; Accessible='Liquid particle model'; Prerequisite=$null },
    [pscustomobject]@{ Key='science/force-and-motion'; Subject='Science'; Chapter='Force and Motion'; Heading='Explore constant speed'; Action='3 m/s for 4 s'; Selected='Selected: 3 m/s for 4 s'; Accessible='3 metres per second.*4 seconds.*12 metres'; Prerequisite=$null },
    [pscustomobject]@{ Key='science/ecosystems'; Subject='Science'; Chapter='Ecosystems'; Heading='Trace ecosystem energy'; Action='Grasshopper →'; Selected='Selected: Grasshopper'; Accessible='Grasshopper, Primary consumer, 1000 example energy units'; Prerequisite='science/force-and-motion' },
    [pscustomobject]@{ Key='english/reading-comprehension'; Subject='English'; Chapter='Reading Comprehension'; Heading='Build an inference'; Action='Inference'; Selected='Selected: Inference'; Accessible='Reading passage\.'; Prerequisite=$null },
    [pscustomobject]@{ Key='english/vocabulary'; Subject='English'; Chapter='Vocabulary'; Heading='Build word meaning'; Action='Root: help'; Selected='Selected: Root: help'; Accessible='Word unhelpful split into prefix'; Prerequisite=$null },
    [pscustomobject]@{ Key='english/writing'; Subject='English'; Chapter='Writing'; Heading='Explore paragraph structure'; Action='Evidence'; Selected='Selected: Evidence'; Accessible='Evidence\. Students can measure real plant growth'; Prerequisite='english/vocabulary' },
    [pscustomobject]@{ Key='social/history'; Subject='Social Studies'; Chapter='History'; Heading='Evaluate historical sources'; Action='A photograph taken at the event'; Selected='Selected: A photograph taken at the event'; Accessible='Primary source\..*It records a moment'; Prerequisite=$null },
    [pscustomobject]@{ Key='social/civics'; Subject='Social Studies'; Chapter='Civics'; Heading='Trace a civic decision'; Action='2. Public input'; Selected='Selected: 2. Public input'; Accessible='Civic stage 2, Public input'; Prerequisite=$null },
    [pscustomobject]@{ Key='social/economics'; Subject='Social Studies'; Chapter='Economics'; Heading='Explore supply and demand'; Action='Price 4'; Selected='Selected: Price 4'; Accessible='At price 4, quantity demanded is 8 and quantity supplied is 8'; Prerequisite='social/civics' }
)
if ($Route.Count) {
    $unknown = @($Route | Where-Object { $_ -notin $examples.Key })
    if ($unknown.Count) { throw "Unknown route(s): $($unknown -join ', ')" }
    $examples = @($examples | Where-Object Key -in $Route)
}

$passed = @()
foreach ($example in $examples) {
    Write-Output "VERIFY $($example.Key)"
    & $adb -s emulator-5554 uninstall $package | Out-Null
    Adb install $apk | Out-Null
    RestartApp
    TapText 'New student? Create a private account'
    $email = 'x' + [Guid]::NewGuid().ToString('N').Substring(0, 8) + '@x.co'
    EnterField 0 $email
    EnterField 1 'qa-password-long-enough'
    TapText 'Create account'
    FindText "Grade`n8" | Out-Null

    $login = Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{
        email=$email; password='qa-password-long-enough'
    } | ConvertTo-Json)
    $headers = @{ Authorization = "Bearer $($login.access_token)" }
    if ($example.Prerequisite) {
        Invoke-RestMethod "http://127.0.0.1:8000/__qa/learning-path/$($example.Prerequisite)" -Method Post -Headers $headers | Out-Null
    }

    TapText "Grade`n8"
    TapText $example.Subject
    TapText $example.Chapter
    TapText 'Needs another look'
    TapText 'Submit answer'
    FindText $example.Heading 30 -Scroll | Out-Null
    TapText $example.Action 30 -Scroll
    FindText $example.Selected 30 -Scroll | Out-Null
    if ($VerifyTalkBack) { VerifyTalkBackExplorer $example.Heading $example.Selected $example.Accessible }

    [xml]$preferences = (Adb shell run-as $package cat shared_prefs/learn-smart.xml) -join "`n"
    $sessionId = ($preferences.map.ChildNodes | Where-Object name -eq "active_mastery:$email").InnerText
    $state = Invoke-RestMethod "http://127.0.0.1:8000/v1/mastery/sessions/$sessionId" -Headers $headers
    if ($state.status -ne 'tutor' -or $state.coaching_rounds -ne 0 -or $state.mastery_score -ne 0) {
        throw "Explorer interaction changed mastery state for $($example.Key)."
    }
    $captureName = 'qa-explorer-' + $example.Key.Replace('/', '-') + '.png'
    Adb shell screencap -p "/sdcard/$captureName" | Out-Null
    Adb pull "/sdcard/$captureName" (Join-Path $repo "artifacts\$captureName") | Out-Null
    Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers $headers | Out-Null
    Adb shell pm clear $package | Out-Null
    $passed += $example.Key
}

Write-Output "PASS: $($passed.Count) full catalog explorer journey(s): $($passed -join ', ')"
