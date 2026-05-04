# Test DeepLabCut Model on Images

This folder provides a CLI for **fast visual sanity checks** of a trained DeepLabCut model on still images.

The script runs DLC inference from your `config.yaml`, writes CSV outputs, and can generate labeled preview images with keypoint names and likelihood scores.

## Script

- `run_dlc_image_test.py`
- `validate_models_folder.py`

## Validate the bundled `Models/` folder without a camera

Use this on a Mac or other machine without FLIR/PySpin camera access. It loads
the active model folder with DLCLive, runs a synthetic image smoke test, and can
optionally run still images through the model with CSV and preview outputs.

```bash
conda run -n DLC python Train-Test-Model/validate_models_folder.py \
  --model-path Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --output-dir /tmp/EyeTrack/model_validation
```

With real eye images:

```bash
conda run -n DLC python Train-Test-Model/validate_models_folder.py \
  --model-path Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1 \
  --image-dir /path/to/test_images \
  --frametype .png \
  --output-dir /tmp/EyeTrack/model_validation
```

This validates TensorFlow/DLCLive/model compatibility only. It does not test
FLIR acquisition, PySpin, live timing, ZMQ streaming, or MATLAB receive-side
behavior.

## Basic inference (CSV output only)

```bash
python Train-Test-Model/run_dlc_image_test.py \
  --config /path/to/your-dlc-project/config.yaml \
  --image-dir /path/to/test_images \
  --frametype .png \
  --shuffle 1 \
  --trainingsetindex 0 \
  --gpu 0 \
  --output-csv /path/to/results/dlc_predictions.csv
```

## Inference + labeled overlay previews

```bash
python Train-Test-Model/run_dlc_image_test.py \
  --config /path/to/your-dlc-project/config.yaml \
  --image-dir /path/to/test_images \
  --frametype .png \
  --shuffle 1 \
  --trainingsetindex 0 \
  --gpu 0 \
  --output-csv /path/to/results/dlc_predictions.csv \
  --preview-dir /path/to/results/dlc_previews \
  --pcutoff 0.5 \
  --max-previews 200
```

## Required/important arguments

- `--config`: path to DLC `config.yaml`.
- `--image-dir`: directory of input images.
- `--frametype`: extension filter such as `.png`, `.jpg`.
- `--shuffle`: model shuffle index.
- `--trainingsetindex`: `TrainingFraction` index.
- `--gpu`: GPU id for inference (`0`, `1`, etc). Omit to use DLC default.
- `--output-csv`: flattened CSV output path. Defaults to `<image-dir>/dlc_predictions.csv`.
- `--preview-dir`: optional preview output directory. Defaults to `<image-dir>/dlc_previews`.

For runtime smoke tests after export, place the exported model directory under
`Models/` as described in `Models/README.md`, then run
`Cam-Tests/smoke_dlc_flir_inference.py` with `--model-path Models/<model-name>`.

## Outputs

1. Raw DLC CSV in `--image-dir` produced by `deeplabcut.analyze_time_lapse_frames`.
2. Flattened CSV at `--output-csv` with columns:
   - `image`
   - `<keypoint>_x`
   - `<keypoint>_y`
   - `<keypoint>_p`
3. Optional labeled preview images in `--preview-dir` with keypoint name + likelihood text.
