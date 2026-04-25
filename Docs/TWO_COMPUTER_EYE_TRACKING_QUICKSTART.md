# Two-Computer Eye Tracking Quick Start

This guide sets up eye tracking on one Ubuntu computer and BehaviorBox on a second Ubuntu computer connected by one direct Ethernet cable.

If you want to remove the dedicated display, mouse, and keyboard from the eye-tracking computer and use SSH/X11 forwarding instead, see [SSH_X11_FORWARDING_POPOS.md](./SSH_X11_FORWARDING_POPOS.md).

## Goal

Use this layout:

| Role | Static IP | Runs |
| --- | --- | --- |
| Eye-tracking computer | `10.55.0.1` | FLIR camera, PySpin, DLCLive, `dlc_eye_streamer.py`, preview window |
| Behavior computer | `10.55.0.2` | `behavior_eye_receiver.py`, MATLAB, BehaviorBox, `BehaviorBoxEyeTrack` importer |

The eye-tracking computer publishes ZMQ messages at:

```text
tcp://10.55.0.1:5555
```

The behavior computer receiver connects to that same address.

Do not use `127.0.0.1` for a two-computer setup. `127.0.0.1` means "this same computer", so the behavior-computer receiver would try to connect to itself instead of the eye-tracking computer.

Any `/home/<user>/...` paths below are examples. Replace `<user>` with the
account on that Linux computer, and replace the `BehaviorBox` and conda paths if
your install location differs.

## 1. Physical Setup

1. Connect the FLIR camera to the eye-tracking computer.
2. Connect the eye-tracking computer and behavior computer with one Ethernet cable.
3. Keep normal internet on Wi-Fi or a second Ethernet adapter if needed.
4. Do not put the direct-cable connection on DHCP. Set the static IPs below.

Modern Ethernet ports usually handle direct computer-to-computer cables without a crossover cable.

## 2. Configure Static Ethernet IPs

### Recommended: Use the Setup Script

The `Stream-DeepLabCut` folder contains a role-based setup script:

```bash
cd /home/<user>/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
./setup_two_computer_eye_link.sh --help
```

On the eye-tracking computer:

```bash
./setup_two_computer_eye_link.sh --role sender --iface enp172s0 --apply
```

On the behavior computer:

```bash
./setup_two_computer_eye_link.sh --role receiver --iface <IFACE> --apply
```

The script defaults to dry-run mode if `--apply` is omitted, so you can safely
preview what it will do:

```bash
./setup_two_computer_eye_link.sh --role sender --iface enp172s0
```

It configures the `bb-eye-direct` NetworkManager profile, keeps the direct cable
from becoming the default internet route, and prints the commands needed to test
and launch the eye stream.

### Manual Static IP Setup

Run these commands on each computer. Replace `<IFACE>` with the wired interface used by the direct cable.

Find the interface name:

```bash
nmcli device status
```

Common names look like `enp3s0`, `eno1`, or `eth0`.

### Eye-Tracking Computer

```bash
sudo nmcli con add type ethernet ifname <IFACE> con-name bb-eye-direct \
  ipv4.method manual \
  ipv4.addresses 10.55.0.1/24 \
  ipv4.never-default yes \
  ipv6.method disabled \
  autoconnect yes

sudo nmcli con up bb-eye-direct
```

### Behavior Computer

```bash
sudo nmcli con add type ethernet ifname <IFACE> con-name bb-eye-direct \
  ipv4.method manual \
  ipv4.addresses 10.55.0.2/24 \
  ipv4.never-default yes \
  ipv6.method disabled \
  autoconnect yes

sudo nmcli con up bb-eye-direct
```

If a `bb-eye-direct` connection already exists and `nmcli con add` fails, modify the existing profile instead:

Eye-tracking computer:

```bash
sudo nmcli con mod bb-eye-direct \
  ipv4.method manual \
  ipv4.addresses 10.55.0.1/24 \
  ipv4.never-default yes \
  ipv6.method disabled

sudo nmcli con up bb-eye-direct
```

Behavior computer:

```bash
sudo nmcli con mod bb-eye-direct \
  ipv4.method manual \
  ipv4.addresses 10.55.0.2/24 \
  ipv4.never-default yes \
  ipv6.method disabled

sudo nmcli con up bb-eye-direct
```

### Verify the Link

From the behavior computer:

```bash
ping -c 3 10.55.0.1
```

From the eye-tracking computer:

```bash
ping -c 3 10.55.0.2
```

If `ufw` is enabled on the eye-tracking computer, allow the behavior computer to connect to the ZMQ port:

```bash
sudo ufw allow from 10.55.0.2 to any port 5555 proto tcp
sudo ufw status
```

## 3. Install the Eye-Tracking Python Environment

Do this on the eye-tracking computer.

This assumes the computer already has:

- Ubuntu
- NVIDIA driver if using GPU inference
- SpinView
- PySpin or the Spinnaker Python wheel
- The DLC model folder

### Install Miniforge If Needed

Skip this if `conda` or `mamba` already exists.

```bash
cd /tmp
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh
source "$HOME/miniforge3/etc/profile.d/conda.sh"
```

### Copy the EyeTrack Code and Model

The eye-tracking computer needs this repo root, including `Stream-DeepLabCut/`,
`Cam-Tests/`, `ssh_x11/`, and `environment.yaml`:

```text
BehaviorBox/EyeTrack/
```

It also needs the model folder, usually:

```text
BehaviorBox/EyeTrack/Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1
```

One way to copy from the behavior computer to the eye-tracking computer is:

```bash
rsync -av /home/<user>/Desktop/BehaviorBox/EyeTrack/ \
  <user>@10.55.0.1:/home/<user>/Desktop/BehaviorBox/EyeTrack/
```

Run that from the behavior computer, adjusting usernames and paths as needed.

### Create the `dlclivegui` Environment

On the eye-tracking computer:

```bash
cd /home/<user>/Desktop/BehaviorBox/EyeTrack
conda env create -n dlclivegui -f environment.yaml
conda activate dlclivegui
```

If the environment already exists:

```bash
conda activate dlclivegui
conda env update -n dlclivegui -f environment.yaml --prune
```

The explicit `-n dlclivegui` is intentional. It avoids reusing the `prefix` path that may be present in an exported environment file from another computer.

### Make Sure PySpin Is Visible Inside the Environment

Test:

```bash
conda activate dlclivegui
python - <<'PY'
import PySpin
system = PySpin.System.GetInstance()
print("PySpin import OK")
print("Detected cameras:", system.GetCameras().GetSize())
system.ReleaseInstance()
PY
```

If `import PySpin` fails, install the Spinnaker Python wheel into this conda environment.

First search for the wheel:

```bash
find /opt /usr/local "$HOME" -iname "*spinnaker*python*.whl" 2>/dev/null
```

Then install the wheel that matches this environment's Python version:

```bash
conda activate dlclivegui
python --version
python -m pip install /path/to/spinnaker_python-*.whl
```

The current environment uses Python 3.10, so the PySpin wheel must be compatible with Python 3.10. If the installed Spinnaker SDK only provides a different wheel, install the SDK version that provides a Python 3.10 wheel, or recreate the conda environment with the Python version that matches your wheel.

### Check Camera Visibility

From this folder on the eye-tracking computer:

```bash
cd /home/<user>/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate dlclivegui
python3 check_pyspin_camera.py
```

Expected output should include at least one detected camera, for example:

```text
Detected cameras: 1
0: Point Grey Research Chameleon3 CM3-U3-13Y3M serial=...
```

Optional full-frame setup preview:

```bash
python3 ../Cam-Tests/FLIRCam.py --auto-contrast --scale 0.5
```

## 4. Install the Receiver Environment on the Behavior Computer

The behavior computer no longer uses MATLAB as the live ZMQ subscriber. Instead, it runs a separate Python receiver service that:

- subscribes to the streamer ZMQ address
- stamps samples with behavior-computer receive time
- writes per-segment chunk CSV + metadata JSON files
- exposes a localhost HTTP API that `BehaviorBoxEyeTrack` uses

Create a small receiver environment with `pyzmq`:

```bash
conda create -n bbeyezmq -c conda-forge python=3.10 pyzmq -y
conda activate bbeyezmq
python -c "import zmq; print(zmq.__version__)"
```

Using the name `bbeyezmq` is fine and matches the existing lab convention, but the name itself is not required. The important requirement is that the environment can run `run_eye_receiver_service.py` and import `zmq`.

The receiver Python executable will usually be:

```text
/home/<user>/miniforge3/envs/bbeyezmq/bin/python
```

or, if you choose to reuse the full environment:

```text
/home/<user>/miniforge3/envs/dlclivegui/bin/python
```

## 5. Start the Eye Stream on the Eye-Tracking Computer

Run this on the eye-tracking computer:

```bash
cd /home/<user>/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate dlclivegui

./run_eye_stream_production.py \
  --address tcp://10.55.0.1:5555 \
  --model-path /home/<user>/Desktop/BehaviorBox/EyeTrack/Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --model-preset yanglab-pupil8 \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto continuous \
  --display \
  --display-scale 0.75 \
  --display-fps 20
```

Important:

- `--address tcp://10.55.0.1:5555` means the streamer binds to the eye-tracking computer's direct-cable IP.
- The preview window opens on the eye-tracking computer, not the behavior computer.
- CSV and metadata sidecar files are written on the eye-tracking computer under `/tmp/EyeTrack`.
- Use `--no-display` if the preview is not needed.
- Use a lower `--display-fps`, such as `--display-fps 5`, if the preview itself becomes distracting.

Confirm the TCP port is listening:

```bash
ss -ltnp | grep 5555
```

## 6. Start the Deferred Receiver on the Behavior Computer

Run this on the behavior computer from `Stream-DeepLabCut/`:

```bash
cd /path/to/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate bbeyezmq

./run_eye_receiver_service.py \
  --address tcp://10.55.0.1:5555 \
  --api-port 8765
```

Important:

- `--address tcp://10.55.0.1:5555` must point to the eye-tracking computer, not `127.0.0.1`.
- The receiver HTTP API defaults to `http://127.0.0.1:8765` on the behavior computer.
- The receiver writes per-session raw eye chunks under the session output directory that BehaviorBox provides when it opens a session.

Leave this process running while you use BehaviorBox.

## 7. Test MATLAB Receive Before Running Behavior

Start the eye streamer first, then start the receiver, then run this on the behavior computer:

```bash
cd /path/to/BehaviorBox/EyeTrack/Stream-DeepLabCut

./run_matlab_eye_receive_test.py \
  --address tcp://10.55.0.1:5555 \
  --receiver-url http://127.0.0.1:8765 \
  --duration 10
```

Expected successful ending:

```text
MATLAB_EYE_STREAM_RECEIVE_OK
```

You should also see:

- nonzero sample count
- `Ready: 1` once a valid or partial-points sample arrives
- `CSV path advertised by streamer`
- `Metadata path advertised by streamer`

If there is no mouse eye in view, samples may have `sample_status=no_points`. That is still useful for testing transport, but readiness requires a valid JSON sample with expected point names and status `ok` or `partial_points`.

## 8. Run BehaviorBox

If the receiver is using the default local API URL `http://127.0.0.1:8765`, MATLAB does not need extra environment variables. If you changed the receiver API URL, set `BB_EYETRACK_RECEIVER_URL` before starting MATLAB.

Default case:

```bash
cd /path/to/BehaviorBox
matlab
```

Non-default receiver URL:

```bash
export BB_EYETRACK_RECEIVER_URL=http://127.0.0.1:9000
cd /path/to/BehaviorBox
matlab
```

Recommended startup order:

1. Start the eye streamer on the eye-tracking computer.
2. Start the deferred receiver on the behavior computer.
3. Confirm MATLAB can import samples with `run_matlab_eye_receive_test.py`.
4. Start MATLAB on the behavior computer.
5. Start BehaviorBox.
6. Run behavior training or mapping animations.

BehaviorBox now talks to the local receiver service, not directly to the remote ZMQ stream. If it cannot connect to the receiver, it should issue a visible MATLAB warning and continue the session without blocking.

Saved behavior files should include, when data is available:

- `EyeTrackRecord`
- `EyeTrackSegmentMeta`
- `EyeTrackingRecord`
- `EyeTrackingMeta`
- `FrameAlignedRecord`
- `EyeAlignedRecord`

## 9. Shutdown Order

Recommended order:

1. Stop the BehaviorBox session and let it save.
2. Wait for the MATLAB save to complete.
3. Stop the deferred receiver on the behavior computer with `Ctrl+C`.
4. Stop the Python eye streamer on the eye-tracking computer with `Ctrl+C`.

BehaviorBox finalizes/imports eye chunks during save, but it does not stop either external Python process for you.

## 10. Troubleshooting

### Behavior Computer Cannot Ping Eye-Tracking Computer

Check both interfaces:

```bash
ip addr show
nmcli device status
nmcli con show --active
```

Confirm:

- eye-tracking computer has `10.55.0.1/24`
- behavior computer has `10.55.0.2/24`
- both are on the Ethernet interface connected by the direct cable
- no gateway is assigned to the direct-cable profile

### MATLAB Cannot Connect to the Receiver

On the behavior computer, confirm the receiver process is still running:

```bash
ps -ef | grep run_eye_receiver_service.py
ss -ltnp | grep 8765
```

If you are using a non-default receiver URL, confirm:

```bash
echo "$BB_EYETRACK_RECEIVER_URL"
```

The default is:

```text
http://127.0.0.1:8765
```

If the receiver is up but MATLAB still cannot connect, test the health endpoint directly:

```bash
curl http://127.0.0.1:8765/health
```

### PySpin Works in SpinView But Not in Python

SpinView can work even if the conda environment cannot import PySpin. Test inside the environment:

```bash
conda activate dlclivegui
python -c "import PySpin; print('PySpin OK')"
```

If it fails, install the Spinnaker Python wheel into the conda environment.

### Camera Is Not Detected

Run:

```bash
python3 check_pyspin_camera.py
```

If no camera is detected:

- confirm SpinView sees the camera
- confirm the camera is not already open in SpinView
- unplug and replug the camera
- reboot after installing Spinnaker
- confirm USB permissions and Spinnaker udev rules were installed

### Eye Stream Is Running But the Receiver Gets Zero Samples

Common causes:

- streamer was started with `--address tcp://127.0.0.1:5555`
- receiver was pointed at `tcp://127.0.0.1:5555` instead of `tcp://10.55.0.1:5555`
- firewall blocks port `5555`
- direct-cable IPs are on different subnets
- the behavior-computer receiver environment cannot import `zmq`

Fix by using:

Eye-tracking computer:

```bash
./run_eye_stream_production.py --address tcp://10.55.0.1:5555
```

Behavior computer:

```bash
./run_eye_receiver_service.py --address tcp://10.55.0.1:5555 --api-port 8765
```

Then confirm the receiver is healthy:

```bash
curl http://127.0.0.1:8765/status
```

### Behavior Display Still Lags

Move all DLC inference and preview display to the eye-tracking computer. On the behavior computer, MATLAB only talks to the receiver API and imports finalized chunks outside the hot loops.

On the eye-tracking computer, lower preview load if needed:

```bash
./run_eye_stream_production.py \
  --address tcp://10.55.0.1:5555 \
  --display-fps 5
```

or disable preview:

```bash
./run_eye_stream_production.py \
  --address tcp://10.55.0.1:5555 \
  --no-display
```

### GPU Check on the Eye-Tracking Computer

Run:

```bash
nvidia-smi
```

Start the streamer and watch memory use:

```bash
watch -n 1 nvidia-smi
```

TensorFlow should create a GPU device in the streamer output if it sees the NVIDIA GPU.

## 11. Minimal Command Summary

Eye-tracking computer:

```bash
cd /home/<user>/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate dlclivegui
python3 check_pyspin_camera.py
./run_eye_stream_production.py --address tcp://10.55.0.1:5555 --frame-rate 60 --exposure-us 6000 --gain-auto continuous --display-fps 20
```

Behavior computer:

```bash
cd /path/to/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate bbeyezmq
./run_eye_receiver_service.py --address tcp://10.55.0.1:5555 --api-port 8765
./run_matlab_eye_receive_test.py --address tcp://10.55.0.1:5555 --receiver-url http://127.0.0.1:8765 --duration 10
```

Then start MATLAB from the same terminal:

```bash
cd /path/to/BehaviorBox
matlab
```
