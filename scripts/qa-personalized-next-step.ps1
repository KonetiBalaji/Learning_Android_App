param([switch]$ResetTestAppData)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$adb=Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
$package='com.konetibalaji.learning'
function Adb{& $adb -s emulator-5554 @args;if($LASTEXITCODE-ne0){throw 'ADB failed'}}
function Ui{for($i=0;$i-lt5;$i++){if(((Adb shell uiautomator dump /sdcard/qa-next-step.xml)-join'')-match'dumped to'){return [xml]((Adb shell cat /sdcard/qa-next-step.xml)-join"`n")};Start-Sleep -Milliseconds 500};throw 'Could not read Android UI hierarchy'}
function Center($node){$b=[regex]::Matches($node.bounds,'\d+')|ForEach-Object{[int]$_.Value};@([int](($b[0]+$b[2])/2),[int](($b[1]+$b[3])/2))}
function FindText([string]$text,[int]$seconds=30,[switch]$Scroll){$until=(Get-Date).AddSeconds($seconds);do{$node=(Ui).SelectNodes('//node')|Where-Object text -eq $text|Select-Object -First 1;if($node){return $node};if($Scroll){Adb shell input swipe 540 1850 540 650 350|Out-Null};Start-Sleep -Milliseconds 600}while((Get-Date)-lt$until);throw "UI text not found: $text"}
function FindAbsent([string]$text){if((Ui).SelectNodes('//node')|Where-Object text -eq $text){throw "Unexpected UI text: $text"}}
function TapText([string]$text,[switch]$Scroll){$p=Center(FindText $text 30 -Scroll:$Scroll);Adb shell input tap $p[0] $p[1]|Out-Null;Start-Sleep -Milliseconds 900}
function EnterField([int]$index,[string]$value){$f=@((Ui).SelectNodes('//node')|Where-Object class -eq 'android.widget.EditText');$p=Center $f[$index];Adb shell input tap $p[0] $p[1]|Out-Null;foreach($c in $value.ToCharArray()){switch($c){'@'{Adb shell input keyevent 77|Out-Null}'.'{Adb shell input keyevent 56|Out-Null}'-'{Adb shell input keyevent 69|Out-Null}default{Adb shell input text ([string]$c)|Out-Null}}};Adb shell input keyevent 4|Out-Null}
if(-not$ResetTestAppData){throw 'Requires -ResetTestAppData for the dedicated emulator'}
if(((Adb emu avd name)-join"`n")-notmatch'^LearnSmart_API36'){throw 'Dedicated LearnSmart_API36 AVD required'}
if((Invoke-RestMethod 'http://127.0.0.1:8000/health').ai_provider-notin@('deterministic','scripted-qa')){throw 'Run the isolated deterministic QA backend'}
$email='next-'+[Guid]::NewGuid().ToString('N')+'@example.com'
$password='qa-password-long-enough'
$account=Invoke-RestMethod 'http://127.0.0.1:8000/v1/auth/register' -Method Post -ContentType 'application/json' -Body (@{email=$email;password=$password}|ConvertTo-Json)
$headers=@{Authorization="Bearer $($account.access_token)"}
$paths=@();$states=@{}
foreach($round in 1..2){$started=Invoke-RestMethod 'http://127.0.0.1:8000/v1/mastery/diagnostics' -Method Post -Headers $headers -ContentType 'application/json' -Body (@{grade=8;subject_id='math';chapter_id='fractions'}|ConvertTo-Json);$path="http://127.0.0.1:8000/v1/mastery/sessions/$($started.id)";$paths+=$path;$outcome=Invoke-RestMethod ($path+'/diagnostic-answer') -Method Post -Headers $headers -ContentType 'application/json' -Body (@{selected_option='1/2';expected_state=$started.state_token}|ConvertTo-Json);$states[$path]=$outcome.state_token}
Adb install -r (Join-Path $repo 'android\app\build\outputs\apk\debug\app-debug.apk')|Out-Null
Adb shell pm clear $package|Out-Null
Adb shell am start -n "$package/.MainActivity"|Out-Null
Start-Sleep -Seconds 3
EnterField 0 $email
EnterField 1 $password
TapText 'Sign in'
TapText "Grade`n8"
TapText 'View my progress report' -Scroll
$weak='Adding like fractions'
$rec='Review Adding like fractions in Mathematics · Fractions: 2 unresolved independent mistakes'
FindText $weak 30 -Scroll|Out-Null
FindText $rec 30 -Scroll|Out-Null
Adb shell screencap -p /sdcard/qa-personalized-next-step.png|Out-Null
Adb pull /sdcard/qa-personalized-next-step.png (Join-Path $repo 'artifacts\qa-personalized-next-step.png')|Out-Null
$latest=$paths[-1]
$practice=Invoke-RestMethod ($latest+'/practice') -Method Post -Headers $headers -ContentType 'application/json' -Body (@{response='6/8';expected_state=$states[$latest]}|ConvertTo-Json)
Invoke-RestMethod ($latest+'/rewrite') -Method Post -Headers $headers -ContentType 'application/json' -Body (@{response='We add numerator parts with the same denominator to make one whole.';expected_state=$practice.state_token}|ConvertTo-Json)|Out-Null
foreach($i in 1..5){Adb shell input swipe 540 650 540 1900 300|Out-Null;Start-Sleep -Milliseconds 250}
TapText '‹ Back to subjects'
FindText 'View my progress report' 30 -Scroll|Out-Null
TapText 'View my progress report' -Scroll
FindText 'No unresolved weak areas recorded. Continue assessing and practising.' 30 -Scroll|Out-Null
FindText 'Continue Mathematics · Fractions from your saved diagnostic step' 30 -Scroll|Out-Null
FindAbsent $rec
Invoke-RestMethod 'http://127.0.0.1:8000/v1/account' -Method Delete -Headers $headers|Out-Null
Adb shell pm clear $package|Out-Null
Write-Output 'PASS: recurring independent mistakes produced an evidenced next step; successful rewrite cleared it and selected the active diagnostic.'
