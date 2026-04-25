# FLIR Training Capture Over SSH/X11

This guide records the exact workflow for collecting raw FLIR camera images for
future DeepLabCut/TensorFlow retraining while viewing the capture window through
SSH/X11 forwarding.

The camera and image files are on the eye-tracking computer. The preview window
is displayed on the behavior computer through `ssh -Y`.

## Real Execution Path

- Local wrapper on the behavior computer:
  `ssh_x11/open_training_capture_over_ssh.sh`
- Remote capture utility on the eye-tracking computer:
  `Cam-Tests/capture_flir_training_frames.py`
- Remote default output root:
  `~/Desktop/EyeTrackTrainingFrames`

The wrapper opens a trusted X11 SSH session, activates the remote `dlclivegui`
conda environment, changes into `Cam-Tests`, and runs:

```bash
python capture_flir_training_frames.py "$@"
```

Arguments after `--` are passed directly to
`capture_flir_training_frames.py`.

## Quick Start

Run this from the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./open_training_capture_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --camera-index 0 \
  --auto-contrast \
  --scale 0.5
```

Replace `<user>` with the login account on the eye-tracking computer. The
capture utility still runs on the eye-tracking computer; only the preview window
is forwarded.

In the forwarded preview window:

- press `s` or Space to save the current raw frame
- press `q` or Esc to quit
- closing the window also quits

Saved images and metadata are written on the eye-tracking computer:

```text
~/Desktop/EyeTrackTrainingFrames/session_YYYYMMDD_HHMMSS/
  frames/
    capture_000001_frame_000123.png
    capture_000002_frame_000456.png
  manifest.csv
  metadata.json
```

## What Gets Saved

Saved PNG files are raw camera arrays from `image.GetNDArray().copy()`.
Preview scaling, overlay text, and `--auto-contrast` are display-only and are
not baked into the training images.

Default camera settings match the production-like capture defaults:

- camera index: `0`
- sensor ROI: `0 0 640 480`
- pixel format: `Mono8`
- frame rate: `60`
- exposure: `6000` microseconds
- gain auto: `off`
- gain: `0` dB
- restore camera settings on exit: enabled

Each session writes:

- `frames/*.png`: raw lossless images for labeling
- `manifest.csv`: one row per saved image with frame id, timestamp, trigger,
  shape, dtype, and intensity statistics
- `metadata.json`: command, host details, output paths, requested camera
  settings, applied camera info, and capture policy

## Useful Variants

Save every 10th complete camera frame while still showing the forwarded preview:

```bash
./open_training_capture_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --save-every 10 \
  --auto-contrast \
  --scale 0.5
```

Collect into a named session folder:

```bash
./open_training_capture_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --session-name session_retrain_mouse01 \
  --auto-contrast \
  --scale 0.5
```

Use a different remote output root:

```bash
./open_training_capture_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --output-dir ~/Desktop/EyeTrackTrainingFrames \
  --auto-contrast \
  --scale 0.5
```

Run headless timed capture on the eye-tracking computer through normal SSH
instead of X11:

```bash
ssh <user>@10.55.0.1
source ~/miniforge3/etc/profile.d/conda.sh
conda activate dlclivegui
cd ~/Desktop/BehaviorBox/EyeTrack/Cam-Tests
python3 capture_flir_training_frames.py \
  --seconds 60 \
  --save-every 10 \
  --no-preview
```

Headless capture is better for long timed collections because an X11 disconnect
cannot close the OpenCV preview window.

## Verify The Output

On the eye-tracking computer:

```bash
find ~/Desktop/EyeTrackTrainingFrames -maxdepth 3 -type f | sort | tail -40
```

Expected files include:

- at least one `frames/capture_*.png`
- `manifest.csv`
- `metadata.json`

Check the manifest header:

```bash
head -2 ~/Desktop/EyeTrackTrainingFrames/session_*/manifest.csv
```

## Troubleshooting

If no forwarded window appears, verify the behavior computer has a local display:

```bash
echo "$DISPLAY"
```

Then verify SSH/X11 forwarding:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./test_x11_forwarding_over_ssh.sh --host <user>@10.55.0.1
```

If the preview is slow, use a smaller display scale:

```bash
./open_training_capture_over_ssh.sh --host <user>@10.55.0.1 -- --scale 0.25 --auto-contrast
```

If the script reports missing Python modules, run it from the eye-tracking
computer's `dlclivegui` environment. The capture path needs `cv2`, `PySpin`,
and the FLIR camera visible to PySpin.

If you need a quick camera check on the eye-tracking computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack
python3 Stream-DeepLabCut/check_pyspin_camera.py
python3 Cam-Tests/TestSpin.py --camera-index 0 --sensor-roi 0 0 640 480 --frames 120
```

## Contracts

This workflow does not change the production eye stream, ZMQ payloads,
`/tmp/EyeTrack` CSV outputs, MATLAB receive behavior, or model-path handling.
It only collects separate raw training images for future labeling and model
retraining.
