# FLIR Chameleon3 + DLCLive + ZeroMQ + Deferred Receiver + MATLAB

This folder contains the active Python streamer, the deferred eye receiver, and the MATLAB-side importer for eye tracking.

## Active Pipeline

The production path is:

1. `dlc_eye_streamer.py` runs on the eye-tracking computer and publishes ZeroMQ JSON.
2. `behavior_eye_receiver.py` runs on the behavior computer, stamps receive time, and writes append-only segment chunk files.
3. `BehaviorBoxEyeTrack.m` connects to the receiver HTTP API, opens/closes segments, and imports finalized chunks outside the hot loops.

BehaviorBox aligns eye data on `t_receive_us` in v1. Remote capture and publish timestamps are still preserved in the raw imported tables and metadata.

## Deferred Receiver

Run the external receiver on the behavior computer before starting BehaviorBox:

```bash
./run_eye_receiver_service.py \
  --address tcp://127.0.0.1:5555 \
  --api-port 8765
```

The receiver subscribes to the existing ZeroMQ eye stream, stamps samples with behavior-computer receive time, writes per-segment chunk CSVs, and exposes a localhost HTTP API that MATLAB uses to register sessions and import finalized chunks.

If the receiver is running on the same behavior computer as MATLAB and uses the default API URL, BehaviorBox does not need extra environment variables. If you bind the API somewhere else, set `BB_EYETRACK_RECEIVER_URL` before starting MATLAB.

## Production Streamer

Start the FLIR -> DLCLive -> ZMQ stream from this folder:

```bash
conda activate dlclivegui
./run_eye_stream_production.py \
  --frame-rate 60 \
  --exposure-us 8000 \
  --gain-auto continuous \
  --display-fps 5
```

Key defaults from `run_eye_stream_production.py`:

- address: `tcp://127.0.0.1:5555`
- sensor ROI: `0 0 640 480`
- display: enabled by default (`--no-display` disables)
- CSV output directory: `/tmp/EyeTrack` (override with `--csv-dir`)

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

With the Python streamer and deferred receiver already running:

```bash
./run_matlab_eye_receive_test.py --duration 10 --receiver-url http://127.0.0.1:8765
```

A successful test prints:

```text
MATLAB_EYE_STREAM_RECEIVE_OK
```

## Legacy Helpers

`matlab_zmq_bridge.py` and `receive_eye_stream_demo.m` are retained as older reference/demo tooling. They are no longer the production ingest path used by `BehaviorBoxEyeTrack.m`.
