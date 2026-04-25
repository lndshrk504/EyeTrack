---
name: deeplabcut-live-runtime
description: Use this skill when a task changes the live DeepLabCut runtime in EyeTrack, including FLIR capture, DLCLive inference, overlay/display, CSV or metadata output, launcher scripts, SSH runtime helpers, or runtime model-path handling.
---

# DeepLabCut live runtime

## Goal

Make live runtime changes without silently breaking capture, inference, transport, or runtime outputs.

## Required workflow

1. Identify the changed runtime stage before editing.
   Choose one or more of:
   - acquisition
   - preprocess
   - inference
   - overlay/display
   - serialization
   - launcher/runtime wiring

2. Map the exact execution path.
   Name:
   - the entrypoint script
   - the touched functions
   - downstream consumers of the changed output
   - the narrowest real validation command

3. Call out behavior changes before editing.
   Explicitly state whether the change can alter:
   - timing, FPS, or latency
   - coordinate frame or crop semantics
   - display behavior
   - CSV columns or metadata JSON keys
   - default output paths under `/tmp/EyeTrack`
   - runtime model-path resolution under `Models/`

4. Preserve existing runtime contracts unless the task explicitly changes them.
   Keep stable by default:
   - the documented ZMQ default address
   - the sample-vs-metadata split
   - CSV and metadata sidecar pairing
   - explicit model-path handling

5. Choose the narrowest relevant validation.
   Typical checks:
   - launcher CLI surface: `python3 Stream-DeepLabCut/run_eye_stream_production.py --help`
   - syntax-only check when imports or hardware are unavailable: `python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py`
   - environment inventory: `python3 Cam-Tests/VerCheck.py --strict`
   - FLIR + DLCLive timing: `python3 Cam-Tests/smoke_dlc_flir_inference.py --model-path <exported_model_dir> --model-preset yanglab-pupil8 --model-type base --camera-index 0 --sensor-roi 0 0 640 480 --frames 120`

6. In the handoff, report:
   - changed runtime stage
   - files and functions touched
   - validation command(s)
   - expected output differences
   - what remains unverified because of missing hardware or environment

## Do not

- do not silently change coordinate frames, crop semantics, timestamp units, or output paths
- do not commit model blobs or `/tmp/EyeTrack` runtime outputs
- do not move full training/export workflow into this skill; until `deeplabcut-model-lifecycle` exists, only runtime-facing model-path behavior belongs here
