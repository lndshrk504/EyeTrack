# README And Docs Accuracy Cleanup

- Status: Implemented
- Created: 2026-04-25
- Last updated: 2026-04-25

## Goal

Rectify documentation discrepancies found after the repository layout cleanup, especially command consistency, host/path assumptions, active receiver guidance, SSH/X11 workflow details, training-frame capture defaults, and model-placement notes.

## Active paths

- `README.md`
- `Cam-Tests/README.md`
- `Docs/README_eye_stream.md`
- `Docs/SSH_X11_FORWARDING_POPOS.md`
- `Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`
- `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Train-Test-Model/train-README.md`
- `Train-Test-Model/test-README.md`
- `.agents/PLANS.md`

## Contracts to preserve

- No runtime code changes.
- No changes to ZMQ payloads, CSV schemas, metadata JSON schemas, coordinate-frame semantics, camera defaults, model blobs, or `/tmp/EyeTrack` behavior.
- Preserve the documented default ZMQ endpoint `tcp://127.0.0.1:5555` for single-machine/default use and the explicit `tcp://10.55.0.1:5555` address for two-computer use.
- Preserve `~/Desktop/EyeTrackTrainingFrames` as the default FLIR training-image output root.

## Planned edits

- Normalize examples around `python3` while documenting that an active conda environment may expose `python`.
- Make SSH/two-computer examples clearer about placeholder host, path, and user values.
- Clarify that `run_eye_receiver_service.py` is the active BehaviorBox ingestion path and MATLAB consumes finalized chunks through the receiver API.
- Add concise startup-order and cwd guidance where command blocks depend on it.
- Tie training/testing docs back to the `Models/` runtime placement convention.

## Validation

- `rg -n "EyeTrack/DeepLabCut|DeepLabCut/ToMatlab|bootstrap_eye_track|legacy/iRecHS2" README.md Docs Cam-Tests Stream-DeepLabCut Train-Test-Model Models`
- `rg -n "wbs@10\.55\.0\.1|/home/wbs" Docs README.md Cam-Tests Train-Test-Model`
- `git diff --check`

## Implementation summary

- Updated public Markdown docs for interpreter consistency, host/path assumptions, active receiver flow, SSH/X11 capture details, and model placement.
- Appended the implemented change to `.agents/PLANS.md`.
