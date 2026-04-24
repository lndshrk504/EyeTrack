#!/usr/bin/env bash

set -euo pipefail

HOST=""
REMOTE_REPO='~/Desktop/BehaviorBox/EyeTrack'

usage() {
  cat <<'EOF'
Usage:
  ./stop_eye_stream_over_ssh.sh --host USER@HOST [--remote-repo PATH]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --remote-repo)
      REMOTE_REPO="$2"
      shift 2
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

ssh "$HOST" bash -s -- "$REMOTE_REPO" <<'REMOTE'
set -euo pipefail

repo_root="$1"

expand_path() {
  local raw="$1"
  case "$raw" in
    "~")
      printf '%s\n' "$HOME"
      ;;
    "~/"*)
      printf '%s/%s\n' "$HOME" "${raw#~/}"
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

streamer_pattern="$repo_root/DeepLabCut/ToMatlab/dlc_eye_streamer.py"
launcher_pattern="$repo_root/DeepLabCut/ToMatlab/run_eye_stream_production.py"

echo "Sending SIGINT to matching eye-stream processes..."
pkill -INT -f "$streamer_pattern" 2>/dev/null || true
pkill -INT -f "$launcher_pattern" 2>/dev/null || true
sleep 1

echo
echo "Remaining matching processes:"
pgrep -af "$streamer_pattern|$launcher_pattern" || echo "No matching processes remain."
REMOTE
