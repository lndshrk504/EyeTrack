#!/usr/bin/env bash
# Source this file on the behavior computer before starting the receiver
# service or MATLAB.
#
# It defines the environment variables used by the current deferred eye path:
# - BB_EYETRACK_ZMQ_ADDRESS      remote streamer ZMQ address
# - BB_EYETRACK_RECEIVER_URL     local receiver HTTP API URL
# - BB_EYETRACK_RECEIVER_PYTHON  convenience path for launching the receiver
#
# BehaviorBox itself reads:
# - BB_EYETRACK_ZMQ_ADDRESS
# - BB_EYETRACK_RECEIVER_URL
#
# The receiver Python path is a shell convenience only. BehaviorBox does not
# read it directly.
#
# Usage from the Stream-DeepLabCut directory:
#   source ./behavior_eye_tracking_env.sh
#   "$BB_EYETRACK_RECEIVER_PYTHON" ./run_eye_receiver_service.py
#   cd /path/to/BehaviorBox
#   matlab
#
# Or source one of the profile-specific wrappers:
#   source ./set_behavior_env_bbeyezmq.sh
#   source ./set_behavior_env_dlclivegui.sh
#
# Defaults to the small bbeyezmq environment.

export BB_EYETRACK_ZMQ_ADDRESS="${BB_EYETRACK_ZMQ_ADDRESS:-tcp://10.55.0.1:5555}"
export BB_EYETRACK_RECEIVER_URL="${BB_EYETRACK_RECEIVER_URL:-http://127.0.0.1:8765}"

PY_PROFILE="${BB_EYETRACK_RECEIVER_PYTHON_PROFILE:-bbeyezmq}"

case "$PY_PROFILE" in
    bbeyezmq|dlclivegui)
        ;;
    *)
        echo "Unknown receiver Python profile '$PY_PROFILE'; use bbeyezmq or dlclivegui." >&2
        ;;
esac

if [[ -x "$HOME/miniforge3/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_RECEIVER_PYTHON="$HOME/miniforge3/envs/$PY_PROFILE/bin/python"
elif [[ -x "$HOME/mambaforge/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_RECEIVER_PYTHON="$HOME/mambaforge/envs/$PY_PROFILE/bin/python"
elif [[ -x "$HOME/miniconda3/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_RECEIVER_PYTHON="$HOME/miniconda3/envs/$PY_PROFILE/bin/python"
elif [[ -x "$HOME/anaconda3/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_RECEIVER_PYTHON="$HOME/anaconda3/envs/$PY_PROFILE/bin/python"
else
    export BB_EYETRACK_RECEIVER_PYTHON="$HOME/miniforge3/envs/$PY_PROFILE/bin/python"
fi
