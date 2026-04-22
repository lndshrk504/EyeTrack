# ToMatlab

This folder contains the active MATLAB/Python bridge layer.

## Primary files

- `dlc_eye_streamer.py`
- `matlab_zmq_bridge.py`
- `receive_eye_stream_demo.m`
- `run_eye_stream_production.py`
- `run_matlab_eye_receive_test.py`

## Common commands

Start production stream (defaults shown):

```bash
./run_eye_stream_production.py \
  --frame-rate 60 \
  --exposure-us 6000 \
  --gain-auto off \
  --display-fps 20
```

Run MATLAB receive test against the same stream:

```bash
./run_matlab_eye_receive_test.py --address tcp://127.0.0.1:5555 --duration 10
```

For full live usage notes and two-computer deployment details, see `README_eye_stream.md` and `../TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`.
