#!/usr/bin/env bash

set -euo pipefail

HOST=""
TRY_XCLOCK=0

usage() {
  cat <<'EOF'
Usage:
  ./test_x11_forwarding_over_ssh.sh --host USER@HOST [--try-xclock]

Options:
  --host USER@HOST      Required SSH target for the eye-tracking computer
  --try-xclock          Run xclock remotely if it is installed
  -h, --help            Show this help
EOF
}

require_display() {
  if [[ -z "${DISPLAY:-}" ]]; then
    echo "DISPLAY is empty on this computer. Run this from a graphical desktop session." >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --try-xclock)
      TRY_XCLOCK=1
      shift
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

if [[ -z "$HOST" ]]; then
  echo "--host is required." >&2
  usage >&2
  exit 1
fi

require_display

echo "Local DISPLAY: ${DISPLAY}"
echo "Testing SSH/X11 forwarding to ${HOST}..."

ssh -Y "$HOST" bash -s -- "$TRY_XCLOCK" <<'REMOTE'
set -euo pipefail

try_xclock="$1"

echo "Remote DISPLAY: ${DISPLAY:-}"
if [[ -z "${DISPLAY:-}" ]]; then
  echo "Remote DISPLAY is empty; X11 forwarding is not active." >&2
  exit 1
fi

if ! command -v xauth >/dev/null 2>&1; then
  echo "xauth is missing on the eye-tracking computer." >&2
  exit 1
fi
echo "xauth: $(command -v xauth)"

if [[ "$try_xclock" == "1" ]]; then
  if command -v xclock >/dev/null 2>&1; then
    echo "Starting xclock. Close the xclock window to finish this test."
    xclock
  else
    echo "xclock is not installed; skipping the visual xclock test."
  fi
fi

echo "SSH/X11 forwarding checks passed."
REMOTE
