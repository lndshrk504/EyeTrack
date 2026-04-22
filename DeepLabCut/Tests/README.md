# Tests

This folder contains bounded Python-side smoke checks for eye-tracking environments,
cameras, and inference timing. These scripts are diagnostics, not production pipeline code.

## Production path (for reference)

The active runtime path in this repo is:

- `../ToMatlab/dlc_eye_streamer.py`
- `../ToMatlab/matlab_zmq_bridge.py`
- `../ToMatlab/run_eye_stream_production.py`
- `../ToMatlab/run_matlab_eye_receive_test.py`

## Scripts

- `VerCheck.py`: prints Python executable, environment, package versions, TensorFlow
  CUDA/cuDNN/TensorRT build metadata, and visible TensorFlow GPUs.
- `TestSpin.py`: bounded PySpin smoke test for FLIR/Point Grey cameras.
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
