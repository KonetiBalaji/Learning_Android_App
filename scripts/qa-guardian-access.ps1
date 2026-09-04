param([switch]$ResetTestAppData)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$adb=Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package='com.konetibalaji.learning'
function Adb{& $adb -s emulator-5554 @args;if($LASTEXITCODE-ne0){throw "ADB failed: $($args[0])"}}
function Ui{for($i=0;$i-lt5;$i++){if(((Adb shell uiautomator dump /sdcard/qa-guardian.xml)-join'')-match'dumped to'){return [xml]((Adb shell cat /sdcard/qa-guardian.xml)-join"`n")};Start-Sleep -Milliseconds 500};throw 'Could not obtain a fresh Android UI hierarchy.'}
function Center($node){$b=[regex]::Matches($node.bounds,'\d+')|ForEach-Object{[int]$_.Value};@([int](($b[0]+$b[2])/2),[int](($b[1]+$b[3])/2))}
function FindText([string]$value,[int]$seconds=30,[switch]$Scroll){$until=(Get-Date).AddSeconds($seconds);do{$node=(Ui).SelectNodes('//node')|Where-Object text -eq $value|Select-Object -First 1;if($node){return $node};if($Scroll){Adb shell input swipe 540 1850 540 700 350|Out-Null};Start-Sleep -Milliseconds 600}while((Get-Date)-lt$until);throw "UI text not found: $value"}
function TapText([string]$value,[int]$seconds=30,[switch]$Scroll){$p=Center(FindText $value $seconds -Scroll:$Scroll);Adb shell input tap $p[0] $p[1]|Out-Null;Start-Sleep -Milliseconds 900}
function EnterField([int]$index,[string]$value){$fields=@((Ui).SelectNodes('//node')|Where-Object class -eq 'android.widget.EditText');if($index-ge$fields.Count){throw "Input field $index not found"};$p=Center $fields[$index];Adb shell input tap $p[0] $p[1]|Out-Null;Adb shell input keyevent 123|Out-Null;foreach($c in $value.ToCharArray()){switch($c){'@'{Adb shell input keyevent 77|Out-Null}'.'{Adb shell input keyevent 56|Out-Null}'-'{Adb shell input keyevent 69|Out-Null}default{Adb shell input text ([string]$c)|Out-Null}}};Adb shell input keyevent 4|Out-Null}
function Register([string]$email){Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/register' -Method Post -ContentType 'application/json' -Body (@{email=$email;password='qa-password-long-enough'}|ConvertTo-Json)}
function DeleteAccount($token){if($token){Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers @{Authorization="Bearer $($token.access_token)"}|Out-Null}}
if(-not$ResetTestAppData){throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.'}
if(((Adb emu avd name)-join"`n")-notmatch'^LearnSmart_API36'){throw 'Dedicated LearnSmart_API36 AVD required.'}
if((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider-notin@('deterministic','scripted-qa')){throw 'Run an isolated deterministic or scripted QA backend first.'}
$suffix=[Guid]::NewGuid().ToString('N')
$learnerEmail="guardian-learner-$suffix@example.com"
$guardianEmail="guardian-viewer-$suffix@example.com"
$learner=$null;$guardian=$null
try{
    $learner=Register $learnerEmail
    $guardian=Register $guardianEmail
    $invitation=Invoke-RestMethod 'http://127.0.0.1:8000/v1/guardian/invitations' -Method Post -ContentType 'application/json' -Body '{}' -Headers @{Authorization="Bearer $($learner.access_token)"}
    if($invitation.code-notmatch'^[0-9a-f]{32}$'){throw 'Invitation was not the expected high-entropy typeable code.'}
    & $adb -s emulator-5554 uninstall $package|Out-Null
    Adb install (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk')|Out-Null
    Adb shell am start -n "$package/.MainActivity"|Out-Null;Start-Sleep -Seconds 3
    EnterField 0 $guardianEmail
    EnterField 1 'qa-password-long-enough'
    TapText 'Sign in'
    TapText "Grade`n8"
    TapText 'Parent & teacher access' 30 -Scroll
    FindText 'No learner reports linked.' 30 -Scroll|Out-Null
    EnterField 0 $invitation.code
    TapText 'Link learner' 30 -Scroll
    FindText $learnerEmail 30 -Scroll|Out-Null
    TapText 'View Grade 8 report' 30 -Scroll
    FindText $learnerEmail 30 -Scroll|Out-Null
    FindText 'Shared aggregate progress only. Answers and uploaded documents are never included.' 30 -Scroll|Out-Null
    Adb shell screencap -p /sdcard/qa-guardian-access.png|Out-Null
    Adb pull /sdcard/qa-guardian-access.png (Join-Path $repo 'artifacts\qa-guardian-access.png')|Out-Null
    TapText '‹ Back to linked learners' 30 -Scroll
    TapText 'Remove linked learner' 30 -Scroll
    FindText 'No learner reports linked.' 30 -Scroll|Out-Null
    $linked=Invoke-RestMethod 'http://127.0.0.1:8000/v1/guardian/learners' -Headers @{Authorization="Bearer $($guardian.access_token)"}
    $access=Invoke-RestMethod 'http://127.0.0.1:8000/v1/guardian/access' -Headers @{Authorization="Bearer $($learner.access_token)"}
    if(@($linked).Count-ne0-or@($access).Count-ne0){throw 'Unlink did not remove both sides of access.'}
    Write-Output 'PASS: separate guardian account redeemed consent, viewed only the linked aggregate report, and removed access.'
}finally{
    DeleteAccount $guardian
    DeleteAccount $learner
    Adb shell pm clear $package|Out-Null
}
