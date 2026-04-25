#!/usr/bin/env bash
#
# setup_two_computer_eye_link.sh
#
# Configure the direct Ethernet link used when eye tracking runs on one Ubuntu
# computer and BehaviorBox/MATLAB runs on another.
#
# Why this exists:
# - The eye-tracking computer does the expensive work: FLIR camera acquisition,
#   DLCLive inference, optional preview display, and ZMQ publishing.
# - The behavior computer should stay light: a separate receiver service
#   subscribes to small ZMQ JSON messages, stamps receive time, writes chunk
#   files, and MATLAB imports finalized chunks through the local receiver API.
# - A direct Ethernet cable gives a stable private link between the two machines
#   without using lab Wi-Fi or the campus network.
#
# Network convention used by BehaviorBox:
# - eye-tracking / sending computer: 10.55.0.1/24
# - behavior / receiving computer:  10.55.0.2/24
# - ZMQ stream address:             tcp://10.55.0.1:5555
#
# Safety behavior:
# - By default this script is DRY RUN only. It prints the commands it would run.
# - Add --apply to actually create or modify the NetworkManager connection.
# - The direct-cable connection is marked ipv4.never-default=yes so it should not
#   steal the computer's normal internet route from Wi-Fi or another adapter.
#
# Typical use on the EYE-TRACKING computer:
#
#   ./setup_two_computer_eye_link.sh --role sender --iface enp172s0 --apply
#
# Typical use on the BEHAVIOR computer:
#
#   ./setup_two_computer_eye_link.sh --role receiver --iface <ethernet-interface> --apply
#
# If you do not know the Ethernet interface name, run:
#
#   nmcli device status
#
# Or let this script try to choose the only Ethernet adapter:
#
#   ./setup_two_computer_eye_link.sh --role sender --apply
#
# After sender setup, start the eye stream on the eye-tracking computer:
#
#   cd /home/wbs/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
#   conda activate dlclivegui
#   ./run_eye_stream_production.py --address tcp://10.55.0.1:5555 --frame-rate 60 --exposure-us 6000 --gain-auto continuous --display-fps 20
#
# After receiver setup, source the generated helper on the behavior computer.
# It sets BB_EYETRACK_ZMQ_ADDRESS, BB_EYETRACK_RECEIVER_URL, and a convenience
# BB_EYETRACK_RECEIVER_PYTHON path used to launch the receiver service.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CON_NAME="bb-eye-direct"
SENDER_IP="10.55.0.1"
RECEIVER_IP="10.55.0.2"
PREFIX_LEN="24"
PORT="5555"
RECEIVER_API_HOST="127.0.0.1"
RECEIVER_API_PORT="8765"
ROLE=""
IFACE=""
APPLY=0
OPEN_FIREWALL=1
RECEIVER_PYTHON=""

usage() {
    cat <<'USAGE'
Configure a direct Ethernet link for two-computer BehaviorBox eye tracking.

Usage:
  ./setup_two_computer_eye_link.sh --role sender [--iface IFACE] [--apply]
  ./setup_two_computer_eye_link.sh --role receiver [--iface IFACE] [--apply] [--receiver-python PATH]

Roles:
  sender    Eye-tracking computer. Runs FLIR + DLCLive + ZMQ publisher.
            Static IP: 10.55.0.1/24

  receiver  Behavior computer. Runs receiver service + MATLAB + BehaviorBox importer.
            Static IP: 10.55.0.2/24

Options:
  --role ROLE              Required. sender/eye/publisher or receiver/behavior/matlab.
  --iface IFACE            Ethernet interface to configure. If omitted, the script
                           auto-selects the only Ethernet interface reported by nmcli.
  --apply                  Actually run sudo nmcli commands. Without this, dry run only.
  --connection NAME        NetworkManager connection name. Default: bb-eye-direct.
  --sender-ip IP           Sender static IP. Default: 10.55.0.1.
  --receiver-ip IP         Receiver static IP. Default: 10.55.0.2.
  --prefix N               CIDR prefix length. Default: 24.
  --port PORT              ZMQ TCP port. Default: 5555.
  --receiver-python PATH   Python executable used to start the receiver service
                           on the behavior computer. Default tries common conda
                           env paths.
  --no-firewall            Do not add a sender-side ufw allow rule.
  -h, --help               Show this help.

Examples:
  # On this computer when it is the eye-tracking/sending computer:
  ./setup_two_computer_eye_link.sh --role sender --iface enp172s0 --apply

  # On the behavior/receiving computer:
  ./setup_two_computer_eye_link.sh --role receiver --iface eno1 --apply

  # Dry run first, showing exactly what would change:
  ./setup_two_computer_eye_link.sh --role sender --iface enp172s0

What gets configured:
  - A NetworkManager Ethernet profile named bb-eye-direct.
  - Manual IPv4 address:
      sender   -> 10.55.0.1/24
      receiver -> 10.55.0.2/24
  - IPv6 disabled on the direct link.
  - No default route from this link, so normal internet stays on Wi-Fi/other NIC.
  - On sender only, if ufw is active, a rule allowing receiver -> TCP 5555.

BehaviorBox connection address:
  tcp://10.55.0.1:5555

Do not use tcp://127.0.0.1:5555 for two-computer operation. 127.0.0.1 means
"this same computer"; the behavior computer would try to connect to itself.
USAGE
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

warn() {
    echo "WARNING: $*" >&2
}

info() {
    echo "$*"
}

quote_cmd() {
    local out=""
    local arg
    for arg in "$@"; do
        printf -v out '%s%q ' "$out" "$arg"
    done
    printf '%s\n' "${out% }"
}

run_cmd() {
    if [[ "$APPLY" -eq 1 ]]; then
        info "+ $(quote_cmd "$@")"
        "$@"
    else
        info "[dry-run] $(quote_cmd "$@")"
    fi
}

have_cmd() {
    command -v "$1" >/dev/null 2>&1
}

normalize_role() {
    local role_normalized
    role_normalized="$(printf '%s' "$ROLE" | tr '[:upper:]' '[:lower:]')"
    case "$role_normalized" in
        sender|send|eye|eyetrack|eye-track|publisher|pub)
            ROLE="sender"
            ;;
        receiver|receive|behavior|behaviour|matlab|subscriber|sub)
            ROLE="receiver"
            ;;
        *)
            die "Unknown --role '$ROLE'. Use sender or receiver."
            ;;
    esac
}

autodetect_iface() {
    have_cmd nmcli || die "nmcli is required. Install/use NetworkManager or pass --help for manual commands."

    mapfile -t ethernet_ifaces < <(nmcli -t -f DEVICE,TYPE device status | awk -F: '$2 == "ethernet" {print $1}')
    if [[ "${#ethernet_ifaces[@]}" -eq 0 ]]; then
        die "No Ethernet interface found by nmcli. Plug in an Ethernet adapter/cable and run: nmcli device status"
    fi
    if [[ "${#ethernet_ifaces[@]}" -gt 1 ]]; then
        printf 'Ethernet interfaces found:\n' >&2
        printf '  %s\n' "${ethernet_ifaces[@]}" >&2
        die "More than one Ethernet interface found. Rerun with --iface IFACE."
    fi
    IFACE="${ethernet_ifaces[0]}"
}

connection_exists() {
    nmcli -t -f NAME con show | grep -Fxq "$CON_NAME"
}

default_receiver_python() {
    local candidates=(
        "$HOME/miniforge3/envs/bbeyezmq/bin/python"
        "$HOME/mambaforge/envs/bbeyezmq/bin/python"
        "$HOME/miniconda3/envs/bbeyezmq/bin/python"
        "$HOME/anaconda3/envs/bbeyezmq/bin/python"
        "$HOME/miniforge3/envs/dlclivegui/bin/python"
        "$HOME/mambaforge/envs/dlclivegui/bin/python"
        "$HOME/miniconda3/envs/dlclivegui/bin/python"
        "$HOME/anaconda3/envs/dlclivegui/bin/python"
    )
    local candidate
    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return
        fi
    done
    printf '%s\n' "$HOME/miniforge3/envs/bbeyezmq/bin/python"
}

write_receiver_env_file() {
    local env_file="$SCRIPT_DIR/behavior_eye_tracking_env.sh"
    local address="tcp://${SENDER_IP}:${PORT}"
    local receiver_url="http://${RECEIVER_API_HOST}:${RECEIVER_API_PORT}"
    if [[ -z "$RECEIVER_PYTHON" ]]; then
        RECEIVER_PYTHON="$(default_receiver_python)"
    fi

    if [[ "$APPLY" -eq 1 ]]; then
        cat > "$env_file" <<EOF
#!/usr/bin/env bash
# Source this file on the behavior computer before starting the receiver
# service or MATLAB.
#
# Usage:
#   source "$env_file"
#   "\$BB_EYETRACK_RECEIVER_PYTHON" "$SCRIPT_DIR/run_eye_receiver_service.py"
#   cd /home/wbs/Desktop/BehaviorBox
#   matlab

export BB_EYETRACK_ZMQ_ADDRESS="$address"
export BB_EYETRACK_RECEIVER_URL="$receiver_url"
export BB_EYETRACK_RECEIVER_PYTHON="$RECEIVER_PYTHON"
EOF
        chmod +x "$env_file"
        info "Wrote receiver environment helper: $env_file"
    else
        info "[dry-run] would write receiver environment helper: $env_file"
        info "[dry-run] BB_EYETRACK_ZMQ_ADDRESS=$address"
        info "[dry-run] BB_EYETRACK_RECEIVER_URL=$receiver_url"
        info "[dry-run] BB_EYETRACK_RECEIVER_PYTHON=$RECEIVER_PYTHON"
    fi
}

maybe_open_firewall() {
    [[ "$ROLE" == "sender" ]] || return 0
    [[ "$OPEN_FIREWALL" -eq 1 ]] || return 0
    have_cmd ufw || return 0

    local status
    status="$(ufw status 2>/dev/null | head -n 1 || true)"
    if [[ "$status" == *"active"* ]]; then
        run_cmd sudo ufw allow from "$RECEIVER_IP" to any port "$PORT" proto tcp
    else
        info "ufw is not active; no firewall rule needed."
    fi
}

configure_nmcli() {
    local my_ip peer_ip role_label
    if [[ "$ROLE" == "sender" ]]; then
        my_ip="$SENDER_IP"
        peer_ip="$RECEIVER_IP"
        role_label="eye-tracking sender"
    else
        my_ip="$RECEIVER_IP"
        peer_ip="$SENDER_IP"
        role_label="behavior receiver"
    fi

    info "Role: $role_label"
    info "Interface: $IFACE"
    info "Connection: $CON_NAME"
    info "This computer IP: ${my_ip}/${PREFIX_LEN}"
    info "Peer computer IP: ${peer_ip}/${PREFIX_LEN}"
    info "ZMQ address used by receiver path: tcp://${SENDER_IP}:${PORT}"
    info "Receiver API URL used by BehaviorBox: http://${RECEIVER_API_HOST}:${RECEIVER_API_PORT}"
    info ""

    if connection_exists; then
        info "NetworkManager connection '$CON_NAME' already exists; it will be updated."
        run_cmd sudo nmcli con mod "$CON_NAME" \
            connection.interface-name "$IFACE" \
            connection.autoconnect yes \
            ipv4.method manual \
            ipv4.addresses "${my_ip}/${PREFIX_LEN}" \
            ipv4.never-default yes \
            ipv4.ignore-auto-dns yes \
            ipv6.method disabled
    else
        info "NetworkManager connection '$CON_NAME' does not exist; it will be created."
        run_cmd sudo nmcli con add type ethernet ifname "$IFACE" con-name "$CON_NAME" \
            connection.autoconnect yes \
            ipv4.method manual \
            ipv4.addresses "${my_ip}/${PREFIX_LEN}" \
            ipv4.never-default yes \
            ipv4.ignore-auto-dns yes \
            ipv6.method disabled
    fi

    maybe_open_firewall

    if [[ "$APPLY" -eq 1 ]]; then
        info ""
        info "Bringing up '$CON_NAME'. If this fails, plug in the Ethernet cable and run:"
        info "  sudo nmcli con up $CON_NAME"
        if ! sudo nmcli con up "$CON_NAME"; then
            warn "Could not bring up '$CON_NAME'. The profile was configured, but the cable/interface may be down."
        fi
    else
        info "[dry-run] sudo nmcli con up $CON_NAME"
    fi

    if [[ "$ROLE" == "receiver" ]]; then
        write_receiver_env_file
    fi

    info ""
    info "Verification commands:"
    info "  ip -br addr show $IFACE"
    info "  ping -c 3 $peer_ip"
    if [[ "$ROLE" == "sender" ]]; then
        info "  ss -ltnp | grep $PORT    # after starting run_eye_stream_production.py"
    else
        info "  source ./behavior_eye_tracking_env.sh"
        info "  \"\$BB_EYETRACK_RECEIVER_PYTHON\" ./run_eye_receiver_service.py --address \"\$BB_EYETRACK_ZMQ_ADDRESS\" --api-port ${RECEIVER_API_PORT}"
        info "  ./run_matlab_eye_receive_test.py --address \"\$BB_EYETRACK_ZMQ_ADDRESS\" --receiver-url \"\$BB_EYETRACK_RECEIVER_URL\" --duration 10"
    fi
}

print_next_steps() {
    local address="tcp://${SENDER_IP}:${PORT}"
    info ""
    info "Next steps:"
    if [[ "$ROLE" == "sender" ]]; then
        cat <<EOF
1. Confirm the FLIR camera is visible:

   cd "$SCRIPT_DIR"
   conda activate dlclivegui
   python check_pyspin_camera.py

2. Start the eye stream on this sender computer:

   ./run_eye_stream_production.py \\
     --address $address \\
     --frame-rate 60 \\
     --exposure-us 6000 \\
     --gain-auto continuous \\
     --display-fps 20

3. On the behavior receiver computer, source the helper and start the
   receiver service:

   source "$SCRIPT_DIR/behavior_eye_tracking_env.sh"
   "\$BB_EYETRACK_RECEIVER_PYTHON" "$SCRIPT_DIR/run_eye_receiver_service.py" \\
     --address "\$BB_EYETRACK_ZMQ_ADDRESS" \\
     --api-port ${RECEIVER_API_PORT}

EOF
    else
        cat <<EOF
1. Source the generated environment helper:

   source "$SCRIPT_DIR/behavior_eye_tracking_env.sh"

2. Start the deferred receiver while the sender streamer is running:

   "\$BB_EYETRACK_RECEIVER_PYTHON" "$SCRIPT_DIR/run_eye_receiver_service.py" \\
     --address "\$BB_EYETRACK_ZMQ_ADDRESS" \\
     --api-port ${RECEIVER_API_PORT}

3. Test MATLAB receive:

   cd "$SCRIPT_DIR"
   ./run_matlab_eye_receive_test.py \\
     --address "\$BB_EYETRACK_ZMQ_ADDRESS" \\
     --receiver-url "\$BB_EYETRACK_RECEIVER_URL" \\
     --duration 10

4. Start MATLAB from the same terminal:

   cd /home/wbs/Desktop/BehaviorBox
   matlab

EOF
    fi
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --role)
            [[ "$#" -ge 2 ]] || die "--role requires a value"
            ROLE="$2"
            shift 2
            ;;
        --iface)
            [[ "$#" -ge 2 ]] || die "--iface requires a value"
            IFACE="$2"
            shift 2
            ;;
        --apply)
            APPLY=1
            shift
            ;;
        --connection)
            [[ "$#" -ge 2 ]] || die "--connection requires a value"
            CON_NAME="$2"
            shift 2
            ;;
        --sender-ip)
            [[ "$#" -ge 2 ]] || die "--sender-ip requires a value"
            SENDER_IP="$2"
            shift 2
            ;;
        --receiver-ip)
            [[ "$#" -ge 2 ]] || die "--receiver-ip requires a value"
            RECEIVER_IP="$2"
            shift 2
            ;;
        --prefix)
            [[ "$#" -ge 2 ]] || die "--prefix requires a value"
            PREFIX_LEN="$2"
            shift 2
            ;;
        --port)
            [[ "$#" -ge 2 ]] || die "--port requires a value"
            PORT="$2"
            shift 2
            ;;
        --receiver-python)
            [[ "$#" -ge 2 ]] || die "--receiver-python requires a value"
            RECEIVER_PYTHON="$2"
            shift 2
            ;;
        --no-firewall)
            OPEN_FIREWALL=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown argument: $1"
            ;;
    esac
done

[[ -n "$ROLE" ]] || { usage; die "--role sender or --role receiver is required"; }
normalize_role

have_cmd nmcli || die "nmcli is required for this setup script."

if [[ -z "$IFACE" ]]; then
    autodetect_iface
fi

info "BehaviorBox two-computer eye-tracking Ethernet setup"
info "Script directory: $SCRIPT_DIR"
if [[ "$APPLY" -eq 1 ]]; then
    info "Mode: APPLY changes"
else
    info "Mode: DRY RUN only. Add --apply to change NetworkManager settings."
fi
info ""

configure_nmcli
print_next_steps
