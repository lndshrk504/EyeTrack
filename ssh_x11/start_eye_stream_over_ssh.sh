#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ssh_x11_common.sh
source "$SCRIPT_DIR/ssh_x11_common.sh"

HOST=""
REMOTE_REPO='~/Desktop/BehaviorBox/EyeTrack'
CONDA_SH='~/miniforge3/etc/profile.d/conda.sh'
CONDA_ENV='dlclivegui'
EXTRA_ARGS=()
USE_X11=0
HAS_DISPLAY_FLAG=0
HAS_DISPLAY_FPS=0
DISPLAY_MODE=""

usage() {
  cat <<'EOF'
Usage:
  ./start_eye_stream_over_ssh.sh --host USER@HOST [options] -- [run_eye_stream_production.py args...]

Options:
  --host USER@HOST      Required SSH target for the eye-tracking computer
  --remote-repo PATH    Remote EyeTrack repo root. Default: ~/Desktop/BehaviorBox/EyeTrack
  --conda-sh PATH       Remote conda.sh path. Default: ~/miniforge3/etc/profile.d/conda.sh
  --conda-env NAME      Remote conda environment. Default: dlclivegui
  -h, --help            Show this help

Any arguments after -- are passed directly to Stream-DeepLabCut/run_eye_stream_production.py.
If neither --display nor --no-display is passed, this wrapper adds --display.
When display is enabled without an explicit --display-fps, it adds --display-fps 5.
Use --no-display explicitly for a headless run.
EOF
}

require_display() {
  if [[ -z "${DISPLAY:-}" ]]; then
    echo "DISPLAY is empty on this computer. Run this from a graphical desktop session or use --no-display." >&2
    exit 1
  fi
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
    --conda-sh)
      ssh_x11_require_option_value "$1" "$#"
      CONDA_SH="$2"
      shift 2
      ;;
    --conda-env)
      ssh_x11_require_option_value "$1" "$#"
      CONDA_ENV="$2"
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

if [[ -z "$HOST" ]]; then
  echo "--host is required." >&2
  usage >&2
  exit 1
fi

for arg in "${EXTRA_ARGS[@]}"; do
  if [[ "$arg" == "--display" ]]; then
    HAS_DISPLAY_FLAG=1
    DISPLAY_MODE="display"
  elif [[ "$arg" == "--no-display" ]]; then
    HAS_DISPLAY_FLAG=1
    DISPLAY_MODE="no-display"
  elif [[ "$arg" == "--display-fps" || "$arg" == --display-fps=* ]]; then
    HAS_DISPLAY_FPS=1
  fi
done

if [[ "$HAS_DISPLAY_FLAG" -eq 0 ]]; then
  EXTRA_ARGS+=(--display)
  DISPLAY_MODE="display"
fi

if [[ "$DISPLAY_MODE" == "display" && "$HAS_DISPLAY_FPS" -eq 0 ]]; then
  EXTRA_ARGS+=(--display-fps 5)
fi

if [[ "$DISPLAY_MODE" == "display" ]]; then
  USE_X11=1
fi

if [[ "$USE_X11" -eq 1 ]]; then
  require_display
  SSH_ARGS=(-Y)
else
  SSH_ARGS=()
fi

echo "Starting remote eye stream on ${HOST}..."
echo "Remote repo: ${REMOTE_REPO}"
echo "Remote conda env: ${CONDA_ENV}"
if [[ "$USE_X11" -eq 1 ]]; then
  echo "Mode: X11-forwarded preview"
else
  echo "Mode: headless (--no-display)"
fi

ssh_x11_build_remote_command \
  bash -s -- "$REMOTE_REPO" "$CONDA_SH" "$CONDA_ENV" "${EXTRA_ARGS[@]}"
ssh "${SSH_ARGS[@]}" "$HOST" "$SSH_X11_REMOTE_COMMAND" <<'REMOTE'
set -euo pipefail

repo_root="$1"
conda_sh="$2"
conda_env="$3"
shift 3

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

if [[ ! -f "$conda_sh" ]]; then
  echo "Remote conda.sh not found: $conda_sh" >&2
  exit 1
fi

source "$conda_sh"
conda activate "$conda_env"

cd "$repo_root/Stream-DeepLabCut"
./run_eye_stream_production.py "$@"
REMOTE
