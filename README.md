# EyeTrack

Standalone eye-tracking repo extracted from `BehaviorBox`.

This repo is split into four areas:

- `EyeTrack/`
  Active eye-tracking code. This is the renamed successor of the old `DLC/` tree from `BehaviorBox`.
- `legacy/iRecHS2/`
  Restored legacy eye-tracking code, tests, docs, and non-binary assets.
- `binaries/iRecHS2/`
  Separated legacy binary artifacts. The legacy Windows executable lives here.
- `models/`
  Landing zone for manually copied active runtime model artifacts. Model blobs are intentionally not tracked in git.

## Current layout

```text
EyeTrack/
  ToMatlab/
  Tests/
  environment.yaml
legacy/
  iRecHS2/
binaries/
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

- `EyeTrack/ToMatlab`
- `legacy/iRecHS2/scripts`
- `legacy/iRecHS2/iRecTests`

It does not call `addpath(genpath(...))`.

## Active MATLAB/Python boundary

The active interop boundary is unchanged from the BehaviorBox copy:

- Producer side: Python
  `EyeTrack/ToMatlab/dlc_eye_streamer.py`
- MATLAB bridge helper: Python
  `EyeTrack/ToMatlab/matlab_zmq_bridge.py`
- Consumer side: MATLAB
  `EyeTrack/ToMatlab/receive_eye_stream_demo.m`

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

## Legacy assets and binaries

Legacy source, tests, docs, and non-binary assets live under `legacy/iRecHS2/`.

Separated legacy binaries live under `binaries/iRecHS2/`.

That currently includes:

- `binaries/iRecHS2/iRecHS2.exe`

## Notes

- This local repo currently has no remote configured.
- This repo was created to let `BehaviorBox` transition toward a future submodule at `BehaviorBox/EyeTrack/` without deleting the current `BehaviorBox` tree yet.
