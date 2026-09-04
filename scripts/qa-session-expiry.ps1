param([switch]$ResetTestAppData)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package = 'com.konetibalaji.learning'
function Adb { & $adb -s emulator-5554 @args; if ($LASTEXITCODE -ne 0) { throw "ADB failed: $($args[0])" } }
function Ui {
    for ($attempt = 0; $attempt -lt 5; $attempt++) {
        if (((Adb shell uiautomator dump /sdcard/qa-session-expiry.xml) -join '') -match 'dumped to') {
            return [xml]((Adb shell cat /sdcard/qa-session-expiry.xml) -join "`n")
        }
        Start-Sleep -Milliseconds 500
    }
    throw 'Could not obtain a fresh Android UI hierarchy.'
}
function Center($node) { $b=[regex]::Matches($node.bounds,'\d+')|ForEach-Object{[int]$_.Value}; @([int](($b[0]+$b[2])/2),[int](($b[1]+$b[3])/2)) }
function FindText([string]$text,[int]$seconds=30,[switch]$Scroll) {
    $until=(Get-Date).AddSeconds($seconds); $attempt=0
    do {
        $node=(Ui).SelectNodes('//node')|Where-Object text -eq $text|Select-Object -First 1
        if($node){return $node}
        if($Scroll){if(($attempt%8)-lt4){Adb shell input swipe 540 1850 540 750 350|Out-Null}else{Adb shell input swipe 540 750 540 1850 350|Out-Null};$attempt++}
        Start-Sleep -Milliseconds 600
    }while((Get-Date)-lt$until)
    throw "UI text not found: $text"
}
function TapText([string]$text,[int]$seconds=30,[switch]$Scroll){$p=Center(FindText $text $seconds -Scroll:$Scroll);Adb shell input tap $p[0] $p[1]|Out-Null;Start-Sleep -Milliseconds 900}
function EnterField([int]$index,[string]$value){$f=@((Ui).SelectNodes('//node')|Where-Object class -eq 'android.widget.EditText');$p=Center $f[$index];Adb shell input tap $p[0] $p[1]|Out-Null;foreach($c in $value.ToCharArray()){switch($c){'@'{Adb shell input keyevent 77|Out-Null}'.'{Adb shell input keyevent 56|Out-Null}'-'{Adb shell input keyevent 69|Out-Null}default{Adb shell input text ([string]$c)|Out-Null}}};Adb shell input keyevent 4|Out-Null}
function RestartApp { Adb shell am force-stop $package|Out-Null;Adb shell am start -n "$package/.MainActivity"|Out-Null;Start-Sleep -Seconds 3 }
if(-not $ResetTestAppData){throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.'}
if(((Adb emu avd name)-join"`n")-notmatch'^LearnSmart_API36'){throw 'Dedicated LearnSmart_API36 AVD required.'}
$health=Invoke-RestMethod 'http://127.0.0.1:8000/health'
if($health.ai_provider-ne'deterministic'){throw 'Isolated deterministic QA backend required.'}
& $adb -s emulator-5554 uninstall $package|Out-Null
Adb install (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk')|Out-Null
RestartApp
TapText 'New student? Create a private account'
$email='expiry-'+[Guid]::NewGuid().ToString('N')+'@example.com'
EnterField 0 $email
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
TapText "Grade`n8" 30
[xml]$saved=(Adb shell run-as $package cat shared_prefs/learn-smart.xml)-join"`n"
if(-not($saved.map.ChildNodes|Where-Object name -eq 'session_ciphertext')){throw 'Encrypted session was not persisted before expiry.'}
Start-Sleep -Seconds 65
TapText 'Settings and account' 30 -Scroll
TapText 'Change grade · 8' 30 -Scroll
TapText "Grade`n8" 30
FindText 'Your session has expired or is no longer valid. Please sign in again.' 30 -Scroll|Out-Null
[xml]$cleared=(Adb shell run-as $package cat shared_prefs/learn-smart.xml)-join"`n"
if($cleared.map.ChildNodes|Where-Object name -in @('session_ciphertext','token')){throw 'Expired credentials remained in Android preferences.'}
RestartApp
FindText 'Sign in' 30|Out-Null
$login=Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$email;password='qa-password-long-enough'}|ConvertTo-Json)
Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers @{Authorization="Bearer $($login.access_token)"}|Out-Null
Adb shell pm clear $package|Out-Null
Write-Output 'PASS: a real timed token expiry returned Android to sign-in, cleared encrypted credentials across restart, and preserved reauthentication until disposable-account cleanup.'
