# FLIR Chameleon3 + DLCLive + ZeroMQ + MATLAB

This folder contains the active Python streamer and MATLAB bridge for eye tracking.

## Production Streamer

Start the FLIR -> DLCLive -> ZMQ stream from this folder:

```bash
conda activate dlclivegui
./run_eye_stream_production.py --frame-rate 60 --exposure-us 8000 --gain-auto continuous --display-fps 5
```

The launcher writes outputs under `/tmp/EyeTrack` by default:

- `eye_stream_YYYYMMDD_HHMMSS.csv`: one row per DLC output sample.
- `eye_stream_YYYYMMDD_HHMMSS_metadata.json`: paired sidecar metadata for that CSV.

The CSV intentionally omits static session fields that would be identical on every row. Those fields are saved in the paired metadata JSON instead.

The MATLAB `EyeTrackingRecord` follows the same rule: it keeps one row per DLC output sample with dynamic values and point columns. Static stream details are stored in `EyeTrackingMeta`, especially `EyeTrackingMeta.StreamMetadata`, `EyeTrackingMeta.CsvPath`, and `EyeTrackingMeta.MetadataPath`.

The ZMQ stream follows the same split. Sample messages contain dynamic frame output and point values. Metadata messages are sent at startup and then periodically, controlled by `--metadata-interval-s`.

## CSV Rows

The per-sample CSV contains changing DLC output values:

- sample status
- frame and timestamp fields
- pupil center, diameter, confidence, valid point count
- camera and inference FPS estimates
- latency
- every tracked DLC point as `point_x`, `point_y`, and `point_likelihood`

## Metadata Sidecar

The paired metadata JSON contains static/session information:

- model path, model type, model preset, point names, keypoint mapping
- camera model, serial, sensor ROI, crop, coordinate frame
- requested exposure, gain, frame rate, gain auto mode
- ZMQ address, CSV path, metadata path
- display and dynamic crop settings
- the exact CSV column names

## MATLAB Receive Test

With the Python streamer already running:

```bash
./run_matlab_eye_receive_test.py --duration 10
```

A successful test prints:

```text
MATLAB_EYE_STREAM_RECEIVE_OK
```
