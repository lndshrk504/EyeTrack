#!/usr/bin/env bash

set -euo pipefail

HOST=""

usage() {
  cat <<'EOF'
Usage:
  ./eye_stream_status_over_ssh.sh --host USER@HOST
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
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

ssh "$HOST" bash -s <<'REMOTE'
set -euo pipefail

echo "== Matching processes =="
pgrep -af 'run_eye_stream_production.py|dlc_eye_streamer.py' || echo "No eye-stream processes found."

echo
echo "== Listening sockets on port 5555 =="
ss -ltnp | grep ':5555' || echo "Nothing listening on port 5555."

echo
echo "== Recent CSV files =="
ls -1t /tmp/EyeTrack/eye_stream_*.csv 2>/dev/null | head -n 5 || true
REMOTE
