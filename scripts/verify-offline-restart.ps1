param([string]$Serial = 'emulator-5554')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$adb = Join-Path $root 'work\toolchain\sdk\platform-tools\adb.exe'
if ($Serial -notlike 'emulator-*') { throw 'This destructive process-lifecycle test is restricted to the disposable emulator.' }
$model = (& $adb -s $Serial shell getprop ro.product.model).Trim()
if ($model -notlike '*sdk*') { throw 'Expected the disposable SDK emulator.' }
$mainApk = Join-Path $root 'android\app\build\outputs\apk\debug\app-debug.apk'
$testApk = Join-Path $root 'android\app\build\outputs\apk\androidTest\debug\app-debug-androidTest.apk'
foreach ($apk in @($mainApk, $testApk)) {
    & $adb -s $Serial install -r $apk
    if ($LASTEXITCODE -ne 0) { throw 'Test APK installation failed.' }
}
$test = 'com.studycompanion.LearningFlowTest#savedMaterialSupportsAirplaneModeQuizFeedbackAndDeletion'
$runner = 'com.studycompanion.test/androidx.test.runner.AndroidJUnitRunner'
try {
    $prepared = (& $adb -s $Serial shell am instrument -w -e class $test -e offlineRestartPhase prepare $runner) -join "`n"
    $prepared
    if ($prepared -notmatch 'OK \(1 test\)') { throw 'Offline restart preparation failed.' }
    & $adb -s $Serial shell cmd connectivity airplane-mode enable
    & $adb -s $Serial shell svc wifi disable
    & $adb -s $Serial shell am force-stop com.studycompanion
    $remainingPid = (& $adb -s $Serial shell pidof com.studycompanion) -join ''
    if ($remainingPid.Trim()) { throw 'The original app process is still running.' }
    Write-Output 'Verified original app process is absent; resuming from encrypted disk state.'
    $resumed = (& $adb -s $Serial shell am instrument -w -e class $test -e offlineRestartPhase resume $runner) -join "`n"
    $resumed
    if ($resumed -notmatch 'OK \(1 test\)') { throw 'Offline restart resumption failed.' }
} finally {
    & $adb -s $Serial shell cmd connectivity airplane-mode disable
    & $adb -s $Serial shell svc wifi enable
}
