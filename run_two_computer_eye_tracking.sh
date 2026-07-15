#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STREAM_DIR="$ROOT_DIR/Stream-DeepLabCut"
SSH_DIR="$ROOT_DIR/ssh_x11"

# shellcheck source=ssh_x11/ssh_x11_common.sh
source "$SSH_DIR/ssh_x11_common.sh"
# shellcheck source=Stream-DeepLabCut/behavior_eye_tracking_env.sh
source "$STREAM_DIR/behavior_eye_tracking_env.sh"

HOST="${EYETRACK_EYE_HOST:-wbs@10.55.0.1}"
ADDRESS="$BB_EYETRACK_ZMQ_ADDRESS"
RECEIVER_URL="$BB_EYETRACK_RECEIVER_URL"
REMOTE_REPO="${EYETRACK_REMOTE_REPO:-~/Desktop/BehaviorBox/EyeTrack}"
REMOTE_CONDA_SH="${EYETRACK_REMOTE_CONDA_SH:-~/miniforge3/etc/profile.d/conda.sh}"
REMOTE_CONDA_ENV="${EYETRACK_REMOTE_CONDA_ENV:-dlclivegui}"
MODEL_PATH=""
RECEIVER_PYTHON="$BB_EYETRACK_RECEIVER_PYTHON"
MATLAB_BIN="${EYETRACK_MATLAB_BIN:-matlab}"
BEHAVIORBOX_ROOT="${EYETRACK_BEHAVIORBOX_ROOT:-$(cd -- "$ROOT_DIR/.." && pwd)}"
BEHAVIOR_IP="${EYETRACK_BEHAVIOR_IP:-10.55.0.2}"
STARTUP_TIMEOUT_S=120
POLL_INTERVAL_S=1
MODE="run"
SKIP_ROLE_CHECK=0
STREAMER_EXTRA_ARGS=()

START_SCRIPT="${EYETRACK_START_SCRIPT:-$SSH_DIR/start_eye_stream_over_ssh.sh}"
STATUS_SCRIPT="${EYETRACK_STATUS_SCRIPT:-$SSH_DIR/eye_stream_status_over_ssh.sh}"
STOP_SCRIPT="${EYETRACK_STOP_SCRIPT:-$SSH_DIR/stop_eye_stream_over_ssh.sh}"
X11_TEST_SCRIPT="${EYETRACK_X11_TEST_SCRIPT:-$SSH_DIR/test_x11_forwarding_over_ssh.sh}"
RECEIVER_SCRIPT="${EYETRACK_RECEIVER_SCRIPT:-$STREAM_DIR/run_eye_receiver_service.py}"
MATLAB_TEST_SCRIPT="${EYETRACK_MATLAB_TEST_SCRIPT:-$STREAM_DIR/run_matlab_eye_receive_test.py}"
SSH_BIN="${EYETRACK_SSH_BIN:-ssh}"
CURL_BIN="${EYETRACK_CURL_BIN:-curl}"
SS_BIN="${EYETRACK_SS_BIN:-ss}"
IP_BIN="${EYETRACK_IP_BIN:-ip}"
SETSID_BIN="${EYETRACK_SETSID_BIN:-setsid}"
HEALTH_PYTHON="${EYETRACK_HEALTH_PYTHON:-python3}"
LOCK_FILE="${EYETRACK_LOCK_FILE:-${XDG_RUNTIME_DIR:-/tmp}/eyetrack-two-computer-${UID}.lock}"

ADDRESS_HOST=""
ADDRESS_PORT=""
RECEIVER_HOST=""
RECEIVER_PORT=""
LOCK_FD=""
RUN_DIR=""
STREAMER_LOG=""
STREAMER_STATUS_LOG=""
RECEIVER_LOG=""
SUPERVISOR_LOG=""
STREAMER_PID=""
STREAMER_PGID=""
RECEIVER_PID=""
REMOTE_STARTED=0
CLEANUP_DONE=0

usage() {
  cat <<'EOF'
Usage:
  ./run_two_computer_eye_tracking.sh [options] [-- streamer-args...]

Default workflow:
  Check the two-computer rig, start the X11-forwarded eye streamer, start the
  local receiver, wait for samples, and supervise both services until Ctrl+C.
  This command does not start or stop MATLAB or BehaviorBox. Start MATLAB
  independently, and begin the BehaviorBox session after eye tracking is ready.

Modes:
  --check-only           Run preflight checks without starting services
  --transport-test       Start a temporary MATLAB transport smoke test, then stop
  --full-test            Start a temporary valid-eye MATLAB smoke test, then stop

Rig options:
  --host USER@HOST       Eye computer SSH target. Default: wbs@10.55.0.1
  --address ENDPOINT     Remote ZMQ endpoint. Default: tcp://10.55.0.1:5555
  --receiver-url URL     Local receiver API. Default: http://127.0.0.1:8765
  --remote-repo PATH     Eye-host EyeTrack root. Default: ~/Desktop/BehaviorBox/EyeTrack
  --remote-conda-sh PATH Eye-host conda.sh. Default: ~/miniforge3/etc/profile.d/conda.sh
  --remote-conda-env ENV Eye-host runtime environment. Default: dlclivegui
  --model-path PATH      Optional absolute model path on the eye host
  --receiver-python PATH Local Python with pyzmq. Default comes from
                         Stream-DeepLabCut/behavior_eye_tracking_env.sh
  --matlab-bin PATH      MATLAB executable for smoke-test modes. Default: matlab
  --behaviorbox-root DIR BehaviorBox root for smoke tests. Default: parent of EyeTrack
  --behavior-ip ADDRESS  Expected local direct-link IP. Default: 10.55.0.2
  --skip-role-check      Do not require the expected behavior-host IP

Timing options:
  --startup-timeout-s N  Stream/receiver readiness timeout. Default: 120
  --poll-interval-s N    Readiness polling interval. Default: 1
  -h, --help             Show this help

Arguments after `--` are passed to run_eye_stream_production.py. The supervisor
uses a default display scale of 2; pass-through display-scale arguments may
override that default. It always places its configured --address and
`--display --display-fps 5` last, so those production-session requirements
cannot be overridden accidentally.
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

warn() {
  echo "WARNING: $*" >&2
}

normalize_matlab_bin() {
  local matlab_dir=""
  local matlab_name=""

  if [[ "$MATLAB_BIN" != */* || "$MATLAB_BIN" == /* ]]; then
    return 0
  fi

  matlab_dir="${MATLAB_BIN%/*}"
  matlab_name="${MATLAB_BIN##*/}"
  matlab_dir="$(cd -- "$matlab_dir" 2>/dev/null && pwd -P)" ||
    die "MATLAB executable directory not found: ${MATLAB_BIN%/*}"
  MATLAB_BIN="$matlab_dir/$matlab_name"
}

require_option_value() {
  local option="$1"
  local remaining="$2"

  if (( remaining < 2 )); then
    die "$option requires a value."
  fi
}

set_mode() {
  local requested="$1"
  if [[ "$MODE" != "run" && "$MODE" != "$requested" ]]; then
    die "Choose only one of --check-only, --transport-test, or --full-test."
  fi
  MODE="$requested"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only)
      set_mode "check"
      shift
      ;;
    --transport-test)
      set_mode "transport-test"
      shift
      ;;
    --full-test)
      set_mode "full-test"
      shift
      ;;
    --host)
      require_option_value "$1" "$#"
      HOST="$2"
      shift 2
      ;;
    --address)
      require_option_value "$1" "$#"
      ADDRESS="$2"
      shift 2
      ;;
    --receiver-url)
      require_option_value "$1" "$#"
      RECEIVER_URL="$2"
      shift 2
      ;;
    --remote-repo)
      require_option_value "$1" "$#"
      REMOTE_REPO="$2"
      shift 2
      ;;
    --remote-conda-sh)
      require_option_value "$1" "$#"
      REMOTE_CONDA_SH="$2"
      shift 2
      ;;
    --remote-conda-env)
      require_option_value "$1" "$#"
      REMOTE_CONDA_ENV="$2"
      shift 2
      ;;
    --model-path)
      require_option_value "$1" "$#"
      MODEL_PATH="$2"
      shift 2
      ;;
    --receiver-python)
      require_option_value "$1" "$#"
      RECEIVER_PYTHON="$2"
      shift 2
      ;;
    --matlab-bin)
      require_option_value "$1" "$#"
      MATLAB_BIN="$2"
      shift 2
      ;;
    --behaviorbox-root)
      require_option_value "$1" "$#"
      BEHAVIORBOX_ROOT="$2"
      shift 2
      ;;
    --behavior-ip)
      require_option_value "$1" "$#"
      BEHAVIOR_IP="$2"
      shift 2
      ;;
    --startup-timeout-s)
      require_option_value "$1" "$#"
      STARTUP_TIMEOUT_S="$2"
      shift 2
      ;;
    --poll-interval-s)
      require_option_value "$1" "$#"
      POLL_INTERVAL_S="$2"
      shift 2
      ;;
    --skip-role-check)
      SKIP_ROLE_CHECK=1
      shift
      ;;
    --)
      shift
      STREAMER_EXTRA_ARGS=("$@")
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$STARTUP_TIMEOUT_S" =~ ^[1-9][0-9]*$ ]]; then
  die "--startup-timeout-s must be a positive integer."
fi
if [[ ! "$POLL_INTERVAL_S" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] ||
  [[ "$POLL_INTERVAL_S" =~ ^0*([.]0*)?$ ]]; then
  die "--poll-interval-s must be a positive number."
fi
if [[ -n "$MODEL_PATH" && "$MODEL_PATH" != /* ]]; then
  die "--model-path must be an absolute path on the eye computer."
fi

parse_endpoints() {
  if [[ "$ADDRESS" =~ ^tcp://([^:/]+):([0-9]+)$ ]]; then
    ADDRESS_HOST="${BASH_REMATCH[1]}"
    ADDRESS_PORT="${BASH_REMATCH[2]}"
  else
    die "--address must use the form tcp://HOST:PORT: $ADDRESS"
  fi
  if [[ "$RECEIVER_URL" =~ ^http://([^/:]+):([0-9]+)/?$ ]]; then
    RECEIVER_HOST="${BASH_REMATCH[1]}"
    RECEIVER_PORT="${BASH_REMATCH[2]}"
    RECEIVER_URL="${RECEIVER_URL%/}"
  else
    die "--receiver-url must use the form http://HOST:PORT: $RECEIVER_URL"
  fi
  if (( ADDRESS_PORT < 1 || ADDRESS_PORT > 65535 )); then
    die "ZMQ port must be from 1 through 65535."
  fi
  if (( RECEIVER_PORT < 1 || RECEIVER_PORT > 65535 )); then
    die "Receiver API port must be from 1 through 65535."
  fi
}

command_exists() {
  local command_name="$1"
  if [[ "$command_name" == */* ]]; then
    [[ -x "$command_name" ]]
  else
    command -v "$command_name" >/dev/null 2>&1
  fi
}

pid_is_running() {
  local pid="$1"
  local state=""

  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
  [[ -n "$state" && "$state" != Z* ]]
}

route_uses_source() {
  local route_output="$1"
  local expected_source="$2"
  local previous=""
  local token

  for token in $route_output; do
    if [[ "$previous" == "src" && "$token" == "$expected_source" ]]; then
      return 0
    fi
    previous="$token"
  done
  return 1
}

wait_for_pid_exit() {
  local pid="$1"
  local timeout_s="$2"
  local deadline=$((SECONDS + timeout_s))

  while pid_is_running "$pid"; do
    if (( SECONDS >= deadline )); then
      return 1
    fi
    sleep 0.1
  done
  return 0
}

acquire_lock() {
  command_exists flock || die "Required command not found: flock"
  mkdir -p -- "$(dirname -- "$LOCK_FILE")" || die "Cannot create lock directory."
  exec {LOCK_FD}>"$LOCK_FILE" || die "Cannot open supervisor lock: $LOCK_FILE"
  if ! flock -n "$LOCK_FD"; then
    die "Another two-computer EyeTrack supervisor is already running."
  fi
}

tail_log() {
  local label="$1"
  local path="$2"

  [[ -f "$path" ]] || return 0
  echo "--- ${label}: ${path} ---" >&2
  tail -n 60 "$path" >&2 || true
}

cleanup() {
  local stop_status=0

  if [[ "$CLEANUP_DONE" -eq 1 ]]; then
    return 0
  fi
  CLEANUP_DONE=1
  trap - INT TERM HUP EXIT

  if pid_is_running "$RECEIVER_PID"; then
    echo "Stopping local eye receiver..."
    kill -INT "$RECEIVER_PID" 2>/dev/null || true
    if ! wait_for_pid_exit "$RECEIVER_PID" 5; then
      warn "Receiver did not exit after SIGINT; sending SIGTERM."
      kill -TERM "$RECEIVER_PID" 2>/dev/null || true
      if ! wait_for_pid_exit "$RECEIVER_PID" 3; then
        warn "Receiver did not exit after SIGTERM; sending SIGKILL."
        kill -KILL "$RECEIVER_PID" 2>/dev/null || true
      fi
    fi
  fi
  if [[ -n "$RECEIVER_PID" ]]; then
    wait "$RECEIVER_PID" 2>/dev/null || true
  fi
  RECEIVER_PID=""

  if [[ "$REMOTE_STARTED" -eq 1 ]]; then
    echo "Stopping remote eye streamer..."
    "$STOP_SCRIPT" \
      --host "$HOST" \
      --remote-repo "$REMOTE_REPO" \
      --timeout-s 10 >>"${SUPERVISOR_LOG:-/dev/null}" 2>&1 || {
      stop_status=$?
      warn "Remote stop helper could not verify shutdown; see $SUPERVISOR_LOG."
    }
  fi
  REMOTE_STARTED=0

  if pid_is_running "$STREAMER_PID"; then
    if ! wait_for_pid_exit "$STREAMER_PID" 3; then
      warn "Local SSH streamer wrapper remained after remote stop; terminating its process group."
      if [[ -n "$STREAMER_PGID" ]]; then
        kill -TERM -- "-$STREAMER_PGID" 2>/dev/null || true
      else
        kill -TERM "$STREAMER_PID" 2>/dev/null || true
      fi
      if ! wait_for_pid_exit "$STREAMER_PID" 2; then
        if [[ -n "$STREAMER_PGID" ]]; then
          kill -KILL -- "-$STREAMER_PGID" 2>/dev/null || true
        else
          kill -KILL "$STREAMER_PID" 2>/dev/null || true
        fi
      fi
    fi
  fi
  if [[ -n "$STREAMER_PID" ]]; then
    wait "$STREAMER_PID" 2>/dev/null || true
  fi
  STREAMER_PID=""
  STREAMER_PGID=""

  if [[ "$stop_status" -ne 0 ]]; then
    return "$stop_status"
  fi
  return 0
}

handle_signal() {
  local status="$1"
  echo
  warn "Supervisor termination requested; cleaning up EyeTrack services."
  cleanup
  exit "$status"
}

trap 'cleanup' EXIT
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM
trap 'handle_signal 129' HUP

local_preflight() {
  local path
  local route_output=""

  echo "Checking behavior-computer prerequisites..."
  for path in "$START_SCRIPT" "$STATUS_SCRIPT" "$STOP_SCRIPT" \
    "$X11_TEST_SCRIPT" "$RECEIVER_SCRIPT"; do
    [[ -f "$path" ]] || die "Required file not found: $path"
  done
  [[ -x "$START_SCRIPT" ]] || die "Not executable: $START_SCRIPT"
  [[ -x "$STATUS_SCRIPT" ]] || die "Not executable: $STATUS_SCRIPT"
  [[ -x "$STOP_SCRIPT" ]] || die "Not executable: $STOP_SCRIPT"
  [[ -x "$X11_TEST_SCRIPT" ]] || die "Not executable: $X11_TEST_SCRIPT"
  [[ -x "$RECEIVER_PYTHON" ]] || die "Receiver Python is not executable: $RECEIVER_PYTHON"

  command_exists "$SSH_BIN" || die "Required SSH command not found: $SSH_BIN"
  command_exists "$CURL_BIN" || die "Required HTTP command not found: $CURL_BIN"
  command_exists "$SS_BIN" || die "Required socket command not found: $SS_BIN"
  command_exists "$IP_BIN" || die "Required network command not found: $IP_BIN"
  command_exists "$SETSID_BIN" || die "Required session command not found: $SETSID_BIN"
  command_exists "$HEALTH_PYTHON" || die "Required health-check Python not found: $HEALTH_PYTHON"

  if [[ "$MODE" == "transport-test" || "$MODE" == "full-test" ]]; then
    [[ -f "$MATLAB_TEST_SCRIPT" ]] || die "MATLAB smoke-test script not found: $MATLAB_TEST_SCRIPT"
    [[ -d "$BEHAVIORBOX_ROOT" ]] || die "BehaviorBox root not found: $BEHAVIORBOX_ROOT"
    command_exists "$MATLAB_BIN" || die "MATLAB executable not found: $MATLAB_BIN"
  fi

  if ! "$RECEIVER_PYTHON" -c 'import zmq' >/dev/null 2>&1; then
    die "Receiver Python cannot import zmq: $RECEIVER_PYTHON"
  fi

  [[ -n "${DISPLAY:-}" ]] || die "DISPLAY is empty; the production stream requires X11 forwarding."

  if [[ "$SKIP_ROLE_CHECK" -eq 0 ]]; then
    route_output="$("$IP_BIN" route get "$ADDRESS_HOST" 2>/dev/null || true)"
    if ! route_uses_source "$route_output" "$BEHAVIOR_IP"; then
      die "This host does not route to $ADDRESS_HOST from expected behavior IP $BEHAVIOR_IP. Use --skip-role-check only for an intentional alternate topology."
    fi
  fi

  if [[ -n "$("$SS_BIN" -H -ltn "sport = :$RECEIVER_PORT" 2>/dev/null || true)" ]]; then
    die "Local receiver port $RECEIVER_PORT is already in use; refusing to reuse or stop it."
  fi

  echo "Checking SSH/X11 forwarding to $HOST..."
  "$X11_TEST_SCRIPT" --host "$HOST" || die "SSH/X11 forwarding check failed."
}

remote_preflight() {
  local deep_check=0

  if [[ "$MODE" == "check" ]]; then
    deep_check=1
  fi

  echo "Checking eye-computer runtime, model, camera, and port ownership..."
  ssh_x11_build_remote_command \
    bash -s -- "$REMOTE_REPO" "$REMOTE_CONDA_SH" "$REMOTE_CONDA_ENV" \
    "$MODEL_PATH" "$ADDRESS_PORT" "$deep_check"
  "$SSH_BIN" "$HOST" "$SSH_X11_REMOTE_COMMAND" <<'REMOTE'
set -euo pipefail

repo_root="$1"
conda_sh="$2"
conda_env="$3"
model_path="$4"
port="$5"
deep_check="$6"

expand_path() {
  local raw="$1"
  case "$raw" in
    "~")
      printf '%s\n' "$HOME"
      ;;
    "~/"*)
      printf '%s/%s\n' "$HOME" "${raw#\~/}"
      ;;
    "\${HOME}"*)
      printf '%s%s\n' "$HOME" "${raw#\$\{HOME\}}"
      ;;
    *)
      printf '%s\n' "$raw"
      ;;
  esac
}

repo_root="$(expand_path "$repo_root")"
conda_sh="$(expand_path "$conda_sh")"
repo_root="$(readlink -f -- "$repo_root")"
[[ -d "$repo_root/Stream-DeepLabCut" ]] || {
  echo "Remote runtime directory not found: $repo_root/Stream-DeepLabCut" >&2
  exit 1
}
[[ -f "$conda_sh" ]] || {
  echo "Remote conda.sh not found: $conda_sh" >&2
  exit 1
}

if [[ -z "$model_path" ]]; then
  model_path="$repo_root/models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1"
fi
[[ -d "$model_path" && -f "$model_path/pose_cfg.yaml" ]] || {
  echo "Remote exported model is incomplete or missing: $model_path" >&2
  exit 1
}
compgen -G "$model_path/snapshot-*.index" >/dev/null || {
  echo "Remote exported model has no snapshot index: $model_path" >&2
  exit 1
}

if pgrep -af 'run_eye_stream_production.py|dlc_eye_streamer.py' >/dev/null; then
  echo "An eye-stream process is already running; refusing to adopt or stop it." >&2
  pgrep -af 'run_eye_stream_production.py|dlc_eye_streamer.py' >&2 || true
  exit 1
fi
command -v ss >/dev/null 2>&1 || {
  echo "Remote ss command is required for port ownership checks." >&2
  exit 1
}
if [[ -n "$(ss -H -ltn "sport = :$port" 2>/dev/null || true)" ]]; then
  echo "Remote stream port $port is already in use; refusing to overwrite it." >&2
  ss -H -ltnp "sport = :$port" >&2 || true
  exit 1
fi

source "$conda_sh"
conda activate "$conda_env"
python "$repo_root/Stream-DeepLabCut/check_pyspin_camera.py"
if [[ "$deep_check" -eq 1 ]]; then
  python "$repo_root/Cam-Tests/VerCheck.py" --strict
fi
REMOTE
}

run_preflight() {
  if [[ "$MODE" == "transport-test" || "$MODE" == "full-test" ]]; then
    normalize_matlab_bin
  fi
  parse_endpoints
  acquire_lock
  local_preflight
  remote_preflight || die "Eye-computer preflight failed."
  echo "Two-computer EyeTrack preflight passed."
}

start_streamer() {
  local -a streamer_args=(
    --model-preset yanglab-pupil8
    --model-type base
    --camera-index 0
    --sensor-roi 0 0 640 480
    --frame-rate 60
    --exposure-us 6000
    --gain-auto continuous
    --display-scale 2
  )

  if [[ -n "$MODEL_PATH" ]]; then
    streamer_args+=(--model-path "$MODEL_PATH")
  fi
  streamer_args+=("${STREAMER_EXTRA_ARGS[@]}")
  streamer_args+=(--address "$ADDRESS" --display --display-fps 5)

  RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/eyetrack-supervisor.XXXXXX")" ||
    die "Could not create a supervisor log directory."
  STREAMER_LOG="$RUN_DIR/streamer.log"
  STREAMER_STATUS_LOG="$RUN_DIR/streamer-status.log"
  RECEIVER_LOG="$RUN_DIR/receiver.log"
  SUPERVISOR_LOG="$RUN_DIR/supervisor.log"
  echo "Session logs: $RUN_DIR"
  echo "Starting remote eye streamer with X11 display at 5 display FPS (scale 2 by default)..."

  "$SETSID_BIN" "$START_SCRIPT" \
    --host "$HOST" \
    --remote-repo "$REMOTE_REPO" \
    --conda-sh "$REMOTE_CONDA_SH" \
    --conda-env "$REMOTE_CONDA_ENV" \
    -- "${streamer_args[@]}" >"$STREAMER_LOG" 2>&1 &
  STREAMER_PID=$!
  STREAMER_PGID="$STREAMER_PID"
  REMOTE_STARTED=1
}

wait_for_streamer() {
  local deadline=$((SECONDS + STARTUP_TIMEOUT_S))

  echo "Waiting for remote streamer at $ADDRESS..."
  while (( SECONDS < deadline )); do
    if ! pid_is_running "$STREAMER_PID"; then
      tail_log "streamer" "$STREAMER_LOG"
      die "Remote streamer launcher exited before readiness."
    fi
    if "$STATUS_SCRIPT" \
      --host "$HOST" \
      --address "$ADDRESS" \
      --csv-dir /tmp/EyeTrack >"$STREAMER_STATUS_LOG" 2>&1; then
      echo "Remote streamer is listening."
      return 0
    fi
    sleep "$POLL_INTERVAL_S"
  done
  tail_log "streamer" "$STREAMER_LOG"
  tail_log "streamer status" "$STREAMER_STATUS_LOG"
  die "Timed out after ${STARTUP_TIMEOUT_S}s waiting for the remote streamer."
}

start_receiver() {
  echo "Starting local deferred receiver at $RECEIVER_URL..."
  export BB_EYETRACK_ZMQ_ADDRESS="$ADDRESS"
  export BB_EYETRACK_RECEIVER_URL="$RECEIVER_URL"

  # Job control prevents a background Python process from inheriting SIGINT as
  # ignored, allowing exact-PID SIGINT cleanup to run the receiver's finally path.
  set -m
  "$RECEIVER_PYTHON" "$RECEIVER_SCRIPT" \
    --address "$ADDRESS" \
    --api-host "$RECEIVER_HOST" \
    --api-port "$RECEIVER_PORT" >"$RECEIVER_LOG" 2>&1 &
  RECEIVER_PID=$!
  set +m
}

health_is_ready() {
  local payload=""

  payload="$("$CURL_BIN" -fsS --max-time 2 "$RECEIVER_URL/health" 2>/dev/null)" || return 1
  EYETRACK_HEALTH_JSON="$payload" "$HEALTH_PYTHON" -c '
import json
import os
import sys

payload = json.loads(os.environ["EYETRACK_HEALTH_JSON"])
expected = sys.argv[1]
ready = (
    payload.get("ok") is True
    and payload.get("address") == expected
    and int(payload.get("samples_received") or 0) > 0
)
raise SystemExit(0 if ready else 1)
' "$ADDRESS" >/dev/null 2>&1
}

wait_for_receiver() {
  local deadline=$((SECONDS + STARTUP_TIMEOUT_S))

  echo "Waiting for receiver API and at least one eye-stream sample..."
  while (( SECONDS < deadline )); do
    if ! pid_is_running "$RECEIVER_PID"; then
      tail_log "receiver" "$RECEIVER_LOG"
      die "Local receiver exited before readiness."
    fi
    if ! pid_is_running "$STREAMER_PID"; then
      tail_log "streamer" "$STREAMER_LOG"
      die "Remote streamer exited while waiting for receiver readiness."
    fi
    if health_is_ready; then
      echo "Receiver is healthy and receiving samples from $ADDRESS."
      return 0
    fi
    sleep "$POLL_INTERVAL_S"
  done
  tail_log "receiver" "$RECEIVER_LOG"
  die "Timed out after ${STARTUP_TIMEOUT_S}s waiting for receiver samples."
}

run_smoke_test() {
  local -a command=(
    "$RECEIVER_PYTHON" "$MATLAB_TEST_SCRIPT"
    --address "$ADDRESS"
    --receiver-url "$RECEIVER_URL"
    --behaviorbox-root "$BEHAVIORBOX_ROOT"
    --duration 10
    --matlab-bin "$MATLAB_BIN"
  )

  if [[ "$MODE" == "transport-test" ]]; then
    command+=(--transport-only)
  fi
  echo "Running ${MODE}..."
  "${command[@]}"
}

supervise_services() {
  echo
  echo "Eye tracking is ready."
  echo "MATLAB and BehaviorBox remain under operator control and were not started by this supervisor."
  echo "Start the BehaviorBox session after warm-up. After the session is saved,"
  echo "return here and press Ctrl+C to stop the receiver and streamer."
  echo "MATLAB should contain these endpoint values before the BehaviorBox session starts:"
  echo "  BB_EYETRACK_ZMQ_ADDRESS=$ADDRESS"
  echo "  BB_EYETRACK_RECEIVER_URL=$RECEIVER_URL"
  echo "Verify non-default values with MATLAB getenv/setenv; this supervisor cannot"
  echo "change the environment of an already-running MATLAB process."
  echo
  while true; do
    if ! pid_is_running "$STREAMER_PID"; then
      tail_log "streamer" "$STREAMER_LOG"
      return 1
    fi
    if ! pid_is_running "$RECEIVER_PID"; then
      tail_log "receiver" "$RECEIVER_LOG"
      return 1
    fi
    sleep 1
  done
}

main() {
  run_preflight
  if [[ "$MODE" == "check" ]]; then
    return 0
  fi

  start_streamer
  wait_for_streamer
  start_receiver
  wait_for_receiver

  if [[ "$MODE" == "transport-test" || "$MODE" == "full-test" ]]; then
    run_smoke_test
    return $?
  fi

  supervise_services
}

main
exit $?
