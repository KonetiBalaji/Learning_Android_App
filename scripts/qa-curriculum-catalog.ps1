param([switch]$ResetTestAppData)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$adb=Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package='com.konetibalaji.learning'
function Adb{& $adb -s emulator-5554 @args;if($LASTEXITCODE-ne0){throw "ADB failed: $($args[0])"}}
function Ui{for($i=0;$i-lt5;$i++){if(((Adb shell uiautomator dump /sdcard/qa-catalog.xml)-join'')-match'dumped to'){return [xml]((Adb shell cat /sdcard/qa-catalog.xml)-join"`n")};Start-Sleep -Milliseconds 500};throw 'Could not obtain a fresh Android UI hierarchy.'}
function Center($node){$b=[regex]::Matches($node.bounds,'\d+')|ForEach-Object{[int]$_.Value};@([int](($b[0]+$b[2])/2),[int](($b[1]+$b[3])/2))}
function FindText([string]$text,[int]$seconds=30,[switch]$Scroll){$until=(Get-Date).AddSeconds($seconds);do{$node=(Ui).SelectNodes('//node')|Where-Object text -eq $text|Select-Object -First 1;if($node){return $node};if($Scroll){Adb shell input swipe 540 1850 540 750 350|Out-Null};Start-Sleep -Milliseconds 600}while((Get-Date)-lt$until);throw "UI text not found: $text"}
function FindTextMatch([string]$pattern,[int]$seconds=30){$until=(Get-Date).AddSeconds($seconds);do{$node=(Ui).SelectNodes('//node')|Where-Object text -match $pattern|Select-Object -First 1;if($node){return $node};Start-Sleep -Milliseconds 600}while((Get-Date)-lt$until);throw "UI text pattern not found: $pattern"}
function FindAbsent([string]$text,[int]$seconds=5){$until=(Get-Date).AddSeconds($seconds);do{$node=(Ui).SelectNodes('//node')|Where-Object text -eq $text|Select-Object -First 1;if($node){throw "Unexpected stale UI text found: $text"};Start-Sleep -Milliseconds 500}while((Get-Date)-lt$until)}
function TapText([string]$text,[int]$seconds=30,[switch]$Scroll){$p=Center(FindText $text $seconds -Scroll:$Scroll);Adb shell input tap $p[0] $p[1]|Out-Null;Start-Sleep -Milliseconds 900}
function EnterField([int]$index,[string]$value){$f=@((Ui).SelectNodes('//node')|Where-Object class -eq 'android.widget.EditText');$p=Center $f[$index];Adb shell input tap $p[0] $p[1]|Out-Null;foreach($c in $value.ToCharArray()){switch($c){'@'{Adb shell input keyevent 77|Out-Null}'.'{Adb shell input keyevent 56|Out-Null}'-'{Adb shell input keyevent 69|Out-Null}default{Adb shell input text ([string]$c)|Out-Null}}};Adb shell input keyevent 4|Out-Null}
function RestartApp{Adb shell am force-stop $package|Out-Null;Adb shell am start -n "$package/.MainActivity"|Out-Null;Start-Sleep -Seconds 3}
function CheckSubject([string]$subject,[string]$first,[string]$last){TapText $subject 30 -Scroll;FindText $first 30 -Scroll|Out-Null;FindText $last 30 -Scroll|Out-Null;TapText '‹ All subjects' 30 -Scroll}
if(-not$ResetTestAppData){throw 'This script requires -ResetTestAppData and clears only the dedicated QA emulator app.'}
if(((Adb emu avd name)-join"`n")-notmatch'^LearnSmart_API36'){throw 'Dedicated LearnSmart_API36 AVD required.'}
if((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider-notin@('deterministic','scripted-qa')){throw 'Run an isolated deterministic or scripted QA backend first.'}
& $adb -s emulator-5554 uninstall $package|Out-Null
Adb install (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk')|Out-Null
RestartApp
TapText 'New student? Create a private account'
$email='catalog-'+[Guid]::NewGuid().ToString('N')+'@example.com'
EnterField 0 $email
EnterField 1 'qa-password-long-enough'
TapText 'Create account'
FindText 'Select your grade' 30|Out-Null
TapText "Grade`n8"
$label='Catalog foundation-2026-09 · Board alignment unconfirmed'
FindText $label 30 -Scroll|Out-Null
$login=Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/login' -Method Post -ContentType 'application/json' -Body (@{email=$email;password='qa-password-long-enough'}|ConvertTo-Json)
$headers=@{Authorization="Bearer $($login.access_token)"}
CheckSubject 'Mathematics' 'Fractions' 'Geometry'
CheckSubject 'Science' 'Cells and Living Things' 'Ecosystems'
CheckSubject 'English' 'Grammar' 'Writing'
CheckSubject 'Social Studies' 'Geography' 'Economics'
TapText 'Settings and account' 30 -Scroll
TapText 'Change grade · 8' 30 -Scroll
$grade9=FindText "Grade`n9`nComing later"
if($grade9.ParentNode.enabled-ne'false' -or $grade9.ParentNode.clickable-ne'true'){throw 'Grade 9 card must be present but disabled while Grade 8 is the launch curriculum.'}
Adb shell screencap -p /sdcard/qa-grade-availability.png|Out-Null
Adb pull /sdcard/qa-grade-availability.png (Join-Path $repo 'artifacts\qa-grade-availability.png')|Out-Null
$p=Center $grade9
Adb shell input tap $p[0] $p[1]|Out-Null
Start-Sleep -Milliseconds 900
FindText 'Select your grade'|Out-Null
FindAbsent 'Mathematics'
TapText "Grade`n8"
FindText $label 30 -Scroll|Out-Null
FindText 'Mathematics' 30 -Scroll|Out-Null
FindText 'Science' 30 -Scroll|Out-Null
FindText 'English' 30 -Scroll|Out-Null
FindText 'Social Studies' 30 -Scroll|Out-Null
RestartApp
FindText $label 30 -Scroll|Out-Null
FindText 'Social Studies' 30 -Scroll|Out-Null
Adb shell screencap -p /sdcard/qa-curriculum-catalog.png|Out-Null
Adb pull /sdcard/qa-curriculum-catalog.png (Join-Path $repo 'artifacts\qa-curriculum-catalog.png')|Out-Null
TapText 'Mathematics' 30 -Scroll
TapText 'Fractions' 30 -Scroll
FindText 'Diagnostic quiz'|Out-Null
$legacy=Invoke-RestMethod 'http://127.0.0.1:8000/__qa/mastery/latest/mark-legacy-catalog' -Method Post -Headers $headers
if($legacy.catalog_version-ne'legacy-qa'){throw 'QA server did not mark the session with a legacy catalog.'}
RestartApp
FindText 'Your saved lesson uses an older curriculum catalog. Start a new diagnostic from the current catalog.'|Out-Null
TapText 'Try again'
FindText $label 30 -Scroll|Out-Null
FindText 'Mathematics' 30 -Scroll|Out-Null
FindAbsent 'Resume saved learning'
$retained=Invoke-RestMethod "http://127.0.0.1:8000/v1/mastery/sessions/$($legacy.session_id)" -Headers $headers
if($retained.catalog_version-ne'legacy-qa'){throw 'Server did not retain the legacy-catalog mastery record.'}
Adb shell screencap -p /sdcard/qa-curriculum-catalog-migration.png|Out-Null
Adb pull /sdcard/qa-curriculum-catalog-migration.png (Join-Path $repo 'artifacts\qa-curriculum-catalog-migration.png')|Out-Null
Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers $headers|Out-Null
Adb shell pm clear $package|Out-Null
Write-Output 'PASS: API 36 enforced the Grade 8 launch boundary, restored the server catalog after restart, and safely retired a local resume pointer for a legacy-catalog session.'
