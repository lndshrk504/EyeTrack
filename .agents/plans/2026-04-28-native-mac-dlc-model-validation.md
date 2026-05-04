# Native Mac DLC Model Validation

- Status: Implemented
- Created: 2026-04-28
- Last updated: 2026-04-28

## Goal

Create a native Apple Silicon `DLC` conda environment and add a camera-free validation entrypoint that can load the bundled model under `Models/`, run DLCLive inference without FLIR/PySpin, and write machine-checkable plus visual still-image outputs.

## Active paths

- `Train-Test-Model/validate_models_folder.py`
- `Train-Test-Model/test-README.md`
- `Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1`
- `.agents/plans/2026-04-28-native-mac-dlc-model-validation.md`
- `.agents/PLANS.md`

## Contracts to preserve

- Do not move, rename, rewrite, or commit model artifacts under `Models/`.
- Do not add PySpin or FLIR camera dependencies to the Mac validation path.
- Do not change live streamer timing, coordinate-frame, CSV, metadata JSON, ZMQ, or output-path contracts.
- Keep generated validation CSVs and preview images outside the repository, typically under `/tmp/EyeTrack/model_validation`.

## Planned edits

- Add `Train-Test-Model/validate_models_folder.py` with a synthetic DLCLive smoke test and optional still-image inference/preview generation.
- Document the new camera-free model validation command in `Train-Test-Model/test-README.md`.
- Create the native Mac `DLC` conda environment with TensorFlow, DeepLabCut, DLCLive, OpenCV, and supporting Python packages.

## Validation

- `conda run -n DLC python -c "import tensorflow as tf; print('TF', tf.__version__); print(tf.reduce_sum(tf.random.normal([8, 8])))"`
- `conda run -n DLC python -c "import deeplabcut; print('DLC', deeplabcut.__version__); import dlclive; print('DLCLive import OK')"`
- `conda run -n DLC python Train-Test-Model/train_dlc_eye_model.py --help`
- `conda run -n DLC python Train-Test-Model/run_dlc_image_test.py --help`
- `conda run -n DLC python Train-Test-Model/validate_models_folder.py --model-path Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 --output-dir /tmp/EyeTrack/model_validation`

## Implementation summary

Implemented `Train-Test-Model/validate_models_folder.py`, documented the Mac/no-camera model validation workflow, and created the native osx-arm64 `DLC` conda environment at `/Users/willsnyder/miniforge3/envs/DLC`.

The initial all-pip install path failed when `deeplabcut` tried to build `tables==3.8.0` from source on osx-arm64. The working environment uses conda-forge for `deeplabcut=2.3.11`, `pytables=3.8`, TensorFlow CPU `2.15.0`, PyTorch, OpenCV, and scientific dependencies, then pip for `deeplabcut-live=1.1.0` and `wandb`.

Validation passed for TensorFlow import, DeepLabCut/DLCLive import, training/test CLI help, synthetic model inference, and still-image CSV/preview generation. `tensorflow-metal` was explored but not installed: the package is available for this Mac/Python, but Apple documents V1 TensorFlow networks as unsupported, and the bundled model path uses DLCLive/DLC TensorFlow V1 graph/session code.
