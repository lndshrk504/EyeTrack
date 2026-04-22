#!/usr/bin/env bash
# Source this file (do not execute) from the ToMatlab directory:
#   source ./set_behavior_env_dlclivegui.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This file must be sourced: source \"${BASH_SOURCE[0]}\"" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BB_EYETRACK_PYTHON_PROFILE="dlclivegui"
source "$SCRIPT_DIR/behavior_eye_tracking_env.sh"
