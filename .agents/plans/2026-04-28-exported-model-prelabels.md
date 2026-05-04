# Exported Model Prelabels

- Status: Implemented
- Created: 2026-04-28
- Last updated: 2026-04-28

## Goal

Allow users who only have the exported YangLab/DLCLive model under `Models/` to use its predictions as editable draft labels in a new DeepLabCut project.

## Active paths

- `Models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1`
- `Train-Test-Model/validate_models_folder.py`
- `Train-Test-Model/dlclive_predictions_to_dlc_labels.py`
- `Train-Test-Model/train-README.md`
- `.agents/plans/2026-04-28-exported-model-prelabels.md`
- `.agents/PLANS.md`

## Contracts to preserve

- Do not move, rename, rewrite, or commit model artifacts under `Models/`.
- Do not change live runtime timing, FPS, latency, ZMQ fields, CSV columns, metadata JSON keys, output paths, or model-path resolution.
- Keep label coordinates in the image pixel coordinate frame of the extracted DLC frame folder.
- Treat generated `CollectedData_*.h5` files as draft training labels that require human inspection/correction before training.

## Planned edits

- Add a conversion utility that reads `validate_models_folder.py` flattened predictions and writes DLC-compatible `CollectedData_<scorer>.h5` and `.csv` files into a selected `labeled-data/<folder>/` image directory.
- Map prediction columns to the target DLC project bodyparts by exact name when possible and by keypoint order otherwise, so the bundled model's `RVupil` typo does not block projects using `RVpupil`.
- Document the exported-only prelabel workflow: create project, extract frames, run exported model on the frame folder, convert predictions to `CollectedData`, correct in the DLC/napari labeler, check labels, then train.

## Validation

- `python3 -m py_compile Train-Test-Model/dlclive_predictions_to_dlc_labels.py`
- `python3 Train-Test-Model/dlclive_predictions_to_dlc_labels.py --help`
- `conda run -n DLC python Train-Test-Model/dlclive_predictions_to_dlc_labels.py --help`
- Run the converter against a temporary DLC-style folder using the existing `/tmp/EyeTrack/model_validation_with_image/predictions.csv`, then read the generated HDF with pandas to confirm the expected MultiIndex rows and columns.

## Implementation summary

Implemented `Train-Test-Model/dlclive_predictions_to_dlc_labels.py` to convert flattened DLCLive predictions from `validate_models_folder.py` into DLC-compatible `CollectedData_<scorer>.h5` and `.csv` files under a target `labeled-data/<folder>/` directory.

The converter reads the target DLC project `config.yaml`, uses its `scorer` and `bodyparts`, maps prediction columns by exact name when possible and by keypoint order otherwise, and refuses to overwrite existing label files unless `--overwrite` is passed. This keeps the bundled exported model usable for draft labels even though its `pose_cfg.yaml` has the legacy `RVupil` spelling for one keypoint.

Documented the exported-only prelabel workflow in `Train-Test-Model/train-README.md`.
