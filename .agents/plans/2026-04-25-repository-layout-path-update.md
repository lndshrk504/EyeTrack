# Repository Layout Path Update

- Status: Implemented
- Created: 2026-04-25
- Last updated: 2026-04-25

## Goal

Update path references after the repository was reorganized so scripts,
wrapper commands, validation instructions, and README files point at the new
folder layout.

## Active paths

- `Stream-DeepLabCut/`
- `Cam-Tests/`
- `Train-Test-Model/`
- `Docs/`
- `ssh_x11/`
- `Models/`
- `README.md`
- `AGENTS.md`
- `.agents/skills/`
- `.agents/plans/`
- `.agents/PLANS.md`

## Contracts to preserve

- Preserve the documented ZMQ default endpoint `tcp://127.0.0.1:5555`.
- Preserve `/tmp/EyeTrack` as the production CSV and metadata default output
  root.
- Preserve CSV columns, metadata JSON keys, ZMQ payload fields, coordinate
  frame semantics, crop semantics, timing fields, and MATLAB-visible sample
  structure.
- Keep model blobs out of git.
- Do not restore deleted legacy or bootstrap files unless explicitly requested.

## Planned edits

- Update runtime and smoke-test model path defaults from the old lowercase
  model folder to `Models/`.
- Update camera smoke tests to import the active runtime modules from
  `Stream-DeepLabCut/`.
- Update SSH/X11 wrapper remote `cd` targets and process patterns.
- Update root, runtime, camera-test, training, model, and workflow READMEs.
- Update agent instructions and validation references to the new layout.
- Add `Models/` ignore rules while keeping the README tracked.

## Validation

- Stale old-layout `rg` check returned no matches in the active docs, scripts,
  and agent records.
- `python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py Cam-Tests/smoke_dlc_flir_inference.py Cam-Tests/capture_flir_training_frames.py`
  passed.
- `python3 -m py_compile Stream-DeepLabCut/*.py Cam-Tests/*.py Train-Test-Model/*.py`
  passed.
- `python3 Stream-DeepLabCut/run_eye_stream_production.py --help`
  passed.
- `python3 Cam-Tests/capture_flir_training_frames.py --help`
  passed.
- `python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --help`
  passed.
- `bash -n ssh_x11/*.sh Stream-DeepLabCut/*.sh`
  passed.
- SSH/X11 wrapper help checks passed for `open_alignment_preview_over_ssh.sh`,
  `open_training_capture_over_ssh.sh`, `start_eye_stream_over_ssh.sh`,
  `stop_eye_stream_over_ssh.sh`, `eye_stream_status_over_ssh.sh`,
  `test_x11_forwarding_over_ssh.sh`, and `setup_eye_host_ssh_x11.sh`.
- `Stream-DeepLabCut/setup_two_computer_eye_link.sh --help`
  passed.
- `git diff --check`
  passed.

## Implementation summary

- Updated production launcher and FLIR/DLCLive smoke-test model discovery to
  use `Models/`.
- Updated the FLIR/DLCLive smoke test to import runtime modules from
  `Stream-DeepLabCut/`.
- Updated SSH/X11 wrappers to run scripts from `Cam-Tests/` and
  `Stream-DeepLabCut/`, and updated stop-process patterns accordingly.
- Updated root, runtime, camera-test, training, model, SSH/X11, two-computer,
  and FLIR training-capture documentation for the reorganized layout.
- Updated `AGENTS.md`, repo skills, and existing FLIR plan records so future
  validation and implementation instructions point at the new layout.
- Added `Models/` ignore rules while preserving the model README.
- Hardware camera, X11 forwarding, MATLAB runtime, and live ZMQ receive tests
  remain unverified in this local validation pass.
