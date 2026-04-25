# Single-Computer Eye Tracking Quickstart

- Status: Implemented
- Created: 2026-04-25
- Last updated: 2026-04-25

## Goal

Add a quickstart document for running the Python FLIR/DLCLive streamer, Python
receiver, MATLAB, and BehaviorBox on one computer using localhost transport.

## Active paths

- `Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Docs/README_eye_stream.md`
- `README.md`
- `.agents/PLANS.md`
- Runtime path documented but not changed:
  - `Stream-DeepLabCut/run_eye_stream_production.py`
  - `Stream-DeepLabCut/run_eye_receiver_service.py`
  - `Stream-DeepLabCut/run_matlab_eye_receive_test.py`
  - `Stream-DeepLabCut/behavior_eye_receiver.py`
  - `/Users/willsnyder/Desktop/BehaviorBox/BehaviorBoxEyeTrack.m`
  - `/Users/willsnyder/Desktop/BehaviorBox/BehaviorBoxWheel.m`

## Contracts to preserve

- No runtime code changes.
- Preserve the localhost ZMQ default `tcp://127.0.0.1:5555`.
- Preserve the receiver API default `http://127.0.0.1:8765`.
- Preserve `/tmp/EyeTrack` streamer output behavior.
- Preserve MATLAB-visible schema, CSV columns, metadata keys, coordinate frames,
  timestamps, and model-path resolution.

## Planned edits

- Add a new single-computer quickstart under `Docs/`.
- Link it from the root README and stream contract doc.
- Record the change in the planning records.

## Validation

- `rg -n "SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART" README.md Docs/README_eye_stream.md Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `rg -n "wbs@|/home/wbs|--address tcp://10\.55\.0\.1:5555|--address tcp://10\.55\.0\.2:5555" Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `git diff --check`

## Implementation summary

- Added the single-computer quickstart.
- Linked the quickstart from `README.md` and `Docs/README_eye_stream.md`.
- Appended the implemented change to `.agents/PLANS.md`.
