# SSH/X11 Forwarded Preview on Pop!_OS 22/24

This guide shows how to remove the dedicated display, mouse, and keyboard from the eye-tracking computer while still being able to:

- preview the FLIR camera during setup,
- capture FLIR training images through the forwarded preview,
- start the production eye stream over SSH,
- check whether the remote eye-stream process is running,
- stop the remote eye-stream process over SSH.

It assumes:

- both computers run Pop!_OS 22 or Pop!_OS 24,
- the eye-tracking computer is the direct-cable host at `10.55.0.1`,
- the behavior computer is the direct-cable host at `10.55.0.2`,
- the existing two-computer networking from [TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md](./TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md) is already in place.

## Recommended Operating Pattern

Use SSH/X11 only for camera alignment and occasional drift checks. Do not depend on a forwarded OpenCV window for the full session unless you accept that a GUI disconnect can stop the remote process.

Recommended workflow:

1. Run the one-time SSH/X11 setup script on the eye-tracking computer.
2. From the behavior computer, open a forwarded FLIR preview for alignment.
3. Optionally open a forwarded FLIR training-frame capture window and save raw
   images for future retraining.
4. Close those preview windows after setup or image collection.
5. Start the production eye stream headless over SSH with `--no-display`.
6. Check process status over SSH when needed.
7. Stop the production eye stream over SSH at the end of the session.

That pattern is safer than leaving the main inference preview window open for hours.

## Real Execution Path

These are the existing repo paths involved in SSH/X11 use:

- Preview-only alignment path:
  [`DeepLabCut/Tests/FLIRCam.py`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/Tests/FLIRCam.py)
- Training-frame capture path:
  [`DeepLabCut/Tests/capture_flir_training_frames.py`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/Tests/capture_flir_training_frames.py)
- Production launcher:
  [`DeepLabCut/ToMatlab/run_eye_stream_production.py`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/run_eye_stream_production.py)
- Production streamer and OpenCV display loop:
  [`DeepLabCut/ToMatlab/dlc_eye_streamer.py`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/dlc_eye_streamer.py)

The new helper scripts in this guide do not replace those paths. They wrap them over SSH.

## Why Preview-Only Is Safer Than Forwarding the Main Streamer Window

`dlc_eye_streamer.py` uses an OpenCV display loop for the live overlay window. If that window is closed, or the forwarded GUI connection dies, the streamer can stop. That makes plain SSH X11 forwarding acceptable for setup and spot checks, but not ideal as the only monitoring path for a long unattended session.

`FLIRCam.py` is the better tool for alignment because:

- it exercises the same FLIR camera stack,
- it is independent of the production ZMQ stream,
- closing the preview does not interrupt a running behavior session because it is not the production process.

## Files Added for This Workflow

The helper scripts live here:

- [`DeepLabCut/ToMatlab/ssh_x11/setup_eye_host_ssh_x11.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/setup_eye_host_ssh_x11.sh)
- [`DeepLabCut/ToMatlab/ssh_x11/test_x11_forwarding_over_ssh.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/test_x11_forwarding_over_ssh.sh)
- [`DeepLabCut/ToMatlab/ssh_x11/open_alignment_preview_over_ssh.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/open_alignment_preview_over_ssh.sh)
- [`DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh)
- [`DeepLabCut/ToMatlab/ssh_x11/start_eye_stream_over_ssh.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/start_eye_stream_over_ssh.sh)
- [`DeepLabCut/ToMatlab/ssh_x11/eye_stream_status_over_ssh.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/eye_stream_status_over_ssh.sh)
- [`DeepLabCut/ToMatlab/ssh_x11/stop_eye_stream_over_ssh.sh`](/Users/willsnyder/Desktop/EyeTrack/DeepLabCut/ToMatlab/ssh_x11/stop_eye_stream_over_ssh.sh)

## One-Time Setup on the Eye-Tracking Computer

Run this on the eye-tracking computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
sudo ./setup_eye_host_ssh_x11.sh --behavior-ip 10.55.0.2
```

What the setup script does:

- checks for the standard Pop!_OS `/etc/ssh/sshd_config.d` include path,
- writes an SSH drop-in enabling `X11Forwarding yes` and `X11UseLocalhost yes`,
- validates the SSH daemon configuration,
- enables and restarts the `ssh` service,
- adds `ufw` rules for SSH port `22` and eye-stream port `5555` if `ufw` is active.

If `openssh-server` or `xauth` is missing, rerun with:

```bash
sudo ./setup_eye_host_ssh_x11.sh --behavior-ip 10.55.0.2 --install-missing
```

## Behavior Computer Requirements

Run the next commands from a normal graphical desktop login on the behavior computer, not from a text console.

On Pop!_OS, X11 forwarding usually works through Xwayland as long as a normal desktop session is active and `DISPLAY` is set.

Check locally:

```bash
echo "$DISPLAY"
```

If that prints an empty string, the behavior computer does not currently have a local X display available for `ssh -Y`.

Then test forwarding:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./test_x11_forwarding_over_ssh.sh --host wbs@10.55.0.1
```

If `xclock` is installed on the eye-tracking computer and you want a visual test:

```bash
./test_x11_forwarding_over_ssh.sh --host wbs@10.55.0.1 --try-xclock
```

## 1. Open a Forwarded Alignment Preview

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./open_alignment_preview_over_ssh.sh \
  --host wbs@10.55.0.1 \
  -- \
  --camera-index 0 \
  --gain-auto continuous \
  --auto-contrast \
  --scale 0.5
```

The script:

- opens a trusted X11 SSH session with `ssh -Y`,
- activates the remote `dlclivegui` conda environment,
- runs `DeepLabCut/Tests/FLIRCam.py` on the eye-tracking computer,
- draws the preview window on the behavior computer.

Close the preview window, or press `q` or `Esc`, when alignment is done.

## 2. Capture Training Frames Through X11

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./open_training_capture_over_ssh.sh \
  --host wbs@10.55.0.1 \
  -- \
  --camera-index 0 \
  --auto-contrast \
  --scale 0.5
```

The script:

- opens a trusted X11 SSH session with `ssh -Y`,
- activates the remote `dlclivegui` conda environment,
- runs `DeepLabCut/Tests/capture_flir_training_frames.py` on the eye-tracking computer,
- draws the preview window on the behavior computer,
- writes saved PNGs, `manifest.csv`, and `metadata.json` on the eye-tracking
  computer under `~/Desktop/EyeTrackTrainingFrames/` by default.

In the forwarded preview, press `s` or Space to save the current raw frame.
Press `q` or `Esc`, or close the window, when image collection is done.

The saved PNGs are raw camera arrays. Preview scaling, overlay text, and
`--auto-contrast` are not baked into the saved training images.

## 3. Start the Production Eye Stream Headless

After alignment looks good, start the production streamer without a GUI:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./start_eye_stream_over_ssh.sh \
  --host wbs@10.55.0.1 \
  -- \
  --address tcp://10.55.0.1:5555 \
  --model-path /home/wbs/Desktop/BehaviorBox/EyeTrack/models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --model-preset yanglab-pupil8 \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto continuous \
  --display-fps 2
```

If you do not explicitly pass `--display`, the wrapper adds `--no-display` automatically.

Run this from a dedicated terminal tab or pane. Stop it with `Ctrl+C` when you are finished, or use the stop script below from another terminal.

## 4. Check Whether the Remote Stream Is Running

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./eye_stream_status_over_ssh.sh --host wbs@10.55.0.1
```

This reports:

- matching `run_eye_stream_production.py` and `dlc_eye_streamer.py` processes,
- whether port `5555` is listening,
- the most recent CSV files under `/tmp/EyeTrack`.

## 5. Stop the Remote Stream from Another Terminal

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./stop_eye_stream_over_ssh.sh --host wbs@10.55.0.1
```

This sends `SIGINT` first so the streamer follows its normal shutdown path.

## Optional: Forward the Production Overlay Window Anyway

If you want to see the production overlay over SSH, you can do it, but it is more fragile than the preview-only pattern.

From the behavior computer:

```bash
./start_eye_stream_over_ssh.sh \
  --host wbs@10.55.0.1 \
  -- \
  --address tcp://10.55.0.1:5555 \
  --model-path /home/wbs/Desktop/BehaviorBox/EyeTrack/models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto continuous \
  --display \
  --display-scale 0.5 \
  --display-fps 1
```

Use a very low `--display-fps` if your goal is only to confirm that the eye remains in frame.

Risk:

- if the forwarded OpenCV window closes,
- or if the X11 SSH connection drops,
- the production streamer may stop.

## Troubleshooting

### `X11 forwarding request failed on channel 0`

On the eye-tracking computer, re-run:

```bash
sudo ./setup_eye_host_ssh_x11.sh --behavior-ip 10.55.0.2 --install-missing
```

Then verify:

```bash
sudo sshd -t
systemctl status ssh --no-pager
```

### No Window Appears on the Behavior Computer

Check locally on the behavior computer:

```bash
echo "$DISPLAY"
```

Check remotely:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/DeepLabCut/ToMatlab/ssh_x11
./test_x11_forwarding_over_ssh.sh --host wbs@10.55.0.1
```

The remote `DISPLAY` value should not be empty during an X11-forwarded session.

### The Preview Is Too Slow

That is expected over SSH/X11. Lower the amount of work:

- use `--scale 0.5` or smaller for `FLIRCam.py`,
- use `--scale 0.5` or smaller for `capture_flir_training_frames.py`,
- keep the preview only long enough to align the mouse,
- use the training capture preview only long enough to collect images,
- run the production streamer with `--no-display` after setup.

### The Streamer Stops When the Preview Window Closes

That behavior is expected for the production overlay window. Use the preview-only `FLIRCam.py` path for alignment, then run `run_eye_stream_production.py` headless.

## Summary

For your room setup, the least fragile arrangement is:

1. no dedicated display on the eye-tracking computer,
2. one-time SSH/X11 setup on the eye-tracking computer,
3. forwarded `FLIRCam.py` preview from the behavior computer only when aligning,
4. forwarded `capture_flir_training_frames.py` preview only when collecting training images,
5. headless production inference over SSH for the session itself,
6. status and stop commands over SSH from the behavior computer.
