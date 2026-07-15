#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
SUPERVISOR="$ROOT_DIR/run_two_computer_eye_tracking.sh"
TEST_TMP="$(mktemp -d)"
FAKE_BIN="$TEST_TMP/bin"
FAKE_BEHAVIORBOX="$TEST_TMP/BehaviorBox"

cleanup() {
  rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_contains() {
  local expected="$1"
  local file="$2"

  grep -F -- "$expected" "$file" >/dev/null ||
    fail "Expected '$expected' in $file"
}

expect_status() {
  local expected="$1"
  local output_file="$2"
  shift 2
  local actual=0

  "$@" >"$output_file" 2>&1 || actual=$?
  [[ "$actual" -eq "$expected" ]] ||
    fail "Expected status $expected, got $actual: $*"
}

assert_not_running() {
  local pid_file="$1"
  local pid=""

  [[ -s "$pid_file" ]] || fail "Missing PID file: $pid_file"
  pid="$(<"$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    fail "Process $pid from $pid_file is still running."
  fi
}

mkdir -p "$FAKE_BIN" "$FAKE_BEHAVIORBOX"

cat >"$FAKE_BIN/fake_start" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\0' "$@" >"$FAKE_START_ARGS"
printf '%s\n' "$$" >"$FAKE_START_PID"
trap 'exit 0' INT TERM
while true; do
  sleep 0.1
done
EOF

cat >"$FAKE_BIN/fake_status" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
[[ -s "$FAKE_START_PID" ]] || exit 1
pid="$(<"$FAKE_START_PID")"
kill -0 "$pid" 2>/dev/null
EOF

cat >"$FAKE_BIN/fake_stop" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
count=0
if [[ -f "$FAKE_STOP_COUNT" ]]; then
  count="$(<"$FAKE_STOP_COUNT")"
fi
printf '%s\n' "$((count + 1))" >"$FAKE_STOP_COUNT"
if [[ -s "$FAKE_START_PID" ]]; then
  pid="$(<"$FAKE_START_PID")"
  kill -INT "$pid" 2>/dev/null || true
fi
EOF

cat >"$FAKE_BIN/fake_x11" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\0' "$@" >"$FAKE_X11_ARGS"
EOF

cat >"$FAKE_BIN/fake_ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat >/dev/null
printf '%s\0' "$@" >"$FAKE_SSH_ARGS"
exit "${FAKE_SSH_STATUS:-0}"
EOF

cat >"$FAKE_BIN/fake_ss" <<'EOF'
#!/usr/bin/env bash
if [[ "${FAKE_LOCAL_LISTENER:-0}" == "1" ]]; then
  echo "LISTEN 0 10 127.0.0.1:8765 0.0.0.0:*"
fi
EOF

cat >"$FAKE_BIN/fake_curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '{"ok":true,"address":"tcp://10.55.0.1:5555","samples_received":2}'
EOF

cat >"$FAKE_BIN/fake_receiver_python" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-c" && "${2:-}" == "import zmq" ]]; then
  exit 0
fi
if [[ "${1:-}" == *run_eye_receiver_service.py ]]; then
  printf '%s\n' "$$" >"$FAKE_RECEIVER_PID"
  trap 'exit 0' INT TERM
  while true; do
    sleep 0.1
  done
fi
if [[ "${1:-}" == *run_matlab_eye_receive_test.py ]]; then
  printf '%s\0' "$@" >"$FAKE_MATLAB_TEST_ARGS"
  exit "${FAKE_MATLAB_TEST_STATUS:-0}"
fi
echo "Unexpected fake receiver Python arguments: $*" >&2
exit 2
EOF

cat >"$FAKE_BIN/fake_matlab" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
tty0=0
tty1=0
tty2=0
[[ -t 0 ]] && tty0=1
[[ -t 1 ]] && tty1=1
[[ -t 2 ]] && tty2=1
printf '%s\0' "$@" >"$FAKE_MATLAB_ARGS"
printf 'cwd=%s\n' "$PWD" >"$FAKE_MATLAB_RECORD"
printf 'address=%s\n' "${BB_EYETRACK_ZMQ_ADDRESS:-}" >>"$FAKE_MATLAB_RECORD"
printf 'receiver=%s\n' "${BB_EYETRACK_RECEIVER_URL:-}" >>"$FAKE_MATLAB_RECORD"
printf 'tty=%s,%s,%s\n' "$tty0" "$tty1" "$tty2" >>"$FAKE_MATLAB_RECORD"
echo "MATLAB_LIVE_OUTPUT"
exit "${FAKE_MATLAB_STATUS:-0}"
EOF

chmod +x "$FAKE_BIN"/*

export PATH="$FAKE_BIN:$PATH"
export DISPLAY=":99"
export FAKE_START_ARGS="$TEST_TMP/start.args"
export FAKE_START_PID="$TEST_TMP/start.pid"
export FAKE_RECEIVER_PID="$TEST_TMP/receiver.pid"
export FAKE_STOP_COUNT="$TEST_TMP/stop.count"
export FAKE_X11_ARGS="$TEST_TMP/x11.args"
export FAKE_SSH_ARGS="$TEST_TMP/ssh.args"
export FAKE_MATLAB_TEST_ARGS="$TEST_TMP/matlab-test.args"
export FAKE_MATLAB_ARGS="$TEST_TMP/matlab.args"
export FAKE_MATLAB_RECORD="$TEST_TMP/matlab.record"
export EYETRACK_START_SCRIPT="$FAKE_BIN/fake_start"
export EYETRACK_STATUS_SCRIPT="$FAKE_BIN/fake_status"
export EYETRACK_STOP_SCRIPT="$FAKE_BIN/fake_stop"
export EYETRACK_X11_TEST_SCRIPT="$FAKE_BIN/fake_x11"
export EYETRACK_RECEIVER_SCRIPT="$ROOT_DIR/Stream-DeepLabCut/run_eye_receiver_service.py"
export EYETRACK_MATLAB_TEST_SCRIPT="$ROOT_DIR/Stream-DeepLabCut/run_matlab_eye_receive_test.py"
export EYETRACK_SSH_BIN="$FAKE_BIN/fake_ssh"
export EYETRACK_CURL_BIN="$FAKE_BIN/fake_curl"
export EYETRACK_SS_BIN="$FAKE_BIN/fake_ss"
export EYETRACK_LOCK_FILE="$TEST_TMP/supervisor.lock"
export EYETRACK_MATLAB_BIN="$TEST_TMP/missing-matlab"
export EYETRACK_BEHAVIORBOX_ROOT="$TEST_TMP/missing-BehaviorBox"

SERVICE_ARGS=(
  --skip-role-check
  --receiver-python "$FAKE_BIN/fake_receiver_python"
  --startup-timeout-s 5
  --poll-interval-s 0.1
)
SMOKE_ARGS=(
  "${SERVICE_ARGS[@]}"
  --matlab-bin "$FAKE_BIN/fake_matlab"
  --behaviorbox-root "$FAKE_BEHAVIORBOX"
)

expect_status 0 "$TEST_TMP/check-only.out" \
  "$SUPERVISOR" --check-only "${SERVICE_ARGS[@]}"
assert_contains "Two-computer EyeTrack preflight passed." "$TEST_TMP/check-only.out"
[[ ! -e "$FAKE_START_PID" ]] || fail "--check-only started the streamer."
[[ ! -e "$FAKE_STOP_COUNT" ]] || fail "--check-only invoked remote stop."
[[ ! -e "$FAKE_MATLAB_ARGS" ]] || fail "--check-only started MATLAB."

expect_status 130 "$TEST_TMP/default-run.out" \
  timeout --preserve-status --signal=INT 2 "$SUPERVISOR" "${SERVICE_ARGS[@]}"

assert_contains "Eye tracking is ready." "$TEST_TMP/default-run.out"
assert_contains "MATLAB and BehaviorBox remain under operator control" "$TEST_TMP/default-run.out"
assert_contains "BB_EYETRACK_ZMQ_ADDRESS=tcp://10.55.0.1:5555" "$TEST_TMP/default-run.out"
assert_contains "BB_EYETRACK_RECEIVER_URL=http://127.0.0.1:8765" "$TEST_TMP/default-run.out"
[[ ! -e "$FAKE_MATLAB_ARGS" ]] || fail "Default production run started MATLAB."
[[ "$(<"$FAKE_STOP_COUNT")" == "1" ]] || fail "Remote stop did not run exactly once."
assert_not_running "$FAKE_START_PID"
assert_not_running "$FAKE_RECEIVER_PID"

mapfile -d '' -t start_args <"$FAKE_START_ARGS"
arg_count=${#start_args[@]}
(( arg_count >= 5 )) || fail "Too few captured streamer arguments."
display_scale_seen=0
for ((index = 0; index + 1 < arg_count; index++)); do
  if [[ "${start_args[index]}" == "--display-scale" &&
    "${start_args[index + 1]}" == "2" ]]; then
    display_scale_seen=1
    break
  fi
done
[[ "$display_scale_seen" -eq 1 ]] || fail "Default display scale was not set to 2."
[[ "${start_args[arg_count - 5]}" == "--address" ]] || fail "Address was not enforced last."
[[ "${start_args[arg_count - 4]}" == "tcp://10.55.0.1:5555" ]] || fail "Wrong enforced address."
[[ "${start_args[arg_count - 3]}" == "--display" ]] || fail "Display was not enforced."
[[ "${start_args[arg_count - 2]}" == "--display-fps" ]] || fail "Display FPS flag was not enforced."
[[ "${start_args[arg_count - 1]}" == "5" ]] || fail "Display FPS was not forced to 5."

rm -f -- "$FAKE_START_PID" "$FAKE_RECEIVER_PID" "$FAKE_STOP_COUNT"
expect_status 0 "$TEST_TMP/transport-test.out" \
  "$SUPERVISOR" --transport-test "${SMOKE_ARGS[@]}"
mapfile -d '' -t matlab_test_args <"$FAKE_MATLAB_TEST_ARGS"
printf '%s\n' "${matlab_test_args[@]}" | grep -Fx -- "--transport-only" >/dev/null ||
  fail "Transport test did not pass --transport-only."
matlab_bin_seen=0
for ((index = 0; index + 1 < ${#matlab_test_args[@]}; index++)); do
  if [[ "${matlab_test_args[index]}" == "--matlab-bin" &&
    "${matlab_test_args[index + 1]}" == "$FAKE_BIN/fake_matlab" ]]; then
    matlab_bin_seen=1
    break
  fi
done
[[ "$matlab_bin_seen" -eq 1 ]] || fail "Smoke test did not receive the configured MATLAB binary."
[[ "$(<"$FAKE_STOP_COUNT")" == "1" ]] || fail "Transport cleanup did not stop remote once."
assert_not_running "$FAKE_START_PID"
assert_not_running "$FAKE_RECEIVER_PID"

rm -f -- "$FAKE_START_PID" "$FAKE_RECEIVER_PID" "$FAKE_STOP_COUNT" \
  "$FAKE_MATLAB_TEST_ARGS"
expect_status 0 "$TEST_TMP/full-test.out" \
  "$SUPERVISOR" --full-test "${SMOKE_ARGS[@]}"
mapfile -d '' -t matlab_test_args <"$FAKE_MATLAB_TEST_ARGS"
if printf '%s\n' "${matlab_test_args[@]}" | grep -Fx -- "--transport-only" >/dev/null; then
  fail "Full test unexpectedly passed --transport-only."
fi
[[ "$(<"$FAKE_STOP_COUNT")" == "1" ]] || fail "Full-test cleanup did not stop remote once."
assert_not_running "$FAKE_START_PID"
assert_not_running "$FAKE_RECEIVER_PID"

rm -f -- "$FAKE_START_PID" "$FAKE_RECEIVER_PID" "$FAKE_STOP_COUNT"
export FAKE_LOCAL_LISTENER=1
expect_status 1 "$TEST_TMP/listener-conflict.out" \
  "$SUPERVISOR" --check-only "${SERVICE_ARGS[@]}"
assert_contains "Local receiver port 8765 is already in use" "$TEST_TMP/listener-conflict.out"
[[ ! -e "$FAKE_START_PID" ]] || fail "Listener conflict started the streamer."
[[ ! -e "$FAKE_STOP_COUNT" ]] || fail "Listener conflict invoked remote stop."

export FAKE_LOCAL_LISTENER=0
export FAKE_SSH_STATUS=9
expect_status 1 "$TEST_TMP/remote-preflight-failure.out" \
  "$SUPERVISOR" --check-only "${SERVICE_ARGS[@]}"
assert_contains "Eye-computer preflight failed." "$TEST_TMP/remote-preflight-failure.out"
[[ ! -e "$FAKE_START_PID" ]] || fail "Remote preflight failure started the streamer."
[[ ! -e "$FAKE_STOP_COUNT" ]] || fail "Remote preflight failure invoked remote stop."

echo "TWO_COMPUTER_SUPERVISOR_OK"
