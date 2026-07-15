# FLIR Chameleon3 + DLCLive + ZeroMQ + Deferred Receiver + MATLAB

The active scripts described here live in `../Stream-DeepLabCut/`.
This guide documents the Python streamer, the deferred eye receiver, and the
MATLAB-side importer for eye tracking.

## Active Pipeline

The production path is:

1. `dlc_eye_streamer.py` runs on the eye-tracking computer and publishes ZeroMQ JSON.
2. `behavior_eye_receiver.py` runs on the behavior computer, stamps receive time, and writes append-only segment chunk files.
3. `BehaviorBoxEyeTrack.m` connects to the receiver HTTP API, opens/closes segments, and imports finalized chunks outside the hot loops.

BehaviorBox aligns eye data on `t_receive_us` in v1. Remote capture and publish timestamps are still preserved in the raw imported tables and metadata.

Recommended two-computer operating order:

1. Start MATLAB/BehaviorBox while the mouse warms up, but do not begin a
   BehaviorBox session.
2. Start the Python streamer and `run_eye_receiver_service.py` through the
   root `run_two_computer_eye_tracking.sh` supervisor.
3. Wait for receiver readiness, then begin the BehaviorBox session.
4. After the session saves, press `Ctrl+C` in the supervisor terminal.

For a one-computer setup, both the streamer and receiver stay on localhost.
See [SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md](./SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md).

For a direct-cable two-computer setup, the streamer binds to the eye-tracking
computer's direct-cable IP and the receiver connects from the behavior computer.
See [TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md](./TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md).

## Deferred Receiver

Run the external receiver on the behavior computer before beginning a
BehaviorBox session:

```bash
cd /path/to/BehaviorBox/EyeTrack/Stream-DeepLabCut
./run_eye_receiver_service.py \
  --address tcp://127.0.0.1:5555 \
  --api-port 8765
```

The receiver subscribes to the existing ZeroMQ eye stream, stamps samples with behavior-computer receive time, writes per-segment chunk CSVs, and exposes a localhost HTTP API that MATLAB uses to register sessions and import finalized chunks.

The BehaviorBox project `startup.m` supplies the normal two-computer defaults
`BB_EYETRACK_ZMQ_ADDRESS=tcp://10.55.0.1:5555` and
`BB_EYETRACK_RECEIVER_URL=http://127.0.0.1:8765` when those variables are empty.
For a single-computer setup, explicitly set the ZMQ address to
`tcp://127.0.0.1:5555` before MATLAB starts, or use MATLAB `setenv` before the
BehaviorBox session begins. If the HTTP API is nondefault, override
`BB_EYETRACK_RECEIVER_URL` as well.

## Production Streamer

Start the FLIR -> DLCLive -> ZMQ stream from the runtime folder:

```bash
cd /path/to/BehaviorBox/EyeTrack/Stream-DeepLabCut
conda activate dlclivegui
./run_eye_stream_production.py \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto off \
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

The MATLAB `EyeTrackingRecord` follows the same rule: it keeps one row per DLC
output sample with dynamic values and point columns. Static streamer details are
stored in `EyeTrackingMeta.StreamMetadata`.

The path fields have distinct owners:

- `EyeTrackingMeta.StreamMetadata.csv_path` and `.metadata_path` are the
  streamer files on the eye-tracking computer, normally under `/tmp/EyeTrack`.
- `EyeTrackingMeta.CsvPath` and `.MetadataPath` are receiver-managed segment
  chunk files on the behavior computer.

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

The paired streamer metadata JSON contains static/session information:

- model path, model type, model preset, point names, keypoint mapping
- camera model, serial, sensor ROI, crop, coordinate frame
- requested and applied exposure, gain, frame rate, gain-auto, pixel-format,
  sensor-ROI, buffer-count, and camera settings
- ZMQ address, CSV path, metadata path
- display and dynamic crop settings
- the exact CSV column names

Periodic ZMQ metadata carries the same static runtime provenance except the
sidecar-only CSV column list. The deferred receiver exposes the current flat
snapshot as `stream_metadata` in its health response and persists it at the top
level of `receiver_session.json`. Later periodic metadata refreshes that saved
session snapshot.

## MATLAB Receive Test

With the Python streamer and deferred receiver already running:

```bash
cd /path/to/BehaviorBox/EyeTrack/Stream-DeepLabCut
./run_matlab_eye_receive_test.py --duration 10 --receiver-url http://127.0.0.1:8765
```

A successful test prints:

```text
MATLAB_EYE_STREAM_RECEIVE_OK
```

The full test requires at least `--min-samples` total rows and
`--min-valid-samples` valid eye rows; the valid minimum defaults to `1`. To
diagnose transport intentionally without an eye in frame, run:

```bash
./run_matlab_eye_receive_test.py \
  --duration 10 \
  --receiver-url http://127.0.0.1:8765 \
  --transport-only
```

That mode prints `MATLAB_EYE_STREAM_TRANSPORT_OK` and does not print the full
receive marker. If EyeTrack is not located directly under the BehaviorBox
repository, pass `--behaviorbox-root /path/to/BehaviorBox` explicitly.

## Legacy Helpers

`matlab_zmq_bridge.py` and `receive_eye_stream_demo.m` are retained as older reference/demo tooling. They are no longer the production ingest path used by `BehaviorBoxEyeTrack.m`.
