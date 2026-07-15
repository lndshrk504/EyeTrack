#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ssh_x11_common.sh
source "$SCRIPT_DIR/ssh_x11_common.sh"

ORIGINAL_ARGS=("$@")
BEHAVIOR_IP="10.55.0.2"
INSTALL_MISSING=0
CONFIGURE_UFW=1
DRY_RUN=0
TEST_MODE=0
TEST_ROOT="${EYETRACK_SSH_X11_TEST_ROOT:-}"
if [[ -n "$TEST_ROOT" ]]; then
  if [[ "$EUID" -eq 0 ]]; then
    echo "EYETRACK_SSH_X11_TEST_ROOT is refused when running as root." >&2
    exit 1
  fi
  if [[ "$TEST_ROOT" != /* ]]; then
    echo "EYETRACK_SSH_X11_TEST_ROOT must be an absolute path." >&2
    exit 1
  fi
  TEST_ROOT="$(realpath -m -- "$TEST_ROOT")"
  TEST_MODE=1
  CONF_DIR="$TEST_ROOT/etc/ssh/sshd_config.d"
  SSHD_CONFIG="$TEST_ROOT/etc/ssh/sshd_config"
else
  CONF_DIR="/etc/ssh/sshd_config.d"
  SSHD_CONFIG="/etc/ssh/sshd_config"
fi
CONF_FILE="${CONF_DIR}/60-eyetrack-x11.conf"

usage() {
  cat <<'EOF'
Usage:
  sudo ./setup_eye_host_ssh_x11.sh [options]

Options:
  --behavior-ip IP      Behavior-computer IP allowed through ufw. Default: 10.55.0.2
  --conf-file PATH      SSH drop-in config path. Default: /etc/ssh/sshd_config.d/60-eyetrack-x11.conf
                        Must be a direct, nonsymlinked *.conf file in
                        /etc/ssh/sshd_config.d
  --install-missing     Install missing openssh-server/xauth with apt
  --skip-ufw            Do not modify ufw rules
  --dry-run             Validate paths and show intended actions without sudo or writes
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

validate_conf_target() {
  local canonical_dir
  local canonical_file
  local filename

  require_cmd realpath
  canonical_dir="$(realpath -m -- "$CONF_DIR")"
  canonical_file="$(realpath -m -- "$CONF_FILE")"
  filename="$(basename -- "$CONF_FILE")"

  if [[ "$canonical_dir" != "$CONF_DIR" || -L "$CONF_DIR" ]]; then
    echo "SSH drop-in directory must be the real directory $CONF_DIR, not a symlink." >&2
    exit 1
  fi
  if [[ "$canonical_file" != "$CONF_FILE" || "$(dirname -- "$CONF_FILE")" != "$CONF_DIR" ]]; then
    echo "--conf-file must be a direct child of $CONF_DIR with no traversal." >&2
    exit 1
  fi
  if [[ "$filename" != *.conf || "$filename" == ".conf" ]]; then
    echo "--conf-file must end in .conf." >&2
    exit 1
  fi
  if [[ -L "$CONF_FILE" ]]; then
    echo "--conf-file must not be a symlink: $CONF_FILE" >&2
    exit 1
  fi
  if [[ -e "$CONF_FILE" && ! -f "$CONF_FILE" ]]; then
    echo "--conf-file exists but is not a regular file: $CONF_FILE" >&2
    exit 1
  fi
}

verify_active_include() {
  if [[ ! -r "$SSHD_CONFIG" ]]; then
    echo "Cannot read the SSH daemon config: $SSHD_CONFIG" >&2
    exit 1
  fi
  if ! grep -Eiq '^[[:space:]]*Include[[:space:]]+/etc/ssh/sshd_config\.d/\*\.conf([[:space:]#]|$)' "$SSHD_CONFIG"; then
    echo "Expected $SSHD_CONFIG to include /etc/ssh/sshd_config.d/*.conf." >&2
    echo "Refusing to write a drop-in that sshd would not load." >&2
    exit 1
  fi
}

print_dry_run() {
  echo "Dry run: SSH/X11 setup validation passed."
  echo "Would write SSH drop-in: $CONF_FILE"
  echo "Would validate with: sshd -t"
  echo "Would verify with: sshd -T"
  echo "Would enable and restart: ssh.service"
  if [[ "$CONFIGURE_UFW" -eq 1 ]]; then
    echo "Would allow TCP ports 22 and 5555 from: $BEHAVIOR_IP (when ufw is active)"
  else
    echo "Would leave ufw unchanged."
  fi
}

configure_sshd_dropin() {
  local backup_file=""
  local effective_config
  local filename
  local had_previous=0
  local preserve_backup=0
  local restart_attempted=0
  local stage_file=""
  local transaction_active=0

  filename="$(basename -- "$CONF_FILE")"

  cleanup_transaction() {
    local status=$?
    trap - EXIT

    if [[ "$transaction_active" -eq 1 ]]; then
      echo "Restoring the previous SSH drop-in after setup failure." >&2
      if [[ "$had_previous" -eq 1 ]]; then
        if mv -fT -- "$backup_file" "$CONF_FILE"; then
          backup_file=""
        else
          echo "Failed to restore the previous SSH drop-in: $CONF_FILE" >&2
          echo "Preserved the previous drop-in at: $backup_file" >&2
          preserve_backup=1
        fi
      else
        rm -f -- "$CONF_FILE"
      fi
      if ! sshd -t; then
        echo "Restored SSH configuration still fails sshd -t; inspect it before restarting SSH." >&2
      fi
      if [[ "$restart_attempted" -eq 1 ]] && ! systemctl restart ssh; then
        echo "SSH could not be restarted after restoring the previous configuration." >&2
      fi
    fi

    [[ -z "$stage_file" ]] || rm -f -- "$stage_file"
    if [[ -n "$backup_file" && "$preserve_backup" -eq 0 ]]; then
      rm -f -- "$backup_file"
    fi
    exit "$status"
  }
  trap cleanup_transaction EXIT

  stage_file="$(mktemp "$CONF_DIR/.${filename}.new.XXXXXX")"
  printf '%s\n' \
    '# Managed by setup_eye_host_ssh_x11.sh for EyeTrack SSH/X11 forwarding.' \
    'X11Forwarding yes' \
    'X11UseLocalhost yes' >"$stage_file"
  if [[ "$TEST_MODE" -eq 0 ]]; then
    chown root:root "$stage_file"
  fi
  chmod 0644 "$stage_file"

  if [[ -f "$CONF_FILE" ]]; then
    had_previous=1
    backup_file="$(mktemp "$CONF_DIR/.${filename}.backup.XXXXXX")"
    cp --preserve=mode,ownership,timestamps -- "$CONF_FILE" "$backup_file"
  fi

  mv -fT -- "$stage_file" "$CONF_FILE"
  stage_file=""
  transaction_active=1

  if ! sshd -t; then
    echo "The staged SSH configuration failed sshd -t." >&2
    exit 1
  fi

  if ! effective_config="$(sshd -T)"; then
    echo "Unable to read the effective SSH daemon configuration with sshd -T." >&2
    exit 1
  fi
  if ! grep -Eiq '^x11forwarding[[:space:]]+yes$' <<<"$effective_config"; then
    echo "Effective SSH configuration does not enable X11Forwarding." >&2
    exit 1
  fi
  if ! grep -Eiq '^x11uselocalhost[[:space:]]+yes$' <<<"$effective_config"; then
    echo "Effective SSH configuration does not enable X11UseLocalhost." >&2
    exit 1
  fi

  systemctl enable ssh >/dev/null
  restart_attempted=1
  systemctl restart ssh
  transaction_active=0

  [[ -z "$backup_file" ]] || rm -f -- "$backup_file"
  backup_file=""
  trap - EXIT
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
      ssh_x11_require_option_value "$1" "$#"
      BEHAVIOR_IP="$2"
      shift 2
      ;;
    --conf-file)
      ssh_x11_require_option_value "$1" "$#"
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
    --dry-run)
      DRY_RUN=1
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

validate_conf_target

if [[ "$DRY_RUN" -eq 1 ]]; then
  require_cmd grep
  verify_active_include
  print_dry_run
  exit 0
fi

if [[ "${EUID}" -ne 0 && "$TEST_MODE" -eq 0 ]]; then
  exec sudo "$0" "${ORIGINAL_ARGS[@]}"
fi

require_cmd systemctl
require_cmd mktemp
require_cmd cp
require_cmd mv

maybe_install_missing
require_cmd sshd
verify_active_include

# Reject pre-existing daemon errors before attributing a failure to this drop-in.
sshd -t
validate_conf_target
verify_active_include

configure_sshd_dropin
configure_ufw

echo "SSH/X11 forwarding setup complete."
echo "SSH drop-in: $CONF_FILE"
echo "Behavior computer allowed IP: $BEHAVIOR_IP"
echo "Next step from the behavior computer:"
echo "  ./open_alignment_preview_over_ssh.sh --host USER@<eye-tracking-ip>"
