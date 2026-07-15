#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ssh_x11_common.sh
source "$SCRIPT_DIR/ssh_x11_common.sh"

HOST=""
ADDRESS="tcp://127.0.0.1:5555"
ADDRESS_HOST=""
PORT=""
CSV_DIR="/tmp/EyeTrack"
PORT_SET=0

usage() {
  cat <<'EOF'
Usage:
  ./eye_stream_status_over_ssh.sh --host USER@HOST [options]

Options:
  --host USER@HOST      Required SSH target for the eye-tracking computer
  --address ENDPOINT    Stream endpoint. Default: tcp://127.0.0.1:5555
  --port PORT           Listening port to inspect; overrides the address port
  --csv-dir PATH        Remote streamer output directory. Default: /tmp/EyeTrack
  -h, --help            Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      ssh_x11_require_option_value "$1" "$#"
      HOST="$2"
      shift 2
      ;;
    --address)
      ssh_x11_require_option_value "$1" "$#"
      ADDRESS="$2"
      shift 2
      ;;
    --port)
      ssh_x11_require_option_value "$1" "$#"
      PORT="$2"
      PORT_SET=1
      shift 2
      ;;
    --csv-dir)
      ssh_x11_require_option_value "$1" "$#"
      CSV_DIR="$2"
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

if [[ "$ADDRESS" =~ ^tcp://(\[[^]]+\]|[^:]+):([0-9]+)$ ]]; then
  ADDRESS_HOST="${BASH_REMATCH[1]}"
  ADDRESS_PORT="${BASH_REMATCH[2]}"
else
  echo "--address must use the form tcp://HOST:PORT: $ADDRESS" >&2
  exit 1
fi

if [[ "$PORT_SET" -eq 0 ]]; then
  PORT="$ADDRESS_PORT"
fi

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "--port must be an integer from 1 through 65535." >&2
  exit 1
fi
ADDRESS="tcp://${ADDRESS_HOST}:${PORT}"

ssh_x11_build_remote_command bash -s -- "$ADDRESS" "$ADDRESS_HOST" "$PORT" "$CSV_DIR"
ssh "$HOST" "$SSH_X11_REMOTE_COMMAND" <<'REMOTE'
set -euo pipefail

address="$1"
requested_host="$2"
port="$3"
csv_dir="$4"

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

csv_dir="$(expand_path "$csv_dir")"
status=0

normalize_host() {
  local host="$1"
  host="${host#[}"
  host="${host%]}"
  printf '%s\n' "${host,,}"
}

listener_serves_requested_host() {
  local listener_host
  local normalized_requested_host
  local resolved_host

  listener_host="$(normalize_host "$1")"
  normalized_requested_host="$(normalize_host "$requested_host")"

  case "$listener_host" in
    '*'|0.0.0.0|::)
      return 0
      ;;
  esac
  if [[ "$listener_host" == "$normalized_requested_host" ]]; then
    return 0
  fi
  if [[ "$normalized_requested_host" == "localhost" ]] &&
    [[ "$listener_host" == "127.0.0.1" || "$listener_host" == "::1" ]]; then
    return 0
  fi
  if [[ "$listener_host" == "localhost" ]] &&
    [[ "$normalized_requested_host" == "127.0.0.1" || "$normalized_requested_host" == "::1" ]]; then
    return 0
  fi
  if command -v getent >/dev/null 2>&1; then
    while read -r resolved_host _; do
      if [[ "$(normalize_host "$resolved_host")" == "$listener_host" ]]; then
        return 0
      fi
    done < <(getent ahosts "$normalized_requested_host" 2>/dev/null || true)
  fi
  return 1
}

socket_owned_by_eye_process() {
  local socket_details="$1"
  local pid

  for pid in "${EYE_PIDS[@]}"; do
    if [[ "$socket_details" == *"pid=${pid},"* || "$socket_details" == *"pid=${pid})"* ]]; then
      return 0
    fi
  done
  return 1
}

echo "== Matching processes =="
mapfile -t eye_processes < <(
  pgrep -af 'run_eye_stream_production.py|dlc_eye_streamer.py' || true
)
EYE_PIDS=()
if [[ ${#eye_processes[@]} -eq 0 ]]; then
  echo "No eye-stream processes found."
  status=1
else
  printf '%s\n' "${eye_processes[@]}"
  for process_line in "${eye_processes[@]}"; do
    process_pid="${process_line%% *}"
    if [[ "$process_pid" =~ ^[0-9]+$ ]]; then
      EYE_PIDS+=("$process_pid")
    fi
  done
fi

echo
echo "== Requested endpoint =="
echo "Address: $address"
echo "Listening port: $port"
if ! command -v ss >/dev/null 2>&1; then
  echo "Cannot inspect listening sockets because ss is not installed." >&2
  status=1
elif ! socket_output="$(ss -H -ltnp)"; then
  echo "The ss command failed while inspecting listening sockets." >&2
  status=1
else
  endpoint_sockets=""
  matching_sockets=""
  while read -r state recv_q send_q local_address rest; do
    if [[ "$local_address" == *":$port" ]] &&
      listener_serves_requested_host "${local_address%:*}"; then
      socket_line="${state} ${recv_q} ${send_q} ${local_address} ${rest}"
      endpoint_sockets+="${socket_line}"$'\n'
      if socket_owned_by_eye_process "$rest"; then
        matching_sockets+="${socket_line}"$'\n'
      fi
    fi
  done <<<"$socket_output"
  if [[ -z "$matching_sockets" ]]; then
    if [[ -n "$endpoint_sockets" ]]; then
      echo "A listener exists for $address, but it is not owned by a matching EyeTrack process."
      printf '%s' "$endpoint_sockets"
    else
      echo "Nothing listening for $address."
    fi
    status=1
  else
    printf '%s' "$matching_sockets"
  fi
fi

echo
echo "== Recent CSV files =="
echo "Directory: $csv_dir"
if [[ ! -d "$csv_dir" ]]; then
  echo "Output directory does not exist."
else
  mapfile -t recent_csvs < <(
    find "$csv_dir" -maxdepth 1 -type f -name 'eye_stream_*.csv' \
      -printf '%T@ %p\n' | sort -rn
  )
  if [[ ${#recent_csvs[@]} -eq 0 ]]; then
    echo "No eye-stream CSV files found."
  else
    for entry in "${recent_csvs[@]:0:5}"; do
      echo "${entry#* }"
    done
  fi
fi

exit "$status"
REMOTE
