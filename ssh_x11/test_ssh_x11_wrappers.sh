#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_TMP="$(mktemp -d)"
FAKE_BIN="$TEST_TMP/bin"
FAKE_REMOTE_HOME="$TEST_TMP/remote home"
REMOTE_REPO_REL="Repo with spaces"
REMOTE_REPO="$FAKE_REMOTE_HOME/$REMOTE_REPO_REL"
REMOTE_CONDA_REL="Conda files/conda.sh"
REMOTE_CONDA="$FAKE_REMOTE_HOME/$REMOTE_CONDA_REL"

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

assert_argv() {
  local capture_file="$1"
  shift
  local -a actual=()
  local -a expected=("$@")
  local index

  mapfile -d '' -t actual <"$capture_file"
  [[ ${#actual[@]} -eq $# ]] ||
    fail "Expected $# captured arguments, got ${#actual[@]}"
  for ((index = 0; index < ${#expected[@]}; index++)); do
    if [[ "${actual[index]}" != "${expected[index]}" ]]; then
      fail "Argument $index differs: expected '${expected[index]}', got '${actual[index]}'"
    fi
  done
}

expect_failure() {
  local output_file="$1"
  shift

  if "$@" >"$output_file" 2>&1; then
    fail "Command unexpectedly succeeded: $*"
  fi
}

mkdir -p \
  "$FAKE_BIN" \
  "$REMOTE_REPO/Stream-DeepLabCut" \
  "$REMOTE_REPO/Cam-Tests" \
  "$(dirname -- "$REMOTE_CONDA")"

cat >"$FAKE_BIN/ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

while [[ $# -gt 0 && "$1" == -* ]]; do
  case "$1" in
    -Y|-X|-T)
      shift
      ;;
    *)
      echo "Unsupported fake ssh option: $1" >&2
      exit 2
      ;;
  esac
done

[[ $# -ge 1 ]] || { echo "Fake ssh did not receive a host." >&2; exit 2; }
host="$1"
shift
[[ $# -eq 1 ]] || {
  echo "Expected one serialized remote command after $host, got $# arguments." >&2
  exit 2
}

printf '%s\0%s\0' "$host" "$1" >>"$FAKE_SSH_LOG"
HOME="$FAKE_REMOTE_HOME" PATH="$FAKE_REMOTE_BIN:/usr/bin:/bin" bash -c "$1"
EOF

cat >"$FAKE_BIN/pgrep" <<'EOF'
#!/usr/bin/env bash
if [[ "${FAKE_PGREP_SUCCESS:-0}" == "1" ]]; then
  echo "4242 python run_eye_stream_production.py"
  exit 0
fi
exit 1
EOF

cat >"$FAKE_BIN/ss" <<'EOF'
#!/usr/bin/env bash
port="${FAKE_LISTEN_PORT:-5555}"
host="${FAKE_LISTEN_HOST:-127.0.0.1}"
pid="${FAKE_LISTEN_PID:-4242}"
echo "LISTEN 0 10 ${host}:${port} 0.0.0.0:* users:((python,pid=${pid},fd=3))"
EOF

cat >"$FAKE_BIN/ps" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-eo" ]]; then
  count=0
  if [[ -f "$FAKE_PS_COUNT" ]]; then
    count="$(<"$FAKE_PS_COUNT")"
  fi
  printf '%s\n' "$((count + 1))" >"$FAKE_PS_COUNT"
  case "${FAKE_PS_MODE:-none}" in
    clear)
      if [[ "$count" -eq 0 ]]; then
        printf '999999 %s\n' "$FAKE_PROCESS_COMMAND"
      fi
      ;;
    sticky)
      printf '999999 %s\n' "$FAKE_PROCESS_COMMAND"
      ;;
    none)
      ;;
    *)
      echo "Unknown FAKE_PS_MODE: $FAKE_PS_MODE" >&2
      exit 2
      ;;
  esac
elif [[ "${1:-}" == "-p" ]]; then
  printf '999999 %s\n' "$FAKE_PROCESS_COMMAND"
else
  /bin/ps "$@"
fi
EOF

cat >"$FAKE_BIN/readlink" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "-f" && "${2:-}" == "--" && "${3:-}" == /proc/*/cwd ]]; then
  printf '%s\n' "$FAKE_PROCESS_CWD"
  exit 0
fi
exec /usr/bin/readlink "$@"
EOF

cat >"$FAKE_BIN/xauth" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat >"$FAKE_BIN/xdpyinfo" <<'EOF'
#!/usr/bin/env bash
printf 'called\n' >>"$FAKE_X_PROBE_LOG"
exit "${FAKE_XDPYINFO_STATUS:-0}"
EOF

cat >"$REMOTE_CONDA" <<'EOF'
conda() {
  [[ "$1" == "activate" && -n "${2:-}" ]]
}

python() {
  printf '%s\0' "$@" >"$CAPTURE_FILE"
}
EOF

cat >"$REMOTE_REPO/Stream-DeepLabCut/run_eye_stream_production.py" <<'EOF'
#!/usr/bin/env bash
printf '%s\0' "$@" >"$CAPTURE_FILE"
EOF

chmod +x "$FAKE_BIN"/* "$REMOTE_REPO/Stream-DeepLabCut/run_eye_stream_production.py"

export FAKE_REMOTE_BIN="$FAKE_BIN"
export FAKE_REMOTE_HOME
export FAKE_SSH_LOG="$TEST_TMP/ssh.log"
export FAKE_X_PROBE_LOG="$TEST_TMP/x-probe.log"
export PATH="$FAKE_BIN:$PATH"
export DISPLAY=":99"

sentinel="$TEST_TMP/remote-command-executed"
special_args=(
  --session-name
  "session with spaces"
  "literal*glob"
  '\$(touch should-stay-literal)'
  "\$(touch $sentinel)"
  "semicolon; touch $sentinel"
  "single'quote"
  'redirect>target'
)

export CAPTURE_FILE="$TEST_TMP/start.argv"
"$SCRIPT_DIR/start_eye_stream_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --conda-sh "~/$REMOTE_CONDA_REL" \
  --conda-env "env with spaces" \
  -- "${special_args[@]}" >"$TEST_TMP/start.out"
assert_argv "$CAPTURE_FILE" "${special_args[@]}" --display --display-fps 5
[[ ! -e "$sentinel" ]] || fail "A pass-through argument executed as a remote command."

unset DISPLAY
expect_failure \
  "$TEST_TMP/start-default-without-display.out" \
  "$SCRIPT_DIR/start_eye_stream_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --conda-sh "~/$REMOTE_CONDA_REL"
assert_contains "DISPLAY is empty on this computer." "$TEST_TMP/start-default-without-display.out"

export CAPTURE_FILE="$TEST_TMP/start-headless.argv"
"$SCRIPT_DIR/start_eye_stream_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --conda-sh "~/$REMOTE_CONDA_REL" \
  -- --no-display >"$TEST_TMP/start-headless.out"
assert_argv "$CAPTURE_FILE" --no-display

export DISPLAY=":99"
export CAPTURE_FILE="$TEST_TMP/start-custom-display.argv"
"$SCRIPT_DIR/start_eye_stream_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --conda-sh "~/$REMOTE_CONDA_REL" \
  -- --display --display-fps 2 >"$TEST_TMP/start-custom-display.out"
assert_argv "$CAPTURE_FILE" --display --display-fps 2

export CAPTURE_FILE="$TEST_TMP/alignment.argv"
"$SCRIPT_DIR/open_alignment_preview_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --conda-sh "~/$REMOTE_CONDA_REL" \
  -- --window-name "Eye preview; literal" >"$TEST_TMP/alignment.out"
assert_argv "$CAPTURE_FILE" FLIRCam.py --window-name "Eye preview; literal"

export CAPTURE_FILE="$TEST_TMP/training.argv"
"$SCRIPT_DIR/open_training_capture_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --conda-sh "~/$REMOTE_CONDA_REL" \
  -- --output-dir '~/Desktop/Training frames' >"$TEST_TMP/training.out"
assert_argv \
  "$CAPTURE_FILE" capture_flir_training_frames.py \
  --output-dir '~/Desktop/Training frames'

csv_dir="$FAKE_REMOTE_HOME/CSV output"
mkdir -p "$csv_dir"
: >"$csv_dir/eye_stream_test.csv"
export FAKE_PGREP_SUCCESS=1
export FAKE_LISTEN_HOST=10.55.0.1
export FAKE_LISTEN_PORT=6001
"$SCRIPT_DIR/eye_stream_status_over_ssh.sh" \
  --host fake@example \
  --address tcp://10.55.0.1:6001 \
  --csv-dir '~/CSV output' >"$TEST_TMP/status.out"
assert_contains "Address: tcp://10.55.0.1:6001" "$TEST_TMP/status.out"
assert_contains "Listening port: 6001" "$TEST_TMP/status.out"
assert_contains "Directory: $csv_dir" "$TEST_TMP/status.out"
assert_contains "$csv_dir/eye_stream_test.csv" "$TEST_TMP/status.out"

export FAKE_LISTEN_PID=7777
expect_failure \
  "$TEST_TMP/status-unrelated-listener.out" \
  "$SCRIPT_DIR/eye_stream_status_over_ssh.sh" \
  --host fake@example \
  --address tcp://10.55.0.1:6001 \
  --csv-dir '~/CSV output'
assert_contains \
  "it is not owned by a matching EyeTrack process" \
  "$TEST_TMP/status-unrelated-listener.out"

export FAKE_LISTEN_PID=4242
export FAKE_LISTEN_HOST=127.0.0.1
expect_failure \
  "$TEST_TMP/status-wrong-bind.out" \
  "$SCRIPT_DIR/eye_stream_status_over_ssh.sh" \
  --host fake@example \
  --address tcp://10.55.0.1:6001 \
  --csv-dir '~/CSV output'
assert_contains "Nothing listening for tcp://10.55.0.1:6001." "$TEST_TMP/status-wrong-bind.out"

expect_failure \
  "$TEST_TMP/status-failure.out" \
  "$SCRIPT_DIR/eye_stream_status_over_ssh.sh" \
  --host fake@example --port 6002 --csv-dir '~/CSV output'
assert_contains "Nothing listening for tcp://127.0.0.1:6002." "$TEST_TMP/status-failure.out"

export FAKE_PROCESS_COMMAND="python ./run_eye_stream_production.py"
export FAKE_PROCESS_CWD="$REMOTE_REPO/Stream-DeepLabCut"
export FAKE_PS_COUNT="$TEST_TMP/ps-count"
export FAKE_PS_MODE=clear
rm -f -- "$FAKE_PS_COUNT"
"$SCRIPT_DIR/stop_eye_stream_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL/" \
  --timeout-s 1 \
  --poll-interval-s 0.01 >"$TEST_TMP/stop.out"
assert_contains "All matching eye-stream processes stopped." "$TEST_TMP/stop.out"

export FAKE_PS_MODE=sticky
rm -f -- "$FAKE_PS_COUNT"
expect_failure \
  "$TEST_TMP/stop-timeout.out" \
  "$SCRIPT_DIR/stop_eye_stream_over_ssh.sh" \
  --host fake@example \
  --remote-repo "~/$REMOTE_REPO_REL" \
  --timeout-s 0
assert_contains "Eye-stream processes remained after 0s" "$TEST_TMP/stop-timeout.out"

export FAKE_XDPYINFO_STATUS=0
: >"$FAKE_X_PROBE_LOG"
"$SCRIPT_DIR/test_x11_forwarding_over_ssh.sh" \
  --host fake@example >"$TEST_TMP/x11.out"
assert_contains "X11 probe: xdpyinfo succeeded." "$TEST_TMP/x11.out"
[[ -s "$FAKE_X_PROBE_LOG" ]] || fail "The mandatory X11 probe did not run."

export FAKE_XDPYINFO_STATUS=1
expect_failure \
  "$TEST_TMP/x11-failure.out" \
  "$SCRIPT_DIR/test_x11_forwarding_over_ssh.sh" --host fake@example
assert_contains "xdpyinfo could not open the forwarded display." "$TEST_TMP/x11-failure.out"

for script in \
  start_eye_stream_over_ssh.sh \
  open_alignment_preview_over_ssh.sh \
  open_training_capture_over_ssh.sh \
  eye_stream_status_over_ssh.sh \
  stop_eye_stream_over_ssh.sh \
  test_x11_forwarding_over_ssh.sh; do
  expect_failure "$TEST_TMP/${script}.missing-value" "$SCRIPT_DIR/$script" --host
  assert_contains "--host requires a value." "$TEST_TMP/${script}.missing-value"
done

expect_failure \
  "$TEST_TMP/setup-missing-value.out" \
  "$SCRIPT_DIR/setup_eye_host_ssh_x11.sh" --conf-file
assert_contains "--conf-file requires a value." "$TEST_TMP/setup-missing-value.out"

expect_failure \
  "$TEST_TMP/setup-unsafe-path.out" \
  "$SCRIPT_DIR/setup_eye_host_ssh_x11.sh" \
  --dry-run --conf-file /etc/ssh/sshd_config
assert_contains \
  "--conf-file must be a direct child of /etc/ssh/sshd_config.d" \
  "$TEST_TMP/setup-unsafe-path.out"

SETUP_FAKE_BIN="$TEST_TMP/setup-bin"
mkdir -p "$SETUP_FAKE_BIN"

cat >"$SETUP_FAKE_BIN/sshd" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  -t)
    count=0
    if [[ -f "$FAKE_SSHD_COUNT" ]]; then
      count="$(<"$FAKE_SSHD_COUNT")"
    fi
    count=$((count + 1))
    printf '%s\n' "$count" >"$FAKE_SSHD_COUNT"
    case "$FAKE_SSHD_SCENARIO" in
      syntax_failure)
        [[ "$count" -ne 2 ]]
        ;;
      restore_failure)
        [[ "$count" -lt 2 ]]
        ;;
      *)
        exit 0
        ;;
    esac
    ;;
  -T)
    if [[ "$FAKE_SSHD_SCENARIO" == "effective_failure" ]]; then
      printf 'x11forwarding no\nx11uselocalhost yes\n'
    else
      printf 'x11forwarding yes\nx11uselocalhost yes\n'
    fi
    ;;
  *)
    echo "Unexpected fake sshd arguments: $*" >&2
    exit 2
    ;;
esac
EOF

cat >"$SETUP_FAKE_BIN/systemctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$FAKE_SYSTEMCTL_LOG"
EOF

cat >"$SETUP_FAKE_BIN/xauth" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat >"$SETUP_FAKE_BIN/mv" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
count=0
if [[ -f "$FAKE_MV_COUNT" ]]; then
  count="$(<"$FAKE_MV_COUNT")"
fi
count=$((count + 1))
printf '%s\n' "$count" >"$FAKE_MV_COUNT"
if [[ "$FAKE_SSHD_SCENARIO" == "restore_failure" && "$count" -eq 2 ]]; then
  exit 1
fi
exec /usr/bin/mv "$@"
EOF

chmod +x "$SETUP_FAKE_BIN"/*

prepare_setup_root() {
  local root="$1"
  mkdir -p "$root/etc/ssh/sshd_config.d"
  printf 'Include /etc/ssh/sshd_config.d/*.conf\n' >"$root/etc/ssh/sshd_config"
  printf 'OLD CONFIG\n' >"$root/etc/ssh/sshd_config.d/60-eyetrack-x11.conf"
}

run_setup_scenario() {
  local scenario="$1"
  local root="$2"
  env \
    EYETRACK_SSH_X11_TEST_ROOT="$root" \
    FAKE_SSHD_SCENARIO="$scenario" \
    FAKE_SSHD_COUNT="$root/sshd-count" \
    FAKE_MV_COUNT="$root/mv-count" \
    FAKE_SYSTEMCTL_LOG="$root/systemctl.log" \
    PATH="$SETUP_FAKE_BIN:/usr/bin:/bin" \
    "$SCRIPT_DIR/setup_eye_host_ssh_x11.sh" --skip-ufw
}

setup_syntax_root="$TEST_TMP/setup-syntax-failure"
prepare_setup_root "$setup_syntax_root"
expect_failure \
  "$TEST_TMP/setup-syntax-failure.out" \
  run_setup_scenario syntax_failure "$setup_syntax_root"
assert_contains \
  "The staged SSH configuration failed sshd -t." \
  "$TEST_TMP/setup-syntax-failure.out"
assert_contains \
  "OLD CONFIG" \
  "$setup_syntax_root/etc/ssh/sshd_config.d/60-eyetrack-x11.conf"
[[ "$(<"$setup_syntax_root/sshd-count")" == "3" ]] ||
  fail "Expected baseline, failed post-install, and restored sshd syntax checks."

setup_effective_root="$TEST_TMP/setup-effective-failure"
prepare_setup_root "$setup_effective_root"
expect_failure \
  "$TEST_TMP/setup-effective-failure.out" \
  run_setup_scenario effective_failure "$setup_effective_root"
assert_contains \
  "Effective SSH configuration does not enable X11Forwarding." \
  "$TEST_TMP/setup-effective-failure.out"
assert_contains \
  "OLD CONFIG" \
  "$setup_effective_root/etc/ssh/sshd_config.d/60-eyetrack-x11.conf"

setup_restore_root="$TEST_TMP/setup-restore-failure"
prepare_setup_root "$setup_restore_root"
expect_failure \
  "$TEST_TMP/setup-restore-failure.out" \
  run_setup_scenario restore_failure "$setup_restore_root"
assert_contains "Preserved the previous drop-in at:" "$TEST_TMP/setup-restore-failure.out"
compgen -G \
  "$setup_restore_root/etc/ssh/sshd_config.d/.60-eyetrack-x11.conf.backup.*" \
  >/dev/null || fail "A failed restore deleted the only SSH drop-in backup."

setup_success_root="$TEST_TMP/setup-success"
prepare_setup_root "$setup_success_root"
run_setup_scenario success "$setup_success_root" >"$TEST_TMP/setup-success.out"
assert_contains \
  "X11Forwarding yes" \
  "$setup_success_root/etc/ssh/sshd_config.d/60-eyetrack-x11.conf"
assert_contains \
  "X11UseLocalhost yes" \
  "$setup_success_root/etc/ssh/sshd_config.d/60-eyetrack-x11.conf"
assert_contains "enable ssh" "$setup_success_root/systemctl.log"
assert_contains "restart ssh" "$setup_success_root/systemctl.log"

echo "SSH_X11_WRAPPERS_OK"
