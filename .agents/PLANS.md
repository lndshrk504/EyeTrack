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
- Changed files: `DeepLabCut/Tests/capture_flir_training_frames.py`, `DeepLabCut/Tests/README.md`, `.agents/plans/2026-04-24-flir-training-frame-capture.md`, `.agents/PLANS.md`
- Validation: `python3 -m py_compile DeepLabCut/Tests/capture_flir_training_frames.py` passed; `python3 DeepLabCut/Tests/capture_flir_training_frames.py --help` passed; camera visibility and smoke capture were blocked in local `python3` because `PySpin` and `cv2` are not installed.
- Follow-ups: Run the documented headless smoke capture in the EyeTrack FLIR/PySpin environment and inspect the generated PNGs, `manifest.csv`, and `metadata.json`.

## 2026-04-24 - SSH/X11 FLIR Training Capture
- Plan file: `.agents/plans/2026-04-24-flir-training-frame-capture.md`
- Summary: Added an SSH/X11 wrapper and focused instructional Markdown file for launching the FLIR training-frame capture preview from the behavior computer while saving raw training images on the eye-tracking computer.
- Changed files: `DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh`, `DeepLabCut/ToMatlab/ssh_x11/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md`, `DeepLabCut/SSH_X11_FORWARDING_POPOS.md`, `DeepLabCut/Tests/README.md`, `.agents/plans/2026-04-24-flir-training-frame-capture.md`, `.agents/PLANS.md`
- Validation: `bash -n DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh` passed; `DeepLabCut/ToMatlab/ssh_x11/open_training_capture_over_ssh.sh --help` passed; `python3 -m py_compile DeepLabCut/Tests/capture_flir_training_frames.py` passed; `python3 DeepLabCut/Tests/capture_flir_training_frames.py --help` passed; `test -f DeepLabCut/ToMatlab/ssh_x11/FLIR_TRAINING_CAPTURE_OVER_SSH_X11.md` passed; `git diff --check` passed.
- Follow-ups: Run `./open_training_capture_over_ssh.sh --host wbs@10.55.0.1 -- --auto-contrast --scale 0.5` from the behavior computer and confirm saved images appear under the eye-tracking computer's `~/Desktop/EyeTrackTrainingFrames/`.
