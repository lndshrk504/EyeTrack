# Training a Custom Eye Model

This folder provides a beginner-friendly script to train and export a TensorFlow DeepLabCut model using footage from your own setup.

## What this script does

`train_dlc_eye_model.py` wraps a standard DeepLabCut workflow into explicit steps:

1. `init-project` – create DLC project and set pupil keypoints.
2. `extract-frames` – sample frames for labeling.
3. Label frames using the DLC GUI (`deeplabcut.label_frames(config)`) or napari.
4. `create-dataset` – build the training set from labels.
5. `train` – train the network.
6. `evaluate` – evaluate test/train errors.
7. `export` – export a DLCLive-compatible model for runtime inference.

## Prerequisites

- A Python environment with `deeplabcut` installed.
- TensorFlow-compatible GPU drivers/CUDA if using GPU training.
- Videos captured from your real eye-tracking setup.

## Quick start

Run these commands from the EyeTrack repository root unless a command says
otherwise.

### 1) Create a project

```bash
python Train-Test-Model/train_dlc_eye_model.py init-project \
  --project PupilTracking \
  --experimenter YourName \
  --videos /data/eye/session1.mp4 /data/eye/session2.mp4 \
  --working-directory /data/dlc_projects \
  --copy-videos
```

This creates a DLC project and writes custom keypoints into the generated `config.yaml`.

### 2) Extract frames

```bash
python Train-Test-Model/train_dlc_eye_model.py extract-frames \
  --config /data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml
```

### 3) Label frames

Use DeepLabCut labeling GUI in Python:

```python
import deeplabcut
deeplabcut.label_frames('/data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml')
```

(Optional but recommended) check labels:

```python
deeplabcut.check_labels('/data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml')
```

### 4) Create dataset

```bash
python Train-Test-Model/train_dlc_eye_model.py create-dataset \
  --config /data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml
```

### 5) Train

```bash
python Train-Test-Model/train_dlc_eye_model.py train \
  --config /data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml \
  --maxiters 200000 \
  --saveiters 10000
```

### 6) Evaluate

```bash
python Train-Test-Model/train_dlc_eye_model.py evaluate \
  --config /data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml \
  --plotting
```

### 7) Export for runtime use

```bash
python Train-Test-Model/train_dlc_eye_model.py export \
  --config /data/dlc_projects/PupilTracking-YourName-YYYY-MM-DD/config.yaml \
  --overwrite
```

After export, copy the exported model directory into this repository's runtime Models folder:

```text
Models/<your-exported-model-folder>/
```

The runtime model layout should match the convention documented in
`Models/README.md`; keep the exported model directory intact rather than moving
individual snapshot files by hand.

You can then run inference with:

```bash
python3 Cam-Tests/smoke_dlc_flir_inference.py --model-path Models/<your-exported-model-folder>
```

## Notes

- The default keypoint order matches the existing YangLab pupil-8 naming convention used in this repository.
- If you change keypoints/order, also update runtime `--kp-*` arguments in `Stream-DeepLabCut/dlc_eye_streamer.py` usage.
- For best results, iteratively label failure cases from your real experiments and retrain.
