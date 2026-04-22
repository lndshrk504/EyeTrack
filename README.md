# EyeTrack

Standalone eye-tracking repo extracted from `BehaviorBox`.

This repo is split into four areas:

- `DeepLabCut/`
  Active eye-tracking code. This is the renamed successor of the old `DLC/` tree from `BehaviorBox`.
- `legacy/iRecHS2/`
  Restored legacy eye-tracking code, tests, docs, and assets, including the current legacy Windows executable.
- `models/`
  Landing zone for manually copied active runtime model artifacts. Model blobs are intentionally not tracked in git.

## Current layout

```text
DeepLabCut/
  ToMatlab/
  Tests/
  environment.yaml
training/
  README.md
  train_dlc_eye_model.py
Test/
  README.md
  run_dlc_image_test.py
legacy/
  iRecHS2/
models/
  README.md
bootstrap_eye_track.m
README.md
```

## Bootstrap

From MATLAB:

```matlab
cd('/Users/willsnyder/Desktop/EyeTrack');
paths = bootstrap_eye_track();
disp(paths);
```

`bootstrap_eye_track.m` adds only explicit MATLAB paths:

- `DeepLabCut/ToMatlab`
- `legacy/iRecHS2/scripts`
- `legacy/iRecHS2/iRecTests`

It does not call `addpath(genpath(...))`.

## Active MATLAB/Python boundary

The active interop boundary is unchanged from the BehaviorBox copy:

- Producer side: Python
  `DeepLabCut/ToMatlab/dlc_eye_streamer.py`
- MATLAB bridge helper: Python
  `DeepLabCut/ToMatlab/matlab_zmq_bridge.py`
- Consumer side: MATLAB
  `DeepLabCut/ToMatlab/receive_eye_stream_demo.m`

Transport:

- ZeroMQ JSON stream, default endpoint `tcp://127.0.0.1:5555`

Primary live fields consumed by MATLAB today:

- `frame_id`
- `capture_time_unix_s`
- `publish_time_unix_s`
- `center_x`
- `center_y`
- `diameter_px`
- `confidence_mean`
- `latency_ms`

The bootstrap script only prepares MATLAB path visibility. It does not set `pyenv` for you or choose a Python interpreter.

## Models

Active runtime models should be copied into `models/` as needed.

- They are intentionally excluded from git history here.
- See [models/README.md](models/README.md) for the expected active-model placement.

## Training

A starter script for training and exporting custom DeepLabCut models from your own labeled footage is provided in `training/train_dlc_eye_model.py`.
See `training/README.md` for an end-to-end walkthrough.

## Testing on images

Use `Test/run_dlc_image_test.py` to run DeepLabCut inference from `config.yaml` over a folder of input images, export CSV predictions, and create labeled preview overlays for quick sanity checks.
See `Test/README.md` for usage examples.

## Legacy assets

Legacy source, tests, docs, and the current legacy Windows executable live under `legacy/iRecHS2/`.

## Notes

- This local repo currently has no remote configured.
- This repo was created to let `BehaviorBox` transition toward a future submodule at `BehaviorBox/EyeTrack/` without deleting the current `BehaviorBox` tree yet.
