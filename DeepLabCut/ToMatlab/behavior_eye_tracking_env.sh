#!/usr/bin/env bash
# Source this file on the behavior computer before starting MATLAB.
# It defines the two environment variables needed by BehaviorBox:
# - BB_EYETRACK_ZMQ_ADDRESS
# - BB_EYETRACK_PYTHON
#
# Usage from the ToMatlab directory:
#   source ./behavior_eye_tracking_env.sh
#   cd /path/to/BehaviorBox
#   matlab
#
# Or source one of the profile-specific wrappers:
#   source ./set_behavior_env_bbeyezmq.sh
#   source ./set_behavior_env_dlclivegui.sh
#
# Defaults to the small bbeyezmq environment.
# Override manually with:
#   export BB_EYETRACK_PYTHON_PROFILE=dlclivegui
#   source ./behavior_eye_tracking_env.sh

export BB_EYETRACK_ZMQ_ADDRESS="tcp://10.55.0.1:5555"

PY_PROFILE="${BB_EYETRACK_PYTHON_PROFILE:-bbeyezmq}"

case "$PY_PROFILE" in
    bbeyezmq|dlclivegui)
        ;;
    *)
        echo "Unknown BB_EYETRACK_PYTHON_PROFILE='$PY_PROFILE'; use bbeyezmq or dlclivegui." >&2
        ;;
esac

if [[ -x "$HOME/miniforge3/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_PYTHON="$HOME/miniforge3/envs/$PY_PROFILE/bin/python"
elif [[ -x "$HOME/mambaforge/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_PYTHON="$HOME/mambaforge/envs/$PY_PROFILE/bin/python"
elif [[ -x "$HOME/miniconda3/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_PYTHON="$HOME/miniconda3/envs/$PY_PROFILE/bin/python"
elif [[ -x "$HOME/anaconda3/envs/$PY_PROFILE/bin/python" ]]; then
    export BB_EYETRACK_PYTHON="$HOME/anaconda3/envs/$PY_PROFILE/bin/python"
else
    # Fallback to the exact path from the quickstart; replace if different on your system.
    export BB_EYETRACK_PYTHON="$HOME/miniforge3/envs/$PY_PROFILE/bin/python"
fi
