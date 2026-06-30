# Model Path And Doc Link Casing

- Status: Implemented
- Created: 2026-06-30
- Last updated: 2026-06-30

## Goal

Align the active documentation, launcher defaults, and validation helpers with the current Linux checkout, where runtime model artifacts live under `models/` and the tracked SSH/X11 training-capture docs use their current filenames.

## Active paths

- `README.md`
- `Docs/`
- `Cam-Tests/README.md`
- `Cam-Tests/smoke_dlc_flir_inference.py`
- `Stream-DeepLabCut/run_eye_stream_production.py`
- `Train-Test-Model/`
- `models/README.md`
- `.agents/skills/deeplabcut-live-runtime/SKILL.md`

## Contracts to preserve

- Do not move, rename, rewrite, or commit model artifacts under `models/`.
- Preserve the default ZMQ address `tcp://127.0.0.1:5555`.
- Preserve default streamer output under `/tmp/EyeTrack`.
- Do not change timing, FPS, coordinate frame, crop, CSV columns, metadata JSON keys, or ZMQ payload fields.
- Keep explicit `--model-path` overrides working.

## Planned edits

- Fix broken Markdown links to the currently tracked SSH/X11 and training-capture docs.
- Replace active `Models/` examples and defaults with `models/`.
- Update runtime/model validation default discovery to search `models/`.
- Keep historical implementation-log entries unchanged.

## Validation

- `python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py Cam-Tests/smoke_dlc_flir_inference.py Train-Test-Model/validate_models_folder.py`
- `python3 Stream-DeepLabCut/run_eye_stream_production.py --help`
- `python3 Train-Test-Model/validate_models_folder.py --help`
- Static scan for stale active `Models/` and broken doc-link targets.

## Implementation summary

Updated the active docs, README files, live-runtime skill guidance, streamer launcher default model path, FLIR/DLCLive smoke-test default discovery, and camera-free model validation default discovery to use `models/`. Fixed the broken Markdown links that still referenced the old SSH/X11 and training-capture filenames. No model artifacts were moved or edited.

Validation passed:

- `python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py Cam-Tests/smoke_dlc_flir_inference.py Train-Test-Model/validate_models_folder.py`
- `python3 Stream-DeepLabCut/run_eye_stream_production.py --help`
- `python3 Train-Test-Model/validate_models_folder.py --help`
- `/home/wbs/miniforge3/envs/dlclivegui/bin/python Cam-Tests/smoke_dlc_flir_inference.py --help`
- default model-path checks for `run_eye_stream_production.py`, `smoke_dlc_flir_inference.py`, and `validate_models_folder.py`
- static stale-reference scan over active docs/code
- `git diff --check`
