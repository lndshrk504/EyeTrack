# EyeTrack

Standalone eye-tracking repo extracted from `BehaviorBox`.

This repo is split into four areas:

- `DeepLabCut/`
  Active eye-tracking code (Python streamer + deferred receiver + MATLAB importer + smoke checks).
- `training/`
  Helper CLI for creating, training, evaluating, and exporting DLC models.
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
legacy/
  iRecHS2/
models/
  README.md
bootstrap_eye_track.m
README.md
```

## Quick starts in this repo

- Two-computer deployment: `DeepLabCut/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- Streamer + receiver + MATLAB importer details: `DeepLabCut/ToMatlab/README_eye_stream.md`
- Model training/export flow: `training/README.md`
- Image-only DLC sanity test: `Test/README.md`

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

## Active Runtime Boundary

The active interop boundary is:

- Producer side on the eye-tracking computer: Python
  `DeepLabCut/ToMatlab/dlc_eye_streamer.py`
- Receiver side on the behavior computer: Python
  `DeepLabCut/ToMatlab/behavior_eye_receiver.py`
- Consumer/import side in MATLAB:
  `BehaviorBoxEyeTrack.m`

Transport:

- ZeroMQ JSON stream from streamer to receiver, default endpoint `tcp://127.0.0.1:5555`
- append-only chunk CSV + metadata JSON written by the receiver
- localhost HTTP control/status API, default receiver URL `http://127.0.0.1:8765`

Canonical eye alignment timebase in BehaviorBox v1:

- `t_receive_us` stamped on the behavior computer by the deferred receiver

Preserved provenance fields:

- `capture_time_unix_s`
- `capture_time_unix_ns`
- `publish_time_unix_s`
- `publish_time_unix_ns`

`DeepLabCut/ToMatlab/matlab_zmq_bridge.py` and `DeepLabCut/ToMatlab/receive_eye_stream_demo.m` are retained for older reference/demo usage, but they are no longer the active production ingest path for BehaviorBox.

The bootstrap script only prepares MATLAB path visibility. It does not start the receiver service or configure Python environments for you.

## Models

Active runtime models should be copied into `models/` as needed.

- They are intentionally excluded from git history here.
- See [models/README.md](models/README.md) for expected active-model placement.

## Training

A starter script for training and exporting custom DeepLabCut models from your own labeled footage is provided in `training/train_dlc_eye_model.py`.

## Legacy assets

Legacy source, tests, docs, and the current legacy Windows executable live under `legacy/iRecHS2/`.
