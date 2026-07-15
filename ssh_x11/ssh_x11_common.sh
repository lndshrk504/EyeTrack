#!/usr/bin/env bash

# Shared local-side helpers for the EyeTrack SSH wrappers.

ssh_x11_require_option_value() {
  local option="$1"
  local remaining="$2"

  if (( remaining < 2 )); then
    echo "${option} requires a value." >&2
    exit 1
  fi
}

ssh_x11_build_remote_command() {
  local arg
  local quoted

  SSH_X11_REMOTE_COMMAND=""
  for arg in "$@"; do
    # POSIX shell quoting: close the quote, emit one escaped quote, reopen it.
    quoted=${arg//\'/\'\\\'\'}
    if [[ -n "$SSH_X11_REMOTE_COMMAND" ]]; then
      SSH_X11_REMOTE_COMMAND+=" "
    fi
    SSH_X11_REMOTE_COMMAND+="'${quoted}'"
  done
}
