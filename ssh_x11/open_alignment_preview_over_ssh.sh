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

usage() {
  cat <<'EOF'
Usage:
  ./open_alignment_preview_over_ssh.sh --host USER@HOST [options] -- [FLIRCam.py args...]

Options:
  --host USER@HOST      Required SSH target for the eye-tracking computer
  --remote-repo PATH    Remote EyeTrack repo root. Default: ~/Desktop/BehaviorBox/EyeTrack
  --conda-sh PATH       Remote conda.sh path. Default: ~/miniforge3/etc/profile.d/conda.sh
  --conda-env NAME      Remote conda environment. Default: dlclivegui
  -h, --help            Show this help

Any arguments after -- are passed directly to Cam-Tests/FLIRCam.py.
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

require_display

if [[ ${#EXTRA_ARGS[@]} -eq 0 ]]; then
  EXTRA_ARGS=(--auto-contrast --scale 0.5)
fi

echo "Opening forwarded FLIR alignment preview from ${HOST}..."
echo "Remote repo: ${REMOTE_REPO}"
echo "Remote conda env: ${CONDA_ENV}"

ssh_x11_build_remote_command \
  bash -s -- "$REMOTE_REPO" "$CONDA_SH" "$CONDA_ENV" "${EXTRA_ARGS[@]}"
ssh -Y "$HOST" "$SSH_X11_REMOTE_COMMAND" <<'REMOTE'
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

cd "$repo_root/Cam-Tests"
python FLIRCam.py "$@"
REMOTE
