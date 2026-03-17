# FLIR Chameleon3 + DLCLive + ZeroMQ + MATLAB

Files:
- `dlc_eye_streamer.py` — Python publisher with PySpin camera acquisition, DLCLive inference, pupil metrics, and live overlay.
- `matlab_zmq_bridge.py` — small Python helper that makes MATLAB subscription easier.
- `receive_eye_stream_demo.m` — MATLAB subscriber demo.

## Python dependencies

Install these in the same Python environment:

```bash
pip install deeplabcut-live[tf] pyzmq opencv-python numpy
```

`PySpin` is installed separately from the Teledyne/FLIR Spinnaker package.

## Example run

Replace the point indices with the order used by your eye model.

```bash
python dlc_eye_streamer.py \
  --model-path /path/to/exported_model \
  --model-type base \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --kp-top 0 \
  --kp-bottom 1 \
  --kp-left 2 \
  --kp-right 3 \
  --kp-center 4 \
  --point-names top bottom left right center \
  --display \
  --csv eye_stream.csv
```

If your model expects grayscale directly, add:

```bash
--pass-gray-to-dlc
```

## MATLAB setup

1. Put `matlab_zmq_bridge.py` in the same folder as `receive_eye_stream_demo.m`.
2. Edit `pythonExe` in `receive_eye_stream_demo.m` so MATLAB uses the same Python environment that has `pyzmq` installed.
3. Run `receive_eye_stream_demo` from MATLAB.
