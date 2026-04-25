# EyeTrack

Standalone eye-tracking repo extracted from `BehaviorBox`.

## Current Layout

```text
Stream-DeepLabCut/
  Live FLIR capture, DLCLive inference, ZeroMQ publishing, deferred receiver,
  and MATLAB-side receive helpers.

Cam-Tests/
  Bounded camera, environment, preview, training-frame capture, and inference
  smoke checks.

Train-Test-Model/
  Model training/export helper and still-image model sanity test.

ssh_x11/
  SSH/X11 wrappers for remote preview, training-frame capture, production
  stream startup, status checks, and shutdown.

Docs/
  Single-computer setup, two-computer setup, SSH/X11 workflow, stream contract,
  and training-frame capture instructions.

Models/
  Local runtime model landing zone. Model blobs are intentionally ignored by git.
```

The former runtime, camera-test, training, and still-image test areas have been
flattened into the folders above.

## Quick Starts

Start the production eye stream:

```bash
cd Stream-DeepLabCut
./run_eye_stream_production.py \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto off \
  --display-fps 20
```

Start the deferred receiver on the behavior computer:

```bash
cd Stream-DeepLabCut
./run_eye_receiver_service.py \
  --address tcp://127.0.0.1:5555 \
  --api-port 8765
```

Open a forwarded training-frame capture preview:

```bash
cd ssh_x11
./open_training_capture_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --camera-index 0 \
  --auto-contrast \
  --scale 0.5
```

Run a basic FLIR/PySpin smoke check:

```bash
python3 Cam-Tests/TestSpin.py --camera-index 0 --sensor-roi 0 0 640 480 --frames 120
```

Run FLIR + DLCLive timing:

```bash
python3 Cam-Tests/smoke_dlc_flir_inference.py \
  --model-path Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --model-preset yanglab-pupil8 \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frames 120
```

## Main Docs

- Single-computer deployment: [Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md](Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md)
- Two-computer deployment: [Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md](Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md)
- SSH/X11 workflow: [Docs/SSH_X11_FORWARDING_POPOS.md](Docs/SSH_X11_FORWARDING_POPOS.md)
- FLIR training-frame capture over SSH/X11: [Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md](Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md)
- Streamer, receiver, and MATLAB receive details: [Docs/README_eye_stream.md](Docs/README_eye_stream.md)
- Runtime scripts: [Stream-DeepLabCut/README.md](Stream-DeepLabCut/README.md)
- Camera/environment checks: [Cam-Tests/README.md](Cam-Tests/README.md)
- Model training/export: [Train-Test-Model/train-README.md](Train-Test-Model/train-README.md)
- Still-image model sanity test: [Train-Test-Model/test-README.md](Train-Test-Model/test-README.md)

## Runtime Boundary

The active interop boundary is:

- Eye-tracking computer producer:
  `Stream-DeepLabCut/dlc_eye_streamer.py`
- Behavior computer receiver:
  `Stream-DeepLabCut/behavior_eye_receiver.py`
- MATLAB/BehaviorBox consumer:
  `BehaviorBoxEyeTrack.m` in the BehaviorBox project

Transport:

- ZeroMQ JSON stream from streamer to receiver, default endpoint `tcp://127.0.0.1:5555`
- append-only chunk CSV + metadata JSON written by the receiver
- localhost HTTP control/status API, default receiver URL `http://127.0.0.1:8765`

The normal BehaviorBox ingest path is receiver-backed: `run_eye_receiver_service.py`
runs outside MATLAB, and `BehaviorBoxEyeTrack.m` imports finalized chunks through
that receiver's HTTP API.

The older helpers `Stream-DeepLabCut/matlab_zmq_bridge.py` and
`Stream-DeepLabCut/receive_eye_stream_demo.m` are retained as reference/demo
tools, but they are not the active production ingest path used by BehaviorBox.

## Models

Active runtime models live under `Models/`.

- Model blobs are intentionally excluded from git history.
- See [Models/README.md](Models/README.md) for expected active-model placement.
- `Stream-DeepLabCut/run_eye_stream_production.py` defaults to the
  `Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1` layout.
