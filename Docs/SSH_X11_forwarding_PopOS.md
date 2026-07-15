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

The examples use `<user>@10.55.0.1` for the SSH target. Replace `<user>` with
the account on the eye-tracking computer, for example `wbs`.

## Recommended Operating Pattern

The current production workflow intentionally keeps the X11-forwarded OpenCV
overlay open at 5 display FPS. This makes live alignment and runtime monitoring
available on the behavior computer, with the accepted tradeoff that closing the
window or losing the X11 connection can stop the remote streamer.

Recommended workflow:

1. Run the one-time SSH/X11 setup script on the eye-tracking computer.
2. From the behavior computer, open a forwarded FLIR preview for alignment.
3. Optionally open a forwarded FLIR training-frame capture window and save raw
   images for future retraining.
4. Close those preview windows after setup or image collection.
5. Start the production eye stream with the X11-forwarded overlay at 5 display
   FPS.
6. Check process status over SSH when needed.
7. Stop the production eye stream over SSH at the end of the session.

For normal two-computer operation, the root
`run_two_computer_eye_tracking.sh` supervisor performs steps 5 through 7,
starts the local receiver, and supervises both EyeTrack services until the
operator presses `Ctrl+C`. MATLAB and BehaviorBox are started and stopped
independently.

## Real Execution Path

These are the existing repo paths involved in SSH/X11 use:

- Preview-only alignment path:
  [`Cam-Tests/FLIRCam.py`](../Cam-Tests/FLIRCam.py)
- Training-frame capture path:
  [`Cam-Tests/capture_flir_training_frames.py`](../Cam-Tests/capture_flir_training_frames.py)
- Production launcher:
  [`Stream-DeepLabCut/run_eye_stream_production.py`](../Stream-DeepLabCut/run_eye_stream_production.py)
- Production streamer and OpenCV display loop:
  [`Stream-DeepLabCut/dlc_eye_streamer.py`](../Stream-DeepLabCut/dlc_eye_streamer.py)

The new helper scripts in this guide do not replace those paths. They wrap them over SSH.

## Why Preview-Only Is Safer Than Forwarding the Main Streamer Window

`dlc_eye_streamer.py` uses an OpenCV display loop for the live overlay window. If that window is closed, or the forwarded GUI connection dies, the streamer can stop. That makes plain SSH X11 forwarding acceptable for setup and spot checks, but not ideal as the only monitoring path for a long unattended session.

`FLIRCam.py` is the better tool for alignment because:

- it exercises the same FLIR camera stack,
- it is independent of the production ZMQ stream,
- closing the preview does not interrupt a running behavior session because it is not the production process.

## Files Added for This Workflow

The helper scripts live here:

- [`ssh_x11/setup_eye_host_ssh_x11.sh`](../ssh_x11/setup_eye_host_ssh_x11.sh)
- [`ssh_x11/test_x11_forwarding_over_ssh.sh`](../ssh_x11/test_x11_forwarding_over_ssh.sh)
- [`ssh_x11/open_alignment_preview_over_ssh.sh`](../ssh_x11/open_alignment_preview_over_ssh.sh)
- [`ssh_x11/open_training_capture_over_ssh.sh`](../ssh_x11/open_training_capture_over_ssh.sh)
- [`ssh_x11/start_eye_stream_over_ssh.sh`](../ssh_x11/start_eye_stream_over_ssh.sh)
- [`ssh_x11/eye_stream_status_over_ssh.sh`](../ssh_x11/eye_stream_status_over_ssh.sh)
- [`ssh_x11/stop_eye_stream_over_ssh.sh`](../ssh_x11/stop_eye_stream_over_ssh.sh)
- [`run_two_computer_eye_tracking.sh`](../run_two_computer_eye_tracking.sh)

## One-Time Setup on the Eye-Tracking Computer

Review the intended changes on the eye-tracking computer first:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./setup_eye_host_ssh_x11.sh --behavior-ip 10.55.0.2 --dry-run
```

Then apply them:

```bash
sudo ./setup_eye_host_ssh_x11.sh --behavior-ip 10.55.0.2
```

What the setup script does:

- checks for the standard Pop!_OS `/etc/ssh/sshd_config.d` include path,
- writes an SSH drop-in enabling `X11Forwarding yes` and `X11UseLocalhost yes`,
- validates the SSH daemon configuration,
- verifies the effective X11 settings before reporting success,
- enables and restarts the `ssh` service,
- adds `ufw` rules for SSH port `22` and eye-stream port `5555` if `ufw` is active.

The optional `--conf-file` value must name a regular `.conf` file directly
under `/etc/ssh/sshd_config.d`. Paths outside that included drop-in directory,
symlinks, and parent traversal are rejected before any write.

If `openssh-server` or `xauth` is missing, rerun with:

```bash
sudo ./setup_eye_host_ssh_x11.sh --behavior-ip 10.55.0.2 --install-missing
```

## Behavior Computer Requirements

Run the next commands from a normal graphical desktop login on the behavior computer, not from a text console.

On Pop!_OS, X11 forwarding usually works through Xwayland as long as a normal desktop session is active and `DISPLAY` is set.

These wrappers use trusted forwarding (`ssh -Y`). A trusted remote X client can
interact with the behavior computer's X session, so use this workflow only with
the dedicated, trusted eye-tracking host on the private link.

Check locally:

```bash
echo "$DISPLAY"
```

If that prints an empty string, the behavior computer does not currently have a local X display available for `ssh -Y`.

Then test forwarding:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./test_x11_forwarding_over_ssh.sh --host <user>@10.55.0.1
```

A pass requires the remote host to open the forwarded display with `xdpyinfo`
or `xset`. The test fails if neither noninteractive probe is installed; it does
not treat a nonempty `DISPLAY` and an `xauth` executable as sufficient.

If `xclock` is installed on the eye-tracking computer and you want a visual test:

```bash
./test_x11_forwarding_over_ssh.sh --host <user>@10.55.0.1 --try-xclock
```

## 1. Open a Forwarded Alignment Preview

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./open_alignment_preview_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --camera-index 0 \
  --gain-auto continuous \
  --auto-contrast \
  --scale 0.5
```

The script:

- opens a trusted X11 SSH session with `ssh -Y`,
- activates the remote `dlclivegui` conda environment,
- runs `Cam-Tests/FLIRCam.py` on the eye-tracking computer,
- draws the preview window on the behavior computer.

Close the preview window, or press `q` or `Esc`, when alignment is done.

## 2. Capture Training Frames Through X11

For the focused image-capture instructions, see
[`Capture-FLIR-Images-Over-SSH.md`](./Capture-FLIR-Images-Over-SSH.md).

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./open_training_capture_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --camera-index 0 \
  --auto-contrast \
  --scale 0.5
```

The script:

- opens a trusted X11 SSH session with `ssh -Y`,
- activates the remote `dlclivegui` conda environment,
- runs `Cam-Tests/capture_flir_training_frames.py` on the eye-tracking computer,
- draws the preview window on the behavior computer,
- writes saved PNGs, `manifest.csv`, and `metadata.json` on the eye-tracking
  computer under `~/Desktop/EyeTrackTrainingFrames/` by default.

In the forwarded preview, press `s` or Space to save the current raw frame.
Press `q` or `Esc`, or close the window, when image collection is done.

The saved PNGs are raw camera arrays. Preview scaling, overlay text, and
`--auto-contrast` are not baked into the saved training images.

## 3. Start the Production Eye Stream With Its Forwarded Overlay

The recommended command from the behavior computer is the root supervisor:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack
./run_two_computer_eye_tracking.sh
```

It checks X11, starts the overlay at 5 display FPS, starts the receiver, and
waits for samples. It does not start MATLAB. After warm-up, start the BehaviorBox
session in the independently running MATLAB instance; after the session saves,
press `Ctrl+C` in the supervisor terminal to stop both EyeTrack services.

To start only the remote streamer wrapper manually:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./start_eye_stream_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --address tcp://10.55.0.1:5555 \
  --model-path /home/<user>/Desktop/BehaviorBox/EyeTrack/models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --model-preset yanglab-pupil8 \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto continuous \
  --display \
  --display-fps 5
```

If neither display flag is supplied, the wrapper now adds
`--display --display-fps 5`. An explicit `--no-display` remains available for
an intentional headless troubleshooting run.

Run this from a dedicated terminal tab or pane. Stop it with `Ctrl+C` when you are finished, or use the stop script below from another terminal.

## 4. Check Whether the Remote Stream Is Running

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./eye_stream_status_over_ssh.sh \
  --host <user>@10.55.0.1 \
  --address tcp://10.55.0.1:5555 \
  --csv-dir /tmp/EyeTrack
```

This reports:

- matching `run_eye_stream_production.py` and `dlc_eye_streamer.py` processes,
- whether a listener serves the requested endpoint host and port,
- the most recent CSV files under the requested output directory.

The command exits nonzero unless a matching EyeTrack process owns the requested
listener. A wildcard bind can serve any requested local interface, but a
localhost-only bind does not satisfy a direct-link address such as
`10.55.0.1`. `--port PORT` can override the port parsed from `--address` when
needed.

## 5. Stop the Remote Stream from Another Terminal

From the behavior computer:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./stop_eye_stream_over_ssh.sh \
  --host <user>@10.55.0.1 \
  --timeout-s 10
```

This sends `SIGINT`, polls until the matching processes exit, and returns
nonzero if they are still present after the timeout. The default poll interval
is `0.25` seconds and can be changed with `--poll-interval-s`.

## Optional: Run Headless For Troubleshooting

The forwarded overlay is the default. To run the low-level wrapper without it,
pass `--no-display` explicitly:

From the behavior computer:

```bash
./start_eye_stream_over_ssh.sh \
  --host <user>@10.55.0.1 \
  -- \
  --address tcp://10.55.0.1:5555 \
  --model-path /home/<user>/Desktop/BehaviorBox/EyeTrack/models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto continuous \
  --no-display
```

This removes the X11 window dependency but also removes the requested live
production overlay.

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
cd ~/Desktop/BehaviorBox/EyeTrack/ssh_x11
./test_x11_forwarding_over_ssh.sh --host <user>@10.55.0.1
```

The remote `DISPLAY` value should not be empty during an X11-forwarded session.

### The Preview Is Too Slow

That is expected over SSH/X11. Lower the amount of work:

- use `--scale 0.5` or smaller for `FLIRCam.py`,
- use `--scale 0.5` or smaller for `capture_flir_training_frames.py`,
- keep the preview only long enough to align the mouse,
- use the training capture preview only long enough to collect images,
- keep the production overlay at its default `--display-fps 5`, or use the
  explicit `--no-display` troubleshooting override if necessary.

### The Streamer Stops When the Preview Window Closes

That behavior is expected for the production overlay window. Restart through
`run_two_computer_eye_tracking.sh`; it will recheck X11 and start a new,
supervisor-owned streamer and receiver. Use explicit `--no-display` only when
you intentionally accept losing the production overlay.

## Summary

For your room setup, the requested operating arrangement is:

1. no dedicated display on the eye-tracking computer,
2. one-time SSH/X11 setup on the eye-tracking computer,
3. forwarded `FLIRCam.py` preview from the behavior computer only when aligning,
4. forwarded `capture_flir_training_frames.py` preview only when collecting training images,
5. MATLAB/BehaviorBox started independently while the mouse warms up,
6. the X11-forwarded production overlay and receiver started when eye tracking
   should begin, and
7. operator-controlled receiver and streamer shutdown with `Ctrl+C` after the
   BehaviorBox session finishes saving.
