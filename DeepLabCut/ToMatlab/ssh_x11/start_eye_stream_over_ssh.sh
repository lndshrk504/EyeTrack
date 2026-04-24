#!/usr/bin/env bash

set -euo pipefail

HOST=""
REMOTE_REPO='~/Desktop/BehaviorBox/EyeTrack'
CONDA_SH='~/miniforge3/etc/profile.d/conda.sh'
CONDA_ENV='dlclivegui'
EXTRA_ARGS=()
USE_X11=0
HAS_DISPLAY_FLAG=0

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

Any arguments after -- are passed directly to DeepLabCut/ToMatlab/run_eye_stream_production.py.
If neither --display nor --no-display is passed, this wrapper adds --no-display.
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
      HOST="$2"
      shift 2
      ;;
    --remote-repo)
      REMOTE_REPO="$2"
      shift 2
      ;;
    --conda-sh)
      CONDA_SH="$2"
      shift 2
      ;;
    --conda-env)
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
  if [[ "$arg" == "--display" || "$arg" == "--no-display" ]]; then
    HAS_DISPLAY_FLAG=1
  fi
  if [[ "$arg" == "--display" ]]; then
    USE_X11=1
  fi
done

if [[ "$HAS_DISPLAY_FLAG" -eq 0 ]]; then
  EXTRA_ARGS+=(--no-display)
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

ssh "${SSH_ARGS[@]}" "$HOST" bash -s -- "$REMOTE_REPO" "$CONDA_SH" "$CONDA_ENV" "${EXTRA_ARGS[@]}" <<'REMOTE'
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
conda_sh="$(expand_path "$conda_sh")"

if [[ ! -f "$conda_sh" ]]; then
  echo "Remote conda.sh not found: $conda_sh" >&2
  exit 1
fi

source "$conda_sh"
conda activate "$conda_env"

cd "$repo_root/DeepLabCut/ToMatlab"
./run_eye_stream_production.py "$@"
REMOTE
