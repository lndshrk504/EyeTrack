# Single-Computer Eye Tracking Quick Start

This guide runs FLIR eye tracking and BehaviorBox on the same Linux computer.
It uses the remodeled runtime path:

1. Python streamer publishes FLIR + DLCLive samples over local ZeroMQ.
2. Python receiver subscribes to that local stream and writes segment chunks.
3. MATLAB/BehaviorBox talks to the receiver HTTP API and imports finalized
   chunks outside the hot behavior loops.

This is the right setup when the same computer has the FLIR camera, the
DeepLabCut runtime environment, MATLAB, and BehaviorBox.

## When To Use This

Use the single-computer workflow when:

- the FLIR camera is plugged into the behavior computer,
- the computer can run DLCLive inference and MATLAB at the same time,
- you do not need the direct Ethernet `10.55.0.1` / `10.55.0.2` split,
- you want the simplest wiring for development, testing, or a lighter rig.

Use the two-computer workflow instead if DeepLabCut inference or preview display
causes behavior timing or UI lag.

## Local Data Flow

```text
FLIR camera
  -> Stream-DeepLabCut/run_eye_stream_production.py
  -> tcp://127.0.0.1:5555
  -> Stream-DeepLabCut/run_eye_receiver_service.py
  -> http://127.0.0.1:8765
  -> BehaviorBoxEyeTrack.m
  -> BehaviorBoxWheel.m session save
```

For one computer, keep both defaults local:

- ZMQ stream address: `tcp://127.0.0.1:5555`
- receiver API URL: `http://127.0.0.1:8765`

Do not use `tcp://10.55.0.1:5555` unless you are intentionally running the
two-computer direct-cable workflow.

## Prerequisites

The computer should already have:

- FLIR/Spinnaker installed, with the camera visible in SpinView,
- a Python environment for the eye streamer, usually `dlclivegui`,
- PySpin visible inside that environment,
- the active exported model under `EyeTrack/Models/`,
- MATLAB installed,
- the BehaviorBox repo containing this EyeTrack repo.

Expected repo layout:

```text
~/Desktop/BehaviorBox/
  BehaviorBoxWheel.m
  BehaviorBoxEyeTrack.m
  EyeTrack/
    Stream-DeepLabCut/
    Cam-Tests/
    Models/
```

## 1. Check Camera Visibility

Run this from the EyeTrack repo:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack
conda activate dlclivegui
python3 Stream-DeepLabCut/check_pyspin_camera.py
```

Expected result: at least one detected FLIR/Point Grey camera.

Optional bounded FLIR smoke test:

```bash
python3 Cam-Tests/TestSpin.py \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frames 120
```

## 2. Start The Eye Streamer

Open terminal 1:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate dlclivegui

./run_eye_stream_production.py \
  --address tcp://127.0.0.1:5555 \
  --model-path ../Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --model-preset yanglab-pupil8 \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto off \
  --display-fps 10
```

Notes:

- `127.0.0.1` is correct because the receiver is on the same computer.
- The streamer still writes its own CSV and metadata sidecar under
  `/tmp/EyeTrack` by default.
- If the preview competes with BehaviorBox, use `--no-display` or lower
  `--display-fps`.

## 3. Start The Local Receiver

Open terminal 2:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate bbeyezmq

./run_eye_receiver_service.py \
  --address tcp://127.0.0.1:5555 \
  --api-port 8765
```

The receiver environment only needs enough Python support to run the receiver
and import `zmq`. If you do not have a separate `bbeyezmq` environment, the
full `dlclivegui` environment is also fine:

```bash
conda activate dlclivegui
```

Leave the receiver running while MATLAB and BehaviorBox are active.

Quick receiver health check from another terminal:

```bash
curl http://127.0.0.1:8765/health
```

## 4. Run A MATLAB Receive Smoke Test

With the streamer and receiver already running, run:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate bbeyezmq

./run_matlab_eye_receive_test.py \
  --address tcp://127.0.0.1:5555 \
  --receiver-url http://127.0.0.1:8765 \
  --duration 10
```

Expected successful ending:

```text
MATLAB_EYE_STREAM_RECEIVE_OK
```

If no eye is visible, transport can still work while readiness remains false or
samples report `no_points`. Put the eye in frame before using the result as a
full behavior-session smoke test.

## 5. Start MATLAB And BehaviorBox

Open terminal 3:

```bash
cd ~/Desktop/BehaviorBox
matlab
```

If the receiver uses the default URL `http://127.0.0.1:8765`, no extra
environment variable is needed. `BehaviorBoxEyeTrack.m` defaults to that local
receiver URL.

If you changed the receiver API port, set this before starting MATLAB:

```bash
export BB_EYETRACK_RECEIVER_URL=http://127.0.0.1:9000
cd ~/Desktop/BehaviorBox
matlab
```

Then start BehaviorBox normally. During session setup,
`BehaviorBoxWheel.m` calls `BehaviorBoxEyeTrack.tryCreateFromEnvironment()`.
If the receiver is reachable, eye tracking is attached to the session. If it is
not reachable, BehaviorBox should warn and continue without blocking the session.

## 6. Confirm Saved Outputs

After a session save with eye data available, saved behavior files should include
some or all of:

- `EyeTrackRecord`
- `EyeTrackSegmentMeta`
- `EyeTrackingRecord`
- `EyeTrackingMeta`
- `FrameAlignedRecord`
- `EyeAlignedRecord`

The streamer-side `/tmp/EyeTrack/eye_stream_*.csv` files are useful for runtime
debugging, but the BehaviorBox session should use receiver-managed chunks and
MATLAB-imported records.

## Shutdown Order

Recommended order:

1. Stop the BehaviorBox session and let MATLAB finish saving.
2. Close MATLAB if you are done.
3. Stop `run_eye_receiver_service.py` with `Ctrl+C`.
4. Stop `run_eye_stream_production.py` with `Ctrl+C`.

BehaviorBox finalizes/imports eye chunks during save. It does not stop the
external Python streamer or receiver processes for you.

## Troubleshooting

### MATLAB Cannot Connect To The Receiver

Check that the receiver is running:

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8765/status
```

If you changed the receiver URL, confirm MATLAB inherited it:

```bash
echo "$BB_EYETRACK_RECEIVER_URL"
```

### Receiver Gets Zero Samples

For a single-computer setup, both commands should use the local ZMQ address:

```bash
./run_eye_stream_production.py --address tcp://127.0.0.1:5555
./run_eye_receiver_service.py --address tcp://127.0.0.1:5555 --api-port 8765
```

Do not mix local `127.0.0.1` and direct-cable `10.55.0.1` addresses in this
workflow.

### BehaviorBox Feels Sluggish

Reduce display load first:

```bash
./run_eye_stream_production.py \
  --address tcp://127.0.0.1:5555 \
  --display-fps 2
```

For the lowest GUI load:

```bash
./run_eye_stream_production.py \
  --address tcp://127.0.0.1:5555 \
  --no-display
```

If MATLAB or behavior timing is still affected, move back to the two-computer
workflow.

### PySpin Works In SpinView But Not Python

Test inside the streamer environment:

```bash
conda activate dlclivegui
python3 -c "import PySpin; print('PySpin OK')"
```

If that fails, install the Spinnaker Python wheel that matches the environment's
Python version.

## Minimal Command Summary

Terminal 1, streamer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate dlclivegui
./run_eye_stream_production.py --address tcp://127.0.0.1:5555 --frame-rate 60 --exposure-us 6000 --gain-auto off --display-fps 10
```

Terminal 2, receiver:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate bbeyezmq
./run_eye_receiver_service.py --address tcp://127.0.0.1:5555 --api-port 8765
```

Terminal 3, MATLAB:

```bash
cd ~/Desktop/BehaviorBox
matlab
```

Optional smoke test before MATLAB/BehaviorBox:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/Stream-DeepLabCut
./run_matlab_eye_receive_test.py --address tcp://127.0.0.1:5555 --receiver-url http://127.0.0.1:8765 --duration 10
```
