# EyeTrack Master Implementation Log

This file is the append-only master record of implemented plan-backed changes in this repository.

Working feature plans live under `.agents/plans/`. Use those files for planning, iteration, and implementation notes. Use this file only after a planned change has been implemented.

## Workflow
- During planning, create or update exactly one working feature plan file under `.agents/plans/`.
- Keep refining the same working plan file until the plan is ready and the change is implemented.
- After implementation, update the working plan status and append a new entry to the log below.

## Entry Template

```md
## YYYY-MM-DD - Feature Title
- Plan file: `.agents/plans/YYYY-MM-DD-short-feature-title.md`
- Summary:
- Changed files:
- Validation:
- Follow-ups:
```

## Log

## 2026-04-22 - Planning Records Workflow
- Plan file: `.agents/plans/2026-04-22-planning-records-workflow.md`
- Summary: Added a repo rule and skill for maintaining one stable per-feature plan file during planning and one append-only master implementation log after implementation.
- Changed files: `AGENTS.md`, `.codex/agents/explorer.toml`, `.codex/agents/worker.toml`, `.agents/PLANS.md`, `.agents/plans/2026-04-22-planning-records-workflow.md`, `.agents/skills/feature-plan-records/SKILL.md`
- Validation: `rg` checks confirmed the new skill and `.agents/plans/` workflow are referenced from `AGENTS.md`; TOML parsing confirmed `.codex/agents/explorer.toml` and `.codex/agents/worker.toml` remained valid.
- Follow-ups: Use the new workflow for the next planned feature or behavior change so the pattern becomes the default repository habit.

## 2026-04-24 - FLIR Training Frame Capture
- Plan file: `.agents/plans/2026-04-24-flir-training-frame-capture.md`
- Summary: Added a FLIR/PySpin raw-frame capture utility for collecting DeepLabCut retraining images under `~/Desktop/EyeTrackTrainingFrames`, with preview/manual save, autosave, headless timed capture, manifest CSV, and metadata JSON output.
- Changed files: `Cam-Tests/capture_flir_training_frames.py`, `Cam-Tests/README.md`, `.agents/plans/2026-04-24-flir-training-frame-capture.md`, `.agents/PLANS.md`
- Validation: `python3 -m py_compile Cam-Tests/capture_flir_training_frames.py` passed; `python3 Cam-Tests/capture_flir_training_frames.py --help` passed; camera visibility and smoke capture were blocked in local `python3` because `PySpin` and `cv2` are not installed.
- Follow-ups: Run the documented headless smoke capture in the EyeTrack FLIR/PySpin environment and inspect the generated PNGs, `manifest.csv`, and `metadata.json`.

## 2026-04-24 - SSH/X11 FLIR Training Capture
- Plan file: `.agents/plans/2026-04-24-flir-training-frame-capture.md`
- Summary: Added an SSH/X11 wrapper and focused instructional Markdown file for launching the FLIR training-frame capture preview from the behavior computer while saving raw training images on the eye-tracking computer.
- Changed files: `ssh_x11/open_training_capture_over_ssh.sh`, `Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`, `Docs/SSH_X11_FORWARDING_POPOS.md`, `Cam-Tests/README.md`, `.agents/plans/2026-04-24-flir-training-frame-capture.md`, `.agents/PLANS.md`
- Validation: `bash -n ssh_x11/open_training_capture_over_ssh.sh` passed; `ssh_x11/open_training_capture_over_ssh.sh --help` passed; `python3 -m py_compile Cam-Tests/capture_flir_training_frames.py` passed; `python3 Cam-Tests/capture_flir_training_frames.py --help` passed; `test -f Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md` passed; `git diff --check` passed.
- Follow-ups: Run `./open_training_capture_over_ssh.sh --host wbs@10.55.0.1 -- --auto-contrast --scale 0.5` from the behavior computer and confirm saved images appear under the eye-tracking computer's `~/Desktop/EyeTrackTrainingFrames/`.

## 2026-04-25 - Repository Layout Path Update
- Plan file: `.agents/plans/2026-04-25-repository-layout-path-update.md`
- Summary: Updated path-sensitive runtime defaults, smoke tests, SSH/X11 wrappers, README files, and agent validation records after the repository was reorganized into `Stream-DeepLabCut/`, `Cam-Tests/`, `Train-Test-Model/`, `Docs/`, `ssh_x11/`, and `Models/`.
- Changed files: `Stream-DeepLabCut/run_eye_stream_production.py`, `Cam-Tests/smoke_dlc_flir_inference.py`, `ssh_x11/open_alignment_preview_over_ssh.sh`, `ssh_x11/open_training_capture_over_ssh.sh`, `ssh_x11/start_eye_stream_over_ssh.sh`, `ssh_x11/stop_eye_stream_over_ssh.sh`, `.gitignore`, `README.md`, `AGENTS.md`, `Docs/SSH_X11_FORWARDING_POPOS.md`, `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`, `Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`, `Docs/README_eye_stream.md`, `Stream-DeepLabCut/README.md`, `Cam-Tests/README.md`, `Train-Test-Model/train-README.md`, `Train-Test-Model/test-README.md`, `Models/README.md`, `.agents/skills/deeplabcut-environment-validation/SKILL.md`, `.agents/skills/deeplabcut-live-runtime/SKILL.md`, `.agents/skills/deeplabcut-matlab-bridge/SKILL.md`, `.agents/plans/2026-04-24-flir-training-frame-capture.md`, `.agents/plans/2026-04-25-repository-layout-path-update.md`, `.agents/PLANS.md`
- Validation: Stale old-layout `rg` check returned no matches; `python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py Cam-Tests/smoke_dlc_flir_inference.py Cam-Tests/capture_flir_training_frames.py` passed; `python3 -m py_compile Stream-DeepLabCut/*.py Cam-Tests/*.py Train-Test-Model/*.py` passed; `python3 Stream-DeepLabCut/run_eye_stream_production.py --help` passed; `python3 Cam-Tests/capture_flir_training_frames.py --help` passed; `python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --help` passed; `bash -n ssh_x11/*.sh Stream-DeepLabCut/*.sh` passed; SSH/X11 wrapper help checks passed; `Stream-DeepLabCut/setup_two_computer_eye_link.sh --help` passed; `git diff --check` passed.
- Follow-ups: Run the hardware-dependent checks on the Linux eye-tracking machine: `python3 Stream-DeepLabCut/check_pyspin_camera.py`, `python3 Cam-Tests/TestSpin.py --camera-index 0 --sensor-roi 0 0 640 480 --frames 120`, the SSH/X11 forwarded capture workflow, and the live MATLAB receive test with the streamer running.

## 2026-04-25 - README And Docs Accuracy Cleanup
- Plan file: `.agents/plans/2026-04-25-doc-readme-accuracy-cleanup.md`
- Summary: Tightened README and Docs guidance after the repository layout update by normalizing interpreter examples, clarifying host/path placeholders, documenting the receiver-backed BehaviorBox ingest path, adding startup-order guidance, and tying training/testing docs back to the `Models/` runtime layout.
- Changed files: `README.md`, `Cam-Tests/README.md`, `Docs/README_eye_stream.md`, `Docs/SSH_X11_FORWARDING_POPOS.md`, `Docs/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`, `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`, `Train-Test-Model/train-README.md`, `Train-Test-Model/test-README.md`, `.agents/plans/2026-04-25-doc-readme-accuracy-cleanup.md`, `.agents/PLANS.md`
- Validation: `rg -n "EyeTrack/DeepLabCut|DeepLabCut/ToMatlab|bootstrap_eye_track|legacy/iRecHS2" README.md Docs Cam-Tests Stream-DeepLabCut Train-Test-Model Models` returned no matches; `rg -n "wbs@10\.55\.0\.1|/home/wbs" Docs README.md Cam-Tests Train-Test-Model` returned no matches; `git diff --check` passed.
- Follow-ups: Run the live SSH/X11 and two-computer commands on the actual Linux machines before treating those workflows as hardware-validated.

## 2026-04-25 - Single-Computer Eye Tracking Quickstart
- Plan file: `.agents/plans/2026-04-25-single-computer-eye-tracking-quickstart.md`
- Summary: Added a quickstart for running the FLIR/DLCLive streamer, Python receiver, MATLAB, and BehaviorBox on the same computer using localhost ZMQ and the receiver HTTP API.
- Changed files: `Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`, `README.md`, `Docs/README_eye_stream.md`, `.agents/plans/2026-04-25-single-computer-eye-tracking-quickstart.md`, `.agents/PLANS.md`
- Validation: `rg -n "SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART" README.md Docs/README_eye_stream.md Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md` found the new links; `rg -n "wbs@|/home/wbs|--address tcp://10\.55\.0\.1:5555|--address tcp://10\.55\.0\.2:5555" Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md` returned no matches; `git diff --check` passed.
- Follow-ups: Run the one-computer sequence on the real FLIR/MATLAB machine and confirm BehaviorBox session saves include eye-tracking records.

## 2026-04-28 - Native Mac DLC Model Validation
- Plan file: `.agents/plans/2026-04-28-native-mac-dlc-model-validation.md`
- Summary: Created a native osx-arm64 `DLC` conda environment for Mac-side DeepLabCut validation, added a camera-free DLCLive model validation script, and documented the no-FLIR still-image workflow.
- Changed files: `Train-Test-Model/validate_models_folder.py`, `Train-Test-Model/test-README.md`, `.agents/plans/2026-04-28-native-mac-dlc-model-validation.md`, `.agents/PLANS.md`
- Validation: `python3 -m py_compile Train-Test-Model/validate_models_folder.py`; `python3 Train-Test-Model/validate_models_folder.py --help`; `conda run -n DLC python -c "import tensorflow as tf; print('TF', tf.__version__); print(tf.reduce_sum(tf.random.normal([8, 8])))"`; `conda run -n DLC python -c "import deeplabcut; print('DLC', deeplabcut.__version__); import dlclive; print('DLCLive import OK')"`; `conda run -n DLC python Train-Test-Model/train_dlc_eye_model.py --help`; `conda run -n DLC python Train-Test-Model/run_dlc_image_test.py --help`; `conda run -n DLC python Train-Test-Model/validate_models_folder.py --model-path Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 --output-dir /tmp/EyeTrack/model_validation`; `conda run -n DLC python Train-Test-Model/validate_models_folder.py --model-path Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 --image-dir /tmp/EyeTrack/model_validation_input --frametype .png --output-dir /tmp/EyeTrack/model_validation_with_image`.
- Follow-ups: Use real eye still images for visual quality validation. Keep FLIR/PySpin/live timing validation on the Linux eye-tracking computer. `tensorflow-metal` is mechanically installable on this Mac but is not expected to accelerate the bundled DLCLive TensorFlow V1 graph path because Apple documents V1 TensorFlow networks as unsupported.

## 2026-04-28 - Exported Model Prelabels
- Plan file: `.agents/plans/2026-04-28-exported-model-prelabels.md`
- Summary: Added a converter that turns flattened DLCLive predictions from the bundled exported model into DLC-compatible `CollectedData_<scorer>.h5`/`.csv` draft labels for extracted frame folders, with safe overwrite behavior and bodypart/order mapping for the legacy `RVupil` spelling.
- Changed files: `Train-Test-Model/dlclive_predictions_to_dlc_labels.py`, `Train-Test-Model/train-README.md`, `.agents/plans/2026-04-28-exported-model-prelabels.md`, `.agents/PLANS.md`
- Validation: `python3 -m py_compile Train-Test-Model/dlclive_predictions_to_dlc_labels.py`; `python3 Train-Test-Model/dlclive_predictions_to_dlc_labels.py --help`; `conda run -n DLC python Train-Test-Model/dlclive_predictions_to_dlc_labels.py --help`; temporary conversion using `/tmp/EyeTrack/model_validation_with_image/predictions.csv` wrote `CollectedData_Will.h5` and pandas confirmed shape `(1, 16)`, row index `labeled-data/session1/synthetic_eye.png`, and DLC MultiIndex columns `scorer/bodyparts/coords`; `git diff --check`.
- Follow-ups: Run the full prelabel workflow on real extracted eye frames, open the generated `CollectedData` in the DLC/napari labeler, correct all draft points, and run `deeplabcut.check_labels` before training.
