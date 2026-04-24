#!/usr/bin/env bash

set -euo pipefail

ORIGINAL_ARGS=("$@")
BEHAVIOR_IP="10.55.0.2"
INSTALL_MISSING=0
CONFIGURE_UFW=1
CONF_DIR="/etc/ssh/sshd_config.d"
CONF_FILE="${CONF_DIR}/60-eyetrack-x11.conf"

usage() {
  cat <<'EOF'
Usage:
  sudo ./setup_eye_host_ssh_x11.sh [options]

Options:
  --behavior-ip IP      Behavior-computer IP allowed through ufw. Default: 10.55.0.2
  --conf-file PATH      SSH drop-in config path. Default: /etc/ssh/sshd_config.d/60-eyetrack-x11.conf
  --install-missing     Install missing openssh-server/xauth with apt
  --skip-ufw            Do not modify ufw rules
  -h, --help            Show this help
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

maybe_install_missing() {
  local missing=()

  if ! command -v sshd >/dev/null 2>&1; then
    missing+=(openssh-server)
  fi
  if ! command -v xauth >/dev/null 2>&1; then
    missing+=(xauth)
  fi

  if [[ ${#missing[@]} -eq 0 ]]; then
    return
  fi

  if [[ "$INSTALL_MISSING" -ne 1 ]]; then
    echo "Missing packages: ${missing[*]}" >&2
    echo "Re-run with --install-missing to install them." >&2
    exit 1
  fi

  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y "${missing[@]}"
}

write_sshd_dropin() {
  if ! grep -Eq '^[[:space:]]*Include[[:space:]]+/etc/ssh/sshd_config\.d/\*\.conf([[:space:]]|$)' /etc/ssh/sshd_config; then
    echo "Expected /etc/ssh/sshd_config to include /etc/ssh/sshd_config.d/*.conf on Pop!_OS." >&2
    echo "Refusing to guess at sshd_config edits. Add the Include line manually or pass a different --conf-file path." >&2
    exit 1
  fi

  mkdir -p "$(dirname "$CONF_FILE")"
  cat >"$CONF_FILE" <<'EOF'
# Managed by setup_eye_host_ssh_x11.sh for EyeTrack SSH/X11 forwarding.
X11Forwarding yes
X11UseLocalhost yes
EOF
}

configure_ufw() {
  if [[ "$CONFIGURE_UFW" -ne 1 ]]; then
    return
  fi

  if ! command -v ufw >/dev/null 2>&1; then
    echo "ufw not installed; skipping firewall rules." >&2
    return
  fi

  if ! ufw status | head -n 1 | grep -qi "Status: active"; then
    echo "ufw is not active; skipping firewall rules." >&2
    return
  fi

  ufw allow from "$BEHAVIOR_IP" to any port 22 proto tcp
  ufw allow from "$BEHAVIOR_IP" to any port 5555 proto tcp
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --behavior-ip)
      BEHAVIOR_IP="$2"
      shift 2
      ;;
    --conf-file)
      CONF_FILE="$2"
      shift 2
      ;;
    --install-missing)
      INSTALL_MISSING=1
      shift
      ;;
    --skip-ufw)
      CONFIGURE_UFW=0
      shift
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

if [[ "${EUID}" -ne 0 ]]; then
  exec sudo "$0" "${ORIGINAL_ARGS[@]}"
fi

require_cmd grep
require_cmd systemctl

maybe_install_missing
write_sshd_dropin
require_cmd sshd
sshd -t

systemctl enable ssh >/dev/null
systemctl restart ssh
configure_ufw

echo "SSH/X11 forwarding setup complete."
echo "SSH drop-in: $CONF_FILE"
echo "Behavior computer allowed IP: $BEHAVIOR_IP"
echo "Next step from the behavior computer:"
echo "  ./open_alignment_preview_over_ssh.sh --host USER@<eye-tracking-ip>"
