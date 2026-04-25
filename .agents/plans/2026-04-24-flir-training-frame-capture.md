# FLIR Training Frame Capture

- Status: Implemented
- Created: 2026-04-24
- Last updated: 2026-04-24

## Goal

Add a focused FLIR/PySpin raw-frame capture utility for collecting candidate
DeepLabCut/TensorFlow retraining images under `~/Desktop/EyeTrackTrainingFrames`.

## Active paths

- `DeepLabCut/Tests/capture_flir_training_frames.py`
- `DeepLabCut/Tests/README.md`
- `DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh`
- `DeepLabCut/ToMatlab/ssh_x11/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`
- `DeepLabCut/SSH_X11_FORWARDING_POPOS.md`
- `.agents/plans/2026-04-24-flir-training-frame-capture.md`
- `.agents/PLANS.md`

## Contracts to preserve

- Do not change the production FLIR -> DLCLive -> ZMQ stream.
- Do not change `/tmp/EyeTrack` CSV or metadata output contracts.
- Do not change runtime model-path handling under `models/`.
- Save raw camera frames only; preview overlay, scaling, and auto-contrast are display-only.
- Restore original FLIR camera settings on exit by default.

## Planned edits

- Add `capture_flir_training_frames.py` beside the existing FLIR camera diagnostics.
- Reuse existing `FLIRCam.py` camera configuration and restore helpers.
- Default to production-like settings: `Mono8`, sensor ROI `0 0 640 480`,
  60 Hz frame rate, 6000 us exposure, gain auto off, gain 0 dB.
- Support hybrid preview/manual save, autosave every N frames, and headless
  timed capture with `--no-preview`.
- Write one timestamped session folder containing `frames/*.png`,
  `manifest.csv`, and `metadata.json`.
- Add an SSH/X11 wrapper so the behavior computer can open the capture preview
  on the eye-tracking computer and save images through the forwarded window.
- Add a focused instructional Markdown file for the forwarded training-frame
  capture workflow, including commands, output layout, verification, and
  troubleshooting.
- Document the new utility in `DeepLabCut/Tests/README.md`.
- Document the forwarded capture workflow in `DeepLabCut/SSH_X11_FORWARDING_POPOS.md`.

## Validation

- `python3 -m py_compile DeepLabCut/Tests/capture_flir_training_frames.py`
  passed.
- `python3 DeepLabCut/Tests/capture_flir_training_frames.py --help`
  passed.
- `python3 DeepLabCut/ToMatlab/check_pyspin_camera.py` was blocked because
  local `python3` does not have `PySpin`.
- `python3 DeepLabCut/Tests/capture_flir_training_frames.py --output-dir ~/Desktop/EyeTrackTrainingFrames --seconds 2 --save-every 10 --no-preview`
  was blocked because local `python3` does not have `cv2`.
- `bash -n DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh`
  passed.
- `DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh --help`
  passed.
- `test -f DeepLabCut/ToMatlab/ssh_x11/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`
  passed.
- `git diff --check` passed.

## Implementation summary

- Added the FLIR training-frame capture script with lazy camera-module imports,
  Desktop output defaults, raw PNG writing, CSV manifest writing, metadata JSON
  writing, and clean missing-module reporting.
- Added `open_training_capture_over_ssh.sh` for launching the capture preview
  over `ssh -Y` from the behavior computer.
- Added `FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md` as the focused user-facing
  instruction file for the X11 image recording workflow.
- Updated the tests README with default preview usage and headless timed capture
  usage.
- Updated the SSH/X11 guide with the forwarded training-frame capture workflow.
- Hardware capture remains to be verified in the EyeTrack FLIR/PySpin runtime
  environment.
