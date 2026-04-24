#!/usr/bin/env bash

set -euo pipefail

HOST=""
REMOTE_REPO='${HOME}/Desktop/BehaviorBox/EyeTrack'
CONDA_SH='${HOME}/miniforge3/etc/profile.d/conda.sh'
CONDA_ENV='dlclivegui'
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  ./open_alignment_preview_over_ssh.sh --host USER@HOST [options] -- [FLIRCam.py args...]

Options:
  --host USER@HOST      Required SSH target for the eye-tracking computer
  --remote-repo PATH    Remote EyeTrack repo root. Default: ${HOME}/Desktop/BehaviorBox/EyeTrack
  --conda-sh PATH       Remote conda.sh path. Default: ${HOME}/miniforge3/etc/profile.d/conda.sh
  --conda-env NAME      Remote conda environment. Default: dlclivegui
  -h, --help            Show this help

Any arguments after -- are passed directly to DeepLabCut/Tests/FLIRCam.py.
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

require_display

if [[ ${#EXTRA_ARGS[@]} -eq 0 ]]; then
  EXTRA_ARGS=(--auto-contrast --scale 0.5)
fi

echo "Opening forwarded FLIR alignment preview from ${HOST}..."
echo "Remote repo: ${REMOTE_REPO}"
echo "Remote conda env: ${CONDA_ENV}"

ssh -Y "$HOST" bash -s -- "$REMOTE_REPO" "$CONDA_SH" "$CONDA_ENV" "${EXTRA_ARGS[@]}" <<'REMOTE'
set -euo pipefail

repo_root="$1"
conda_sh="$2"
conda_env="$3"
shift 3

expand_path() {
  local raw="$1"
  eval "printf '%s\n' \"$raw\""
}

repo_root="$(expand_path "$repo_root")"
conda_sh="$(expand_path "$conda_sh")"

if [[ ! -f "$conda_sh" ]]; then
  echo "Remote conda.sh not found: $conda_sh" >&2
  exit 1
fi

source "$conda_sh"
conda activate "$conda_env"

cd "$repo_root/DeepLabCut/Tests"
python FLIRCam.py "$@"
REMOTE
