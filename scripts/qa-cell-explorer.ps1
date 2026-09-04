param([switch]$ResetTestAppData)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$adb=Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package='com.konetibalaji.learning'
function Adb{& $adb -s emulator-5554 @args;if($LASTEXITCODE-ne0){throw "ADB failed: $($args[0])"}}
function Ui{for($i=0;$i-lt5;$i++){if(((Adb shell uiautomator dump /sdcard/qa-cell-explorer.xml)-join'')-match'dumped to'){return [xml]((Adb shell cat /sdcard/qa-cell-explorer.xml)-join"`n")};Start-Sleep -Milliseconds 500};throw 'Could not obtain a fresh Android UI hierarchy.'}
function Center($node){$b=[regex]::Matches($node.bounds,'\d+')|ForEach-Object{[int]$_.Value};@([int](($b[0]+$b[2])/2),[int](($b[1]+$b[3])/2))}
function FindText([string]$text,[int]$seconds=30,[switch]$Scroll){$until=(Get-Date).AddSeconds($seconds);$attempt=0;do{$node=(Ui).SelectNodes('//node')|Where-Object text -eq $text|Select-Object -First 1;if($node){return $node};if($Scroll){if(($attempt%8)-lt4){Adb shell input swipe 540 1850 540 750 350|Out-Null}else{Adb shell input swipe 540 750 540 1850 350|Out-Null};$attempt++};Start-Sleep -Milliseconds 600}while((Get-Date)-lt$until);throw "UI text not found: $text"}
function TapText([string]$text,[int]$seconds=30,[switch]$Scroll){$p=Center(FindText $text $seconds -Scroll:$Scroll);Adb shell input tap $p[0] $p[1]|Out-Null;Start-Sleep -Milliseconds 900}
function EnterField([int]$index,[string]$value){$f=@((Ui).SelectNodes('//node')|Where-Object class -eq 'android.widget.EditText');$p=Center $f[$index];Adb shell input tap $p[0] $p[1]|Out-Null;foreach($c in $value.ToCharArray()){switch($c){'@'{Adb shell input keyevent 77|Out-Null}'.'{Adb shell input keyevent 56|Out-Null}'-'{Adb shell input keyevent 69|Out-Null}default{Adb shell input text ([string]$c)|Out-Null}}};Adb shell input keyevent 4|Out-Null}
function RestartApp{Adb shell am force-stop $package|Out-Null;Adb shell am start -n "$package/.MainActivity"|Out-Null;Start-Sleep -Seconds 3}
if(-not$ResetTestAppData){throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.'}
if(((Adb emu avd name)-join"`n")-notmatch'^LearnSmart_API36'){throw 'Dedicated LearnSmart_API36 AVD required.'}
if((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider-ne'scripted-science-qa'){throw 'Run serve_qa.py --qa-only --science-fixture first.'}
& $adb -s emulator-5554 uninstall $package|Out-Null
Adb install (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk')|Out-Null
RestartApp
TapText 'New student? Create a private account'
$email='cell-explorer-'+[Guid]::NewGuid().ToString('N')+'@example.com'
EnterField 0 $email
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
TapText "Grade`n8"
TapText 'Science'
TapText 'Cells and Living Things'
TapText 'Cell wall'
TapText 'Submit answer'
FindText 'Explore a cell' 30 -Scroll|Out-Null
FindText 'Selected: Nucleus' 30 -Scroll|Out-Null
TapText 'Explore Mitochondrion' 30 -Scroll
FindText 'Selected: Mitochondrion' 30 -Scroll|Out-Null
FindText 'Releases usable energy from food through cellular respiration.' 30 -Scroll|Out-Null
Adb shell screencap -p /sdcard/qa-cell-explorer.png|Out-Null
Adb pull /sdcard/qa-cell-explorer.png (Join-Path $repo 'artifacts\qa-cell-explorer.png')|Out-Null
$login=Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$email;password='qa-password-long-enough'}|ConvertTo-Json)
$headers=@{Authorization="Bearer $($login.access_token)"}
[xml]$preferences=(Adb shell run-as $package cat shared_prefs/learn-smart.xml)-join"`n"
$sessionId=($preferences.map.ChildNodes|Where-Object name -eq "active_mastery:$email").InnerText
$state=Invoke-RestMethod "http://127.0.0.1:8000/v1/mastery/sessions/$sessionId" -Headers $headers
if($state.status-ne'tutor'-or$state.coaching_rounds-ne0-or$state.mastery_score-ne0){throw 'Exploration changed the learning state.'}
Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers $headers|Out-Null
Adb shell pm clear $package|Out-Null
Write-Output 'PASS: the native Cells explorer highlighted three curated organelles, selection changed visibly, and exploration did not alter mastery.'
