#!/usr/bin/env bash
set -euo pipefail

run_dir="${RUNNER_TEMP:?Run on the Linux verification runner}/saras-emulator"
export ANDROID_USER_HOME="$run_dir/android"
export ANDROID_AVD_HOME="$ANDROID_USER_HOME/avd"
mkdir -p "$ANDROID_AVD_HOME"

export PYTHONPATH="$PWD/backend"
export STUDY_MODEL_DIR="$PWD/.study-models"
export STUDY_MODELS_OFFLINE=true
export STUDY_GENERATION_MODE=local_practice
export STUDY_OCR_REVIEW_THRESHOLD=1.0

pids=()
cleanup() {
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
}
trap cleanup EXIT

for port in 18763 18771; do
    STUDY_DATA_DIR="$run_dir/data-$port" python -m uvicorn study.api:create_app \
        --factory --host 127.0.0.1 --port "$port" > "$run_dir/backend-$port.log" 2>&1 &
    pids+=("$!")
done

python scripts/start-fallback-test-backend.py --port 18764 --data-dir "$run_dir/data-18764" \
    > "$run_dir/backend-18764.log" 2>&1 &
pids+=("$!")

for port in 18763 18764 18771; do
    curl --fail --silent --show-error --retry 20 --retry-delay 1 --retry-connrefused \
        "http://127.0.0.1:$port/ready" > /dev/null
done

printf 'no\n' | avdmanager create avd --name SarasCI \
    --package "system-images;android-35;google_apis;x86_64" --device pixel_6 --force
"$ANDROID_HOME/emulator/emulator" -list-avds | grep -Fx SarasCI
"$ANDROID_HOME/emulator/emulator" @SarasCI -port 5554 -no-window -no-audio -no-boot-anim \
    -no-snapshot -netdelay none -netspeed full > "$run_dir/emulator.log" 2>&1 &
pids+=("$!")

export ANDROID_SERIAL=emulator-5554
export emulator_pid="$!"
timeout 240 bash -c '
    adb start-server
    until [[ "$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d "\r")" == 1 ]]; do
        kill -0 "$emulator_pid" || exit 1
        sleep 2
    done
'
adb shell input keyevent 82
for scale in window_animation_scale transition_animation_scale animator_duration_scale; do
    adb shell settings put global "$scale" 0
done

adb install android/app/build/outputs/apk/debug/app-debug.apk
adb install android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb reverse tcp:18771 tcp:18771
runner=com.studycompanion.qa.test/androidx.test.runner.AndroidJUnitRunner
curriculum_test=com.studycompanion.LearningFlowTest#gradeSixSubjectPathsUnlockTheirSecondChapter
for phase in prepare resume; do
    timeout 120 adb shell am instrument -w -r -e studyHost 127.0.0.1 -e studyPort 18771 -e class "$curriculum_test" \
        -e curriculumRestartPhase "$phase" "$runner" | tee "$run_dir/curriculum-restart-$phase.log"
    grep -Eq '^OK \(1 test\)' "$run_dir/curriculum-restart-$phase.log"
    if [[ "$phase" == prepare ]]; then
        adb shell am force-stop com.studycompanion.qa
        if adb shell pidof com.studycompanion.qa; then
            echo "The QA app process is still running after force-stop." >&2
            exit 1
        fi
    fi
done

timeout 600 adb shell am instrument -w -r \
    -e studyPort 18763 -e sharingPort 18771 -e googleDisabledPort 18763 \
    com.studycompanion.qa.test/androidx.test.runner.AndroidJUnitRunner | tee "$run_dir/instrumentation.log"

# Android's instrumentation command can exit successfully after a failed test.
grep -Eq '^OK \([1-9][0-9]* tests?\)' "$run_dir/instrumentation.log"
