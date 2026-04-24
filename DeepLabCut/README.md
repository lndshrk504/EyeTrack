# Active DeepLabCut Tree

This directory contains the active eye-tracking code extracted from the old `BehaviorBox/DLC/` tree.

## Key areas

- `ToMatlab/`
  Active FLIR + DLCLive streamer, deferred receiver, and MATLAB importer/client code.
- `Tests/`
  Focused Python smoke/dependency checks for camera and inference timing.
- `environment.yaml`
  Shared conda environment definition used by the active stack.

## Entry points used in practice

- Start production stream:
  `ToMatlab/run_eye_stream_production.py`
- Start deferred receiver on the behavior computer:
  `ToMatlab/run_eye_receiver_service.py`
- Run MATLAB receive smoke test:
  `ToMatlab/run_matlab_eye_receive_test.py`
- Run FLIR + DLCLive bounded timing smoke test:
  `Tests/smoke_dlc_flir_inference.py`

## Related docs

- Two-computer quick start:
  `TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- Streamer/receiver/import details:
  `ToMatlab/README_eye_stream.md`
- Tests guide:
  `Tests/README.md`
