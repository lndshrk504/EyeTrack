#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STREAM_DIR="$ROOT_DIR/Stream-DeepLabCut"
SSH_DIR="$ROOT_DIR/ssh_x11"
CAPTURE_SCRIPT="$SSH_DIR/open_training_capture_over_ssh.sh"

# shellcheck source=Stream-DeepLabCut/behavior_eye_tracking_env.sh
source "$STREAM_DIR/behavior_eye_tracking_env.sh"

HOST="${EYETRACK_EYE_HOST:-wbs@10.55.0.1}"
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  ./run_two_computer_training_capture.sh [--host USER@HOST] [-- capture-cmd-args...]

Default behavior:
  Runs:
    ./ssh_x11/open_training_capture_over_ssh.sh --host <host> -- --auto-contrast --scale 2

Options:
  --host USER@HOST   Override the eye-tracking computer SSH target.
                     Default: wbs@10.55.0.1 (from EYETRACK_EYE_HOST or fallback)
  -h, --help         Show this help message.

Any arguments after `--` are passed directly to
`Cam-Tests/capture_flir_training_frames.py` on the remote host.
EOF
}

require_option_value() {
  local option="$1"
  local remaining="$2"
  if (( remaining < 2 )); then
    echo "$option requires a value." >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      require_option_value "$1" "$#"
      HOST="$2"
      shift 2
      ;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ${#EXTRA_ARGS[@]} -eq 0 ]]; then
  EXTRA_ARGS=(--auto-contrast --scale 2)
else
  EXTRA_ARGS=(--auto-contrast --scale 2 "${EXTRA_ARGS[@]}")
fi

echo "Launching training image capture on ${HOST}..."

"$CAPTURE_SCRIPT" --host "$HOST" -- "${EXTRA_ARGS[@]}"
