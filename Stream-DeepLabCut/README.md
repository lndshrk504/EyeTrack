# Stream DeepLabCut

This folder contains the active eye-stream boundary between the eye-tracking computer, the behavior computer receiver, and MATLAB.

## Primary files

- `dlc_eye_streamer.py`
- `behavior_eye_receiver.py`
- `run_eye_receiver_service.py`
- `run_eye_stream_receive_test.m`
- `run_eye_stream_production.py`
- `run_matlab_eye_receive_test.py`
- `matlab_zmq_bridge.py` (older reference helper, not the production ingest path)
- `receive_eye_stream_demo.m` (older demo entrypoint)

## Common commands

From the EyeTrack repository root on the behavior computer, the recommended
two-computer command is:

```bash
./run_two_computer_eye_tracking.sh
```

It supervises the remote streamer and local receiver until `Ctrl+C`; it does
not start or stop MATLAB or BehaviorBox. Start MATLAB independently during
mouse warm-up, run this command when eye tracking should begin, and start the
BehaviorBox session only after readiness is reported. End and save that session
before pressing `Ctrl+C`. The SSH production overlay is enabled at 5 display
FPS. Use `./run_two_computer_eye_tracking.sh --check-only` for non-starting
preflight checks. The explicit `--transport-test` and `--full-test` diagnostic
modes are the only modes that start a temporary MATLAB process.

Start production stream on the eye-tracking computer (defaults shown):

```bash
./run_eye_stream_production.py \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto off \
  --display-fps 20
```

Start the deferred receiver on the behavior computer:

```bash
./run_eye_receiver_service.py \
  --address tcp://127.0.0.1:5555 \
  --api-port 8765
```

Run the MATLAB receive smoke test against the same receiver:

```bash
./run_matlab_eye_receive_test.py \
  --address tcp://127.0.0.1:5555 \
  --receiver-url http://127.0.0.1:8765 \
  --duration 10
```

The full test requires at least one valid eye sample by default and prints
`MATLAB_EYE_STREAM_RECEIVE_OK`. Use `--transport-only` for an intentional
no-eye connectivity check; that mode prints `MATLAB_EYE_STREAM_TRANSPORT_OK`.
Use `--behaviorbox-root PATH` when EyeTrack is not directly under the
BehaviorBox repository.

The active runtime is:

1. `dlc_eye_streamer.py` publishes ZeroMQ JSON.
2. `behavior_eye_receiver.py` subscribes, stamps behavior-computer receive time, and writes per-segment chunk files.
3. `BehaviorBoxEyeTrack.m` imports finalized chunks through the receiver HTTP API.

For full live usage notes and two-computer deployment details, see
`../Docs/README_eye_stream.md` and
`../Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`.
