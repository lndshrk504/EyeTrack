# Tests

This folder contains bounded Python-side smoke checks for eye-tracking environments,
cameras, and inference timing. These scripts are diagnostics, not production pipeline code.

## Production path (for reference)

The active runtime path in this repo is:

- `../ToMatlab/dlc_eye_streamer.py`
- `../ToMatlab/behavior_eye_receiver.py`
- `../ToMatlab/run_eye_receiver_service.py`
- `../ToMatlab/run_eye_stream_production.py`
- `../ToMatlab/run_matlab_eye_receive_test.py`
- `../ToMatlab/run_eye_stream_receive_test.m`

`../ToMatlab/matlab_zmq_bridge.py` is retained as older reference tooling, but it is not the production ingest path used by BehaviorBox.

## Scripts

- `VerCheck.py`: prints Python executable, environment, package versions, TensorFlow
  CUDA/cuDNN/TensorRT build metadata, and visible TensorFlow GPUs.
- `TestSpin.py`: bounded PySpin smoke test for FLIR/Point Grey cameras.
- `capture_flir_training_frames.py`: FLIR/PySpin raw-frame capture utility for
  collecting candidate DeepLabCut retraining images.
- `GSTOCV.py`: bounded OpenCV smoke test for GStreamer/Aravis cameras or regular USB
  cameras.
- `smoke_dlc_flir_inference.py`: bounded FLIR + DLCLive timing smoke test that reports
  capture, copy, release, preprocess, inference, display, overhead, total time, and FPS.
- `Spin2DLC.py`: compatibility wrapper for `smoke_dlc_flir_inference.py`.
- `CheckReqs.py`: compact TensorFlow CUDA/cuDNN build-info check.

## Examples

Run from `DeepLabCut/Tests/`.

Runtime environment inventory:

```bash
python VerCheck.py
python VerCheck.py --strict
```

PySpin frame grab:

```bash
python TestSpin.py --camera-index 0 --sensor-roi 0 0 640 480 --frames 120
```

FLIR training-frame capture:

```bash
python capture_flir_training_frames.py
```

By default this opens a preview, uses production-like camera settings
(`Mono8`, sensor ROI `0 0 640 480`, 60 Hz, 6000 us exposure, gain auto off),
and writes timestamped sessions under `~/Desktop/EyeTrackTrainingFrames/`.
Press `s` or Space to save the current raw frame; press `q` or Esc to quit.
The saved PNGs are the raw camera arrays, not the preview overlay or scaled
display image.

Headless timed capture:

```bash
python capture_flir_training_frames.py \
  --output-dir ~/Desktop/EyeTrackTrainingFrames \
  --seconds 2 \
  --save-every 10 \
  --no-preview
```

Each run writes `frames/*.png`, `manifest.csv`, and `metadata.json` inside a
new `session_YYYYMMDD_HHMMSS/` folder.

Forwarded SSH/X11 capture from the behavior computer:

```bash
cd ../ToMatlab/ssh_x11
./open_training_capture_over_ssh.sh --host wbs@10.55.0.1 -- --auto-contrast --scale 0.5
```

The forwarded preview runs on the eye-tracking computer and displays on the
behavior computer. Saved frames are written on the eye-tracking computer under
`~/Desktop/EyeTrackTrainingFrames/` by default.
See `../ToMatlab/ssh_x11/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md` for the full
step-by-step workflow.

GStreamer/Aravis camera:

```bash
python GSTOCV.py --backend gstreamer --width 640 --height 480 --fps 120 --frames 120
```

USB camera:

```bash
python GSTOCV.py --backend usb --source 0 --width 640 --height 480 --fps 30 --frames 120
```

FLIR + DLC timing:

```bash
python smoke_dlc_flir_inference.py \
  --model-path ../../models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --model-preset yanglab-pupil8 \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frames 120
```

Receiver smoke test lives in `../ToMatlab/`:

```bash
cd ../ToMatlab
python test_behavior_eye_receiver.py
```
