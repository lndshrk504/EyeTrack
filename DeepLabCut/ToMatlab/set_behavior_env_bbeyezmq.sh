#!/usr/bin/env bash
# Source this file (do not execute) from the ToMatlab directory before
# starting the receiver service or MATLAB:
#   source ./set_behavior_env_bbeyezmq.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "This file must be sourced: source \"${BASH_SOURCE[0]}\"" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export BB_EYETRACK_RECEIVER_PYTHON_PROFILE="bbeyezmq"
source "$SCRIPT_DIR/behavior_eye_tracking_env.sh"
