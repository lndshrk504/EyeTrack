#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ssh_x11_common.sh
source "$SCRIPT_DIR/ssh_x11_common.sh"

HOST=""
REMOTE_REPO='~/Desktop/BehaviorBox/EyeTrack'
TIMEOUT_S=10
POLL_INTERVAL_S=0.25

usage() {
  cat <<'EOF'
Usage:
  ./stop_eye_stream_over_ssh.sh --host USER@HOST [options]

Options:
  --host USER@HOST          Required SSH target for the eye-tracking computer
  --remote-repo PATH        Remote EyeTrack repo root
                            Default: ~/Desktop/BehaviorBox/EyeTrack
  --timeout-s SECONDS       Graceful-stop timeout. Default: 10
  --poll-interval-s SECONDS Process polling interval. Default: 0.25
  -h, --help                Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      ssh_x11_require_option_value "$1" "$#"
      HOST="$2"
      shift 2
      ;;
    --remote-repo)
      ssh_x11_require_option_value "$1" "$#"
      REMOTE_REPO="$2"
      shift 2
      ;;
    --timeout-s)
      ssh_x11_require_option_value "$1" "$#"
      TIMEOUT_S="$2"
      shift 2
      ;;
    --poll-interval-s)
      ssh_x11_require_option_value "$1" "$#"
      POLL_INTERVAL_S="$2"
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

if [[ ! "$TIMEOUT_S" =~ ^[0-9]+$ ]]; then
  echo "--timeout-s must be a nonnegative integer." >&2
  exit 1
fi
if [[ ! "$POLL_INTERVAL_S" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] ||
  [[ "$POLL_INTERVAL_S" =~ ^0*([.]0*)?$ ]]; then
  echo "--poll-interval-s must be a positive number." >&2
  exit 1
fi

ssh_x11_build_remote_command \
  bash -s -- "$REMOTE_REPO" "$TIMEOUT_S" "$POLL_INTERVAL_S"
ssh "$HOST" "$SSH_X11_REMOTE_COMMAND" <<'REMOTE'
set -euo pipefail

repo_root="$1"
timeout_s="$2"
poll_interval_s="$3"

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
expanded_repo_root="$repo_root"
if ! repo_root="$(readlink -f -- "$expanded_repo_root")"; then
  echo "Remote EyeTrack repository path does not exist: $expanded_repo_root" >&2
  exit 1
fi
if [[ ! -d "$repo_root/Stream-DeepLabCut" ]]; then
  echo "Remote EyeTrack runtime directory not found: $repo_root/Stream-DeepLabCut" >&2
  exit 1
fi

streamer_pattern="$repo_root/Stream-DeepLabCut/dlc_eye_streamer.py"
launcher_pattern="$repo_root/Stream-DeepLabCut/run_eye_stream_production.py"
stream_dir="$repo_root/Stream-DeepLabCut"

process_matches_target() {
  local pid="$1"
  local command="$2"
  local cwd=""
  local arg
  local -a argv=()

  if [[ -r "/proc/$pid/cmdline" ]]; then
    if ! mapfile -d '' -t argv <"/proc/$pid/cmdline"; then
      return 1
    fi
    for arg in "${argv[@]}"; do
      if [[ "$arg" == "$streamer_pattern" || "$arg" == "$launcher_pattern" ]]; then
        return 0
      fi
      if [[ "$arg" == "dlc_eye_streamer.py" || "$arg" == "./dlc_eye_streamer.py" ||
        "$arg" == "run_eye_stream_production.py" || "$arg" == "./run_eye_stream_production.py" ]]; then
        cwd="$(readlink -f -- "/proc/$pid/cwd" 2>/dev/null || true)"
        [[ "$cwd" == "$stream_dir" ]] && return 0
      fi
    done
    return 1
  fi

  if [[ "$command" == *"$streamer_pattern"* || "$command" == *"$launcher_pattern"* ]]; then
    return 0
  fi
  if [[ "$command" == *"dlc_eye_streamer.py"* ||
    "$command" == *"run_eye_stream_production.py"* ]]; then
    cwd="$(readlink -f -- "/proc/$pid/cwd" 2>/dev/null || true)"
    [[ "$cwd" == "$stream_dir" ]] && return 0
  fi
  return 1
}

find_matching_pids() {
  local pid
  local command

  MATCHING_PIDS=()
  while read -r pid command; do
    if process_matches_target "$pid" "$command"; then
      MATCHING_PIDS+=("$pid")
    fi
  done < <(ps -eo pid=,args=)
}

find_matching_pids
if [[ ${#MATCHING_PIDS[@]} -eq 0 ]]; then
  echo "No matching eye-stream processes were running."
  exit 0
fi

echo "Sending SIGINT to eye-stream PIDs: ${MATCHING_PIDS[*]}"
kill -INT "${MATCHING_PIDS[@]}" 2>/dev/null || true

deadline=$((SECONDS + timeout_s))
while true; do
  find_matching_pids
  if [[ ${#MATCHING_PIDS[@]} -eq 0 ]]; then
    echo "All matching eye-stream processes stopped."
    exit 0
  fi
  if (( SECONDS >= deadline )); then
    break
  fi
  sleep "$poll_interval_s"
done

echo "Eye-stream processes remained after ${timeout_s}s: ${MATCHING_PIDS[*]}" >&2
for pid in "${MATCHING_PIDS[@]}"; do
  ps -p "$pid" -o pid=,args= >&2 || true
done
exit 1
REMOTE
