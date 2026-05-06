# AGENTS.md

## Repository Profile
EyeTrack is a standalone eye-tracking repository extracted from `BehaviorBox`. The active workflow lives in `Stream-DeepLabCut/`, `Cam-Tests/`, `Train-Test-Model/`, `ssh_x11/`, `Docs/`, and `models/`.

Python owns the live capture, DLCLive inference, transport, SSH/X11 wrappers, training-image capture, and most validation entrypoints. MATLAB is limited here to receive-side bridge/demo code. Model artifacts under `models/` are runtime inputs and are intentionally not tracked in git.

## Working Agreements
- Before editing, map the real execution path and name the files, functions, scripts, and tests involved.
- For MATLAB work, inspect package folders (`+pkg`), class folders (`@Class`), `private/`, and any `startup.m` or `addpath` logic before changing behavior. This repo no longer has a MATLAB bootstrap helper at the root.
- Prefer read-only exploration first, implementation second, review last.
- Make the smallest defensible change first. Do not do drive-by cleanup.
- Treat timing, FPS, coordinate-frame, crop, CSV-column, metadata-JSON, ZMQ-field, saved-array, and tolerance changes as behavior changes. Call out expected differences before editing.
- Run the narrowest relevant validation after every meaningful edit. Report the exact command, a short result summary, and what remains unverified.
- Never install packages, change environments, edit model blobs or large data artifacts, or rewrite directory layouts unless explicitly asked.
- End every task with: changed files, validation run, remaining risks, next best step.

## Patch Tool Path Discipline
Before the first `apply_patch` call in a task, or whenever the working directory is ambiguous, confirm the current working directory and target file with `pwd` and `rg --files` or `ls`. In `*** Update File:`, `*** Add File:`, and `*** Delete File:` lines, use a path that is either relative to that current working directory or a true absolute path beginning with `/`.

Do not use patch filenames such as `home/wbs/Desktop/...`; without the leading slash, the patch tool treats that as relative and duplicates it under the current directory. Do not paste markdown link targets or display-only file references into patch headers.

Keep patches small and anchored on recently read context. If `apply_patch` reports "Failed to find expected lines", reread the target section and retry with a narrower hunk instead of resubmitting the same patch.

## Sub-Agent Settings
- Use `gpt-5.4` with `xhigh` reasoning for sub-agents by default, including `explorer`, `reviewer`, `worker`, and any generic/default sub-agent.

## Mandatory Skill Usage
- Use `$feature-plan-records` when the user asks for a plan, when proposing or refining a new feature or nontrivial behavior change, or when implementing a plan-backed change. Skill path: `.agents/skills/feature-plan-records/SKILL.md`
- Use `$deeplabcut-live-runtime` for live capture, DLCLive inference, overlay/display, CSV or sidecar metadata, runner scripts, SSH launch helpers, and runtime model-path wiring. Skill path: `.agents/skills/deeplabcut-live-runtime/SKILL.md`
- Use `$deeplabcut-matlab-bridge` for any Python/MATLAB boundary work, including `matlab_zmq_bridge.py`, `run_matlab_eye_receive_test.py`, `receive_eye_stream_demo.m`, `run_eye_stream_receive_test.m`, and ZMQ payload or metadata-contract changes. Skill path: `.agents/skills/deeplabcut-matlab-bridge/SKILL.md`
- Use `$deeplabcut-environment-validation` for `environment.yaml`, `Cam-Tests/*`, `Stream-DeepLabCut/check_pyspin_camera.py`, camera/backend validation, dependency checks, and SSH/X11 troubleshooting. Skill path: `.agents/skills/deeplabcut-environment-validation/SKILL.md`
- If a task changes timing, numerical outputs, coordinate frames, CSV columns, metadata schema, or ZMQ fields, explicitly call out the expected behavior change before editing.
- A future `deeplabcut-model-lifecycle` skill is not implemented yet. Until then, exported-model placement and runtime model-path conventions stay under `$deeplabcut-live-runtime`.

## Planning Records
- `.agents/PLANS.md` is the master implementation log. Append to it only after a plan-backed change has been implemented.
- Working feature plans live under `.agents/plans/` using one stable file per feature or change, named `YYYY-MM-DD-short-feature-title.md`.
- When the user asks for a plan, create or update exactly one working feature plan file for that feature or change and keep iterating the same file until it is ready for implementation.
- Give each working feature plan a unique human-readable title that matches the feature or change. Keep the file path stable while the work is being refined and implemented.
- When a feature or planned behavior change is implemented, update the working feature plan with final status and append a dated summary entry to `.agents/PLANS.md`.
- If the task is multi-file, cross-language, touches multiple directories, crosses a data-format boundary, or is likely to change scientific outputs, create or update the working feature plan before broad edits.

## Repo Layout Checklist
Before broad edits, inspect the real equivalents in this repo rather than assuming the old `BehaviorBox` layout:
- Active runtime Python: `Stream-DeepLabCut/dlc_eye_streamer.py`, `run_eye_stream_production.py`, `matlab_zmq_bridge.py`, `run_matlab_eye_receive_test.py`
- Active MATLAB bridge/demo files: `Stream-DeepLabCut/receive_eye_stream_demo.m`, `run_eye_stream_receive_test.m`
- Validation scripts: `Cam-Tests/VerCheck.py`, `CheckReqs.py`, `TestSpin.py`, `GSTOCV.py`, `FLIRCam.py`, `smoke_dlc_flir_inference.py`
- Ops and workflow docs: `README.md`, `Stream-DeepLabCut/README.md`, `Docs/README_eye_stream.md`, `Cam-Tests/README.md`, `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`, `Docs/SSH_X11_forwarding_PopOS.md`
- Planning records: `.agents/PLANS.md`, `.agents/plans/`, `.agents/skills/feature-plan-records/SKILL.md`
- Runtime model landing zone: `models/`

For MATLAB work, also inspect any `+pkg`, `@Class`, `private/`, and startup/addpath logic before changing behavior. Do not assume a root `startup.m` configures this repo for you.

## MATLAB and Python Operating Rules
- Python owns live capture, DLCLive inference, CSV/metadata serialization, and the ZMQ publisher. MATLAB owns receive-side behavior and MATLAB-visible record structure.
- Do not silently change coordinate-frame semantics, crop behavior, timestamp units, field names, sample-vs-metadata split, CSV column names, sidecar keys, or default output paths.
- Preserve the documented default ZMQ endpoint `tcp://127.0.0.1:5555` and default output directory `/tmp/EyeTrack` unless the task explicitly changes those contracts.
- Keep model-path handling deterministic. Do not change `models/` placement rules or commit model blobs unless explicitly asked.
- Keep MATLAB path setup explicit. Do not add `addpath(genpath(...))` unless the repo already depends on it.
- If MATLAB and Python disagree on shapes, dtypes, indexing, coordinate frame, or schema, stop and explain the mismatch before forcing a fix.
- Unless the task explicitly targets another OS, treat Linux as the primary runtime target and call out any macOS- or Windows-specific validation separately.

## Local Validation
Run the narrowest matching checks, in this order when relevant:

1. For launcher CLI or argument-surface changes:
   `python3 Stream-DeepLabCut/run_eye_stream_production.py --help`
2. For MATLAB receive-test CLI or entrypoint changes:
   `python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --help`
3. For import-free Python syntax checks:
   `python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py`
4. For runtime environment inventory:
   `python3 Cam-Tests/VerCheck.py`
   or
   `python3 Cam-Tests/VerCheck.py --strict`
5. For TensorFlow build metadata checks:
   `python3 Cam-Tests/CheckReqs.py`
6. For PySpin camera enumeration:
   `python3 Stream-DeepLabCut/check_pyspin_camera.py`
7. For FLIR/PySpin camera smoke:
   `python3 Cam-Tests/TestSpin.py --camera-index 0 --sensor-roi 0 0 640 480 --frames 120`
8. For OpenCV/GStreamer/USB capture smoke:
   `python3 Cam-Tests/GSTOCV.py --backend usb --source 0 --width 640 --height 480 --fps 30 --frames 120`
   or
   `python3 Cam-Tests/GSTOCV.py --backend gstreamer --width 640 --height 480 --fps 120 --frames 120`
9. For FLIR full-frame preview:
   `python3 Cam-Tests/FLIRCam.py --camera-index 0 --frames 120`
10. For FLIR + DLCLive timing:
   `python3 Cam-Tests/smoke_dlc_flir_inference.py --model-path <exported_model_dir> --model-preset yanglab-pupil8 --model-type base --camera-index 0 --sensor-roi 0 0 640 480 --frames 120`
11. For live MATLAB bridge validation with the Python streamer already running:
   `python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --duration 10`
   or
   `matlab -batch "cd('/Users/willsnyder/Desktop/BehaviorBox/EyeTrack'); run('Stream-DeepLabCut/receive_eye_stream_demo.m');"`

There is no repo-wide Python test runner or coverage gate today. Do not claim broader automated coverage than you actually ran.

## Coding Style and Change Scope
Follow adjacent file style. Prefer spaces over tabs. Python in `Stream-DeepLabCut/` and `Cam-Tests/` uses typed helpers, `argparse`, and small focused functions; match that style rather than reformatting whole files. MATLAB changes should preserve explicit path handling and avoid broad path hacks.

Add focused validation scripts near the subsystem you changed if a reusable smoke test is missing. For hardware-facing work, note the device, OS, and expected behavior you validated.

## Data and Configuration Hygiene
Do not commit generated CSV files, JSON sidecars, `/tmp/EyeTrack` outputs, model blobs, `.mat` receive-test artifacts, or transient environment outputs. Review SSH/X11 and camera helper scripts carefully before changing any remote-host assumptions.

## Definition of Done
A task is done only when:
- the diff is scoped
- the target behavior is validated with Python and/or MATLAB as appropriate
- timing, coordinate-frame, schema, and output-path changes are called out explicitly
- follow-up work is listed if anything remains unresolved

## Review Guidelines
- Flag timing regressions, silent coordinate-frame drift, field-name drift, CSV/metadata schema drift, path brittleness, hidden environment coupling, and missing validation as high priority.
- Treat missing validation for changed runtime or bridge code as a real issue, not a paperwork issue.
- For camera and environment reviews, flag unverified hardware assumptions, backend drift, dependency drift, SSH/X11 coupling, and changes that would only work in one local environment without being documented.
