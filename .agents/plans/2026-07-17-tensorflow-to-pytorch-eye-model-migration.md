# TensorFlow Eye Model to Native PyTorch Migration and DLCLive Export

## Status

- State: Proposed; research complete, implementation not started
- Date opened: 2026-07-17
- Dataset route: replacement project with teacher-assisted labels; the user does not possess the original training data
- Primary target: a trainable DeepLabCut 3 PyTorch eye model and a native DLCLive `.pt` export
- Related environment plan: [AMD ROCm, FLIR, and DLCLive enablement](2026-07-17-amd-rocm-flir-dlclive-enablement.md)
- Master log: update `.agents/PLANS.md` only after this plan has been implemented

## Objective

Replace the current legacy TensorFlow eye-tracking model with a native DeepLabCut 3 PyTorch model that can be trained, evaluated, exported, and run on the AMD Ryzen AI MAX+ 395 GPU through ROCm without installing or depending on NVIDIA software on the AMD computer.

The migration must preserve the existing eight-point pupil geometry, keypoint order, coordinate-frame semantics, crop behavior, and downstream pose shape. It must improve model fidelity on real mouse-eye images rather than merely reproduce the current model's known errors.

## Decision Summary

The primary path is a new labeled project and native retraining, not a direct checkpoint conversion:

1. Record the downloaded model's source URL and license if available, and make one bounded check for any separately published project data.
2. Create a new DeepLabCut project and use the TensorFlow model only as a draft-label generator.
3. Correct and expand the labels using representative failure cases.
4. Train a native DeepLabCut 3 PyTorch model, initially with `resnet_50` for a controlled comparison.
5. Export the trained model through `deeplabcut.export_model` to obtain the native `.pt` artifact expected by DLCLive.
6. Validate scientific accuracy and runtime behavior before changing the production model selection.

A weight-preserving TensorFlow GraphDef -> ONNX -> PyTorch experiment is retained as an optional, non-blocking spike. A converted generic `torch.nn.Module` is not automatically a DeepLabCut 3 checkpoint and will not be treated as the production training path unless it can satisfy the same training, export, and validation contracts.

## Current Evidence

### Existing TensorFlow model

The connected computer at `wbs@10.55.0.1` contains the active exported model at:

```text
/home/wbs/Desktop/BehaviorBox/EyeTrack/models/
  DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1/
```

The model contains:

- `snapshot-650000.pb`, a frozen TensorFlow graph
- `snapshot-650000.pbtxt`, a text graph representation
- `snapshot-650000.index`, `.data-00000-of-00001`, and `.meta` checkpoint files
- `pose_cfg.yaml`
- 269 stored tensors containing approximately 24.0 million scalar values
- graph input `Placeholder:0`
- graph output `concat_1:0`
- a legacy ResNet-50 backbone with part-prediction and location-refinement heads

The bodypart order is:

```text
0 Lpupil
1 LDpupil
2 Dpupil
3 DRpupil
4 Rpupil
5 RVupil
6 Vpupil
7 VLpupil
```

`RVupil` is the spelling in the legacy export. The current repository training helper uses `RVpupil`. Index 5 must remain stable, and any name normalization must be explicit.

### Original project availability

The model configuration records the original project as:

```text
E:\Pupil Recordings\PupilTracking_YangLab-Jim McBurney-Lin-2020-05-14
```

No original `config.yaml`, `labeled-data/`, `CollectedData_*.h5`, `CollectedData_*.csv`, `training-datasets/`, or PyTorch checkpoint was found under the connected computer's home directory or currently mounted external storage.

The user confirmed that the model was downloaded from the internet and that they do not possess the original training data. Personal-storage recovery is therefore closed as a planning branch. If the original download URL can be identified, perform only a bounded provenance and licensing check for any publicly released labels or project files; do not block replacement-dataset work on that possibility.

### Connected computer environment

The connected computer has:

- Pop!_OS 22.04
- NVIDIA RTX 4060
- TensorFlow 2.21.0 with its GPU visible
- PyTorch 2.0.1 with CUDA 11.7 and its GPU visible
- DLCLive 1.1.0
- DLCLive GUI 2.0.0rc1
- PySpin 4.3.0.189
- no full `deeplabcut` installation in the `dlclivegui` environment

This environment can act as a transitional TensorFlow teacher for prelabeling, but it is not currently a complete DeepLabCut training environment.

### AMD computer environment

The target computer has:

- Ubuntu 24.04
- kernel `7.0.0-28-generic`
- AMD Ryzen AI MAX+ 395 / `gfx1151` integrated graphics
- no ROCm tools installed yet

AMD's supported APU stack is ROCm 7.2.1, PyTorch 2.9.1, and Python 3.12. DeepLabCut and DLCLive currently declare compatible Python and PyTorch version ranges, but the complete DeepLabCut training and DLCLive inference paths have not been tested on this hardware.

## Terminology and Required Outcome

The following terms must remain distinct throughout implementation and documentation:

- Dataset migration: reuse TensorFlow-era images and human labels in a PyTorch DeepLabCut project.
- Native PyTorch retraining: create a DeepLabCut 3 PyTorch model and train it from ImageNet-pretrained or other supported PyTorch backbone weights.
- Native PyTorch export: run DeepLabCut's exporter on that trained project and obtain the `.pt` artifact expected by DLCLive.
- Graph conversion: translate the frozen TensorFlow inference graph into ONNX or a generic PyTorch module. This may preserve inference behavior but does not make it a native DeepLabCut project or checkpoint.
- Weight port: manually map TensorFlow checkpoint tensors into a specifically constructed PyTorch architecture. This is custom model-development work and is not the default migration path.

The required production outcome is native PyTorch retraining plus native PyTorch export. A graph conversion alone does not complete this plan.

## Scope

- Recover or reconstruct a valid single-animal DeepLabCut project for the eight pupil keypoints.
- Build a corrected, representative, versioned training dataset.
- Add or update repository tooling so DeepLabCut 3 PyTorch training, evaluation, and export are explicit and reproducible.
- Establish a ROCm training environment on the AMD computer without NVIDIA packages.
- Train and evaluate an initial `resnet_50` model.
- Export a native DLCLive `.pt` model.
- Validate offline predictions, live FLIR inference, output shape, keypoint order, coordinate frame, timing, and downstream compatibility.
- Preserve the TensorFlow model as a read-only baseline and rollback option.
- Document the optional weight-conversion spike and its stop conditions.

## Out of Scope

- Deleting or rewriting the existing TensorFlow model.
- Committing model blobs, videos, label files, generated CSV files, or evaluation artifacts to git.
- Silently changing pupil geometry, keypoint order, coordinate units, crop semantics, CSV columns, metadata keys, or ZMQ fields.
- Treating TensorFlow predictions as ground truth without human review.
- Depending on NVIDIA software for final training or inference on the AMD computer.
- Solving all FLIR/Python compatibility work inside this model plan; the related environment plan owns the system installation and camera-backend decision.

## Behavior Contracts

The migration must preserve these contracts unless a separately reviewed behavior change explicitly replaces them:

- Eight keypoints in the existing numeric order.
- One `(x, y, likelihood)` prediction per keypoint.
- Single-animal DLCLive pose shape compatible with the existing runtime.
- Image-space coordinates in the same frame consumed by pupil calculations and overlays.
- Existing crop, ROI, resize, and image-orientation semantics.
- Existing timestamp, CSV, metadata, and ZMQ contracts.
- Default runtime output directory `/tmp/EyeTrack`.
- Default ZMQ endpoint `tcp://127.0.0.1:5555`.
- Runtime model artifacts remain under `models/<exported-model-name>/` and remain untracked.

The canonical spelling decision for index 5 must be recorded before dataset creation. The recommended project spelling is `RVpupil`, with an explicit legacy import mapping from `RVupil`.

## Data Strategy

### Bounded source and provenance check

Before labeling, record as much model provenance as is available:

- original download URL
- model author or laboratory
- license and redistribution terms
- accompanying publication or model card
- whether the same source separately publishes editable labels, project files, or training images

This check is informational and time-bounded. The plan assumes the original editable images and labels are unavailable. A public artifact is useful only if it contains both the image files and editable human labels, not merely model snapshots or generated `training-datasets/` files.

### Required path: build a replacement labeled project

Create a new single-animal DeepLabCut project with the same eight numeric keypoint positions. Use videos captured from the real FLIR eye-tracking setup and extract frames spanning:

- multiple mice rather than one animal
- multiple sessions and days
- pupil constriction and dilation
- gaze and eye-orientation changes
- eyelid occlusion and blinks
- corneal reflections and changing illumination
- camera-position, focus, and exposure variation
- motion blur and low-contrast frames
- the exact conditions in which the current model visibly fails

Use the current TensorFlow model only to draft labels. The repository's existing workflow is:

1. Run `Train-Test-Model/validate_models_folder.py` on an extracted-frame directory.
2. Convert its prediction CSV with `Train-Test-Model/dlclive_predictions_to_dlc_labels.py`.
3. Open the draft labels in the DeepLabCut or napari labeler.
4. Correct every visible point and remove points that are not actually visible.
5. Run `deeplabcut.check_labels` before creating a training dataset.

Do not select frames solely by the current model's likelihood. Include visually identified failure cases because an inaccurate model can remain overconfident.

### Dataset splitting

Split train, validation, and final holdout data by mouse and/or recording session, not by randomly assigning adjacent frames from the same video. Maintain a final holdout set that is not used for architecture selection or label refinement.

Record, outside git if it contains data:

- source video and session identifiers
- mouse identifiers or pseudonyms
- frame-selection method
- label revision history
- train/validation/holdout membership
- exclusions and reasons

## Environment Architecture

Use isolated environments rather than forcing all responsibilities into one dependency set:

- `dlc-pytorch-train`: Python 3.12, AMD-supported ROCm PyTorch, full DeepLabCut 3, labeling/evaluation dependencies, and no PySpin requirement.
- `dlclivegui`: live runtime dependencies, DLCLive PyTorch support, and the selected FLIR backend.

The training environment must prove:

- `torch.version.hip` reports the expected ROCm build.
- `torch.cuda.is_available()` is true; PyTorch intentionally exposes AMD GPUs through this API.
- device 0 identifies the AMD Radeon device.
- a forward pass, backward pass, optimizer step, and checkpoint save/load succeed.
- no CUDA or NVIDIA wheel is being used on the AMD computer.

The public PySpin 4.3 Python 3.10 wheel does not match AMD's supported Python 3.12 PyTorch stack. Live integration therefore depends on one of the environment plan's camera decisions:

- obtain an official Python 3.12 PySpin build from Teledyne
- use the Spinnaker GenTL producer through Harvesters in Python 3.12
- isolate PySpin capture in a Python 3.10 or C++ process and pass frames to ROCm inference through shared memory or another measured local transport

Do not install a CPython 3.10 PySpin wheel into Python 3.12.

## Repository Implementation Map

Before implementation, inspect the current call chain once and confirm whether each proposed change is necessary. Make the smallest engine-aware changes rather than duplicating the entire workflow.

### Training and export

- `Train-Test-Model/train_dlc_eye_model.py`
  - replace the TensorFlow-only command assumptions with explicit engine-aware behavior
  - preserve TensorFlow commands if they remain useful
  - add PyTorch epoch and device arguments rather than translating epochs into TensorFlow iterations
  - use the project `engine` value as the source of truth
  - export the PyTorch model using the current DeepLabCut API
  - print the selected engine, model configuration, snapshot, and exported artifact
- `Train-Test-Model/train-README.md`
  - document project recovery, prelabel correction, PyTorch dataset creation, AMD training, evaluation, and `.pt` export
  - clearly separate TensorFlow and PyTorch commands
- `Train-Test-Model/validate_models_folder.py`
  - confirm or add explicit TensorFlow versus PyTorch model selection
  - support a `.pt` model path without auto-detecting ambiguous artifacts
  - preserve the prediction CSV column and coordinate contracts
- `Train-Test-Model/dlclive_predictions_to_dlc_labels.py`
  - retain the exact-name-first and order-fallback mapping
  - change only if the agreed `RVupil`/`RVpupil` policy requires a more explicit mapping report

### Model comparison

Prefer a focused comparison entrypoint instead of embedding scientific comparison logic in the production runtime. After inspecting existing validators, either extend the narrowest suitable script or add `Train-Test-Model/compare_tf_pytorch_models.py` to:

- run both models on the same immutable image list
- preserve each model's raw predictions
- map points by explicit numeric index and recorded names
- compute per-keypoint pixel differences and likelihood summaries
- compute derived pupil-center and pupil-size differences when the production calculation is available as a reusable helper
- emit machine-readable CSV/JSON under `/tmp/EyeTrack`
- never overwrite labels or model files

### Live runtime

- `Cam-Tests/smoke_dlc_flir_inference.py`
  - confirm a `.pt` model and `model_type=pytorch` can be selected explicitly
  - preserve camera ROI, frame count, timing, and output behavior
- `Stream-DeepLabCut/dlc_eye_streamer.py`
  - change only if model type, path handling, output shape, or device selection is currently TensorFlow-specific
  - preserve coordinate frames and all output schemas
- `Stream-DeepLabCut/run_eye_stream_production.py`
  - expose deterministic PyTorch model selection if the current launcher cannot already do so
  - preserve existing defaults until the new model passes acceptance
- `models/README.md`
  - document the `.pt` landing-zone convention without committing the artifact
- runtime and operations documentation
  - update only the documents that currently prescribe a TensorFlow-only launch command

### Environment and validation

- `environment.yaml`
  - coordinate ownership with the AMD/FLIR environment plan
  - do not add NVIDIA packages to the AMD specification
  - do not force incompatible PySpin and ROCm Python constraints into one environment
- `Cam-Tests/VerCheck.py`
  - report ROCm/HIP and AMD device identity if current output is CUDA/NVIDIA-specific
- `Cam-Tests/CheckReqs.py`
  - retain TensorFlow metadata checks where needed, but add a separate PyTorch/ROCm result rather than mislabeling HIP as CUDA

When implementation is complete, update this plan's status and append one dated summary to `.agents/PLANS.md`.

## Detailed Execution Phases

### Phase 1: freeze the TensorFlow baseline

1. Treat the current exported directory as read-only.
2. Record file names, byte sizes, hashes, keypoint order, graph input/output names, crop configuration, and package versions.
3. Assemble a fixed image corpus containing normal frames and known failure cases.
4. Run the TensorFlow model on that corpus and store predictions under `/tmp/EyeTrack/tf-baseline/`.
5. Record the exact image preprocessing, crop, resize, orientation, and model-type arguments.

Exit criterion: the TensorFlow baseline can be reproduced from an immutable image list without altering the model.

### Phase 2: build the replacement labeled project

1. Record the model's source URL and license if available, and complete the bounded public-artifact check.
2. Create the replacement project and capture or collect representative eye-tracking videos.
3. Generate draft labels with the TensorFlow teacher and manually correct every annotation.
4. Resolve the index-5 spelling policy before writing final labels.
5. Run label checks and create the session/mouse-level splits.

Exit criterion: a reviewed `config.yaml`, image set, editable labels, and leakage-resistant split exist.

### Phase 3: establish the AMD training environment

1. Follow the related AMD ROCm plan for system and package installation.
2. Install full DeepLabCut 3 into the isolated Python 3.12 training environment.
3. Validate imports, HIP device discovery, matrix operations, autograd, optimizer steps, and checkpoint round trips.
4. Run an import-level DeepLabCut API check before touching the project.
5. Capture an environment manifest for reproducibility.

Exit criterion: a minimal PyTorch training step runs on the AMD GPU with HIP and without NVIDIA software.

### Phase 4: create the native PyTorch model

1. Set `engine: pytorch` in the recovered or replacement project.
2. Create a new PyTorch shuffle rather than reusing or overwriting TensorFlow model directories.
3. Begin with `net_type: resnet_50` for architecture continuity.
4. Inspect the generated `pytorch_config.yaml` and record data augmentation, crop size, normalization, backbone, head, optimizer, scheduler, batch size, device, and epoch settings.
5. Keep the initial model configuration close to DeepLabCut defaults unless image geometry or known eye-specific conditions justify a documented change.

Exit criterion: DeepLabCut creates a valid `dlc-models-pytorch` model directory and configuration without changing the TensorFlow project artifacts.

### Phase 5: perform a tiny overfit test

1. Select a very small reviewed subset, such as 8 to 16 frames.
2. Train long enough to verify that the network can closely fit those labels.
3. Confirm loss decreases, gradients remain finite, snapshots are written, and evaluation can reload the snapshot.
4. Confirm predicted keypoint order and image coordinates against those known frames.
5. Stop and diagnose environment, label, or preprocessing errors before a full training run if the tiny set cannot be fit.

Exit criterion: the native PyTorch pipeline can intentionally overfit a tiny clean dataset on the AMD GPU.

### Phase 6: train and evaluate the full model

1. Train by epochs using the session/mouse-level split.
2. Save periodic and best snapshots without retaining unnecessary optimizer state.
3. Monitor train and validation error for divergence and label problems.
4. Evaluate on the untouched final holdout only after model and training choices are frozen.
5. Add difficult model failures to a later label-refinement iteration rather than contaminating the final holdout.

Exit criterion: the new model meets the agreed held-out keypoint and pupil-geometry quality thresholds and improves the documented failure set.

### Phase 7: export the native `.pt` model

1. Select the snapshot based on held-out evaluation rather than training loss alone.
2. Run the DeepLabCut PyTorch export API.
3. Record the source project, shuffle, snapshot, DeepLabCut version, PyTorch version, architecture, bodypart order, and export date.
4. Place the exported artifact under a new directory in `models/` without committing it.
5. Do not replace or rename the TensorFlow model directory.

Exit criterion: DLCLive can load the exported `.pt` file with `model_type=pytorch` and produce finite predictions for the baseline image corpus.

### Phase 8: validate offline model behavior

1. Run TensorFlow and PyTorch inference on the identical baseline corpus.
2. Verify image preprocessing and coordinate transforms independently before interpreting prediction differences.
3. Compare point locations, likelihoods, pupil center, pupil size, failure rate, and temporal stability.
4. Confirm differences are model-quality changes rather than crop, resize, RGB/BGR, normalization, or indexing drift.
5. Record all expected numerical differences before changing runtime defaults.

Exit criterion: output shape and coordinate contracts match, and quality differences are understood and acceptable.

### Phase 9: validate live FLIR inference

1. Use the camera backend selected by the AMD/FLIR plan.
2. Run the narrow FLIR plus DLCLive smoke test with the PyTorch model.
3. Measure capture time, preprocessing time, inference time, end-to-end latency, achieved FPS, dropped frames, and queue growth.
4. Confirm overlay alignment and pupil estimates on live frames.
5. Run the production launcher only after the smoke test passes.
6. Validate MATLAB/ZMQ consumers only if runtime output shape or serialization code changed.

Exit criterion: the AMD computer runs the new model with the FLIR stream, no NVIDIA dependency, stable output contracts, and documented performance at the intended ROI and frame rate.

### Phase 10: controlled rollout

1. Keep TensorFlow as the explicit default until all acceptance gates pass.
2. Add deterministic selection of the new PyTorch model; do not rely on file-extension guessing when both models are present.
3. Run a limited side-by-side experimental session.
4. Review saved overlays, CSV output, metadata, and derived pupil measures.
5. Change the recommended/default model only after scientific and operational sign-off.

Exit criterion: the PyTorch model is the documented production model and the TensorFlow model remains available as a rollback reference.

## Optional Weight-Preserving Conversion Spike

This spike is not on the critical path. Execute it only after the bounded provenance check and only if preserving the old network's learned behavior has a clear benefit.

### Preconditions

- The original TensorFlow model remains untouched.
- A fixed equivalence corpus and TensorFlow baseline predictions exist.
- Work occurs in a disposable conversion environment, not the live or training environment.
- The effort limit and acceptable numerical tolerance are agreed in advance.

### Experiment A: TensorFlow GraphDef to ONNX

1. Use `snapshot-650000.pb` with input `Placeholder:0` and output `concat_1:0`.
2. Convert with a documented, pinned `tf2onnx` and ONNX opset combination.
3. Inspect unsupported or rewritten operations.
4. Run ONNX inference on the equivalence corpus.
5. Compare raw outputs and decoded points against TensorFlow before proceeding.

Stop if conversion requires custom operations that are not stable on the target runtime or if numerical differences cannot be explained.

### Experiment B: ONNX to a generic PyTorch module

1. Convert the validated ONNX graph with a pinned ONNX-to-PyTorch converter.
2. Run CPU inference first, then ROCm inference.
3. Compare outputs against both TensorFlow and ONNX.
4. Test serialization and reload of the generic module.
5. Determine whether parameters are represented in a form suitable for gradient updates.

Passing this experiment proves only inference equivalence. It does not prove DeepLabCut compatibility.

### Experiment C: native DeepLabCut weight port

Consider this only if Experiments A and B establish value and the native retraining baseline is inadequate.

1. Instantiate the exact DeepLabCut 3 PyTorch ResNet-50 architecture selected for training.
2. Build an explicit tensor-name mapping for the backbone, including TensorFlow HWIO to PyTorch OIHW convolution transposes and BatchNorm state.
3. Determine whether the legacy `part_pred` and `locref_pred` heads can map to the current PyTorch heatmap/deconvolution head.
4. Load only shape- and semantics-compatible tensors; never silently reshape incompatible heads.
5. Compare intermediate activations and final outputs layer by layer.
6. Fine-tune only after numerical and architectural differences are documented.

Likely outcome: the backbone may be portable with custom work, while the legacy and current pose heads require adaptation or reinitialization. If head adaptation becomes a custom architecture, it must gain its own tests, exporter support, and maintenance decision.

### Conversion spike success criteria

- TensorFlow, ONNX, and PyTorch outputs agree within an agreed tolerance on the complete equivalence corpus.
- No unsupported target operation is hidden behind an unmaintained custom runtime.
- The result runs on ROCm without NVIDIA libraries.
- The maintenance cost is justified relative to native retraining.
- If called a DeepLabCut checkpoint, it can actually be loaded, trained, evaluated, and exported through DeepLabCut's supported APIs.

If the final condition is not met, describe the artifact as an inference compatibility module, not as a converted DeepLabCut model.

## Validation Matrix

The exact commands may be adjusted to the implemented CLI, but the following checks define the required coverage.

### Environment

```bash
python3 Cam-Tests/VerCheck.py --strict
python -c "import torch; print(torch.__version__, torch.version.hip, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
python -m torch.utils.collect_env
```

Expected result: AMD/HIP is active and no NVIDIA runtime is selected.

### Training wrapper surface

```bash
python Train-Test-Model/train_dlc_eye_model.py --help
python Train-Test-Model/train_dlc_eye_model.py train --help
python Train-Test-Model/train_dlc_eye_model.py export --help
```

Expected result: PyTorch epochs/device/export options are explicit and TensorFlow-only arguments are not reused ambiguously.

### Offline model validation

```bash
python Train-Test-Model/validate_models_folder.py \
  --model-path <exported-pytorch-pt> \
  --model-type pytorch \
  --image-dir <fixed-image-corpus> \
  --output-dir /tmp/EyeTrack/pytorch-validation
```

Expected result: finite eight-point predictions with the agreed names, order, and image coordinate frame.

### Live FLIR inference

```bash
python3 Cam-Tests/smoke_dlc_flir_inference.py \
  --model-path <exported-pytorch-pt> \
  --model-preset yanglab-pupil8 \
  --model-type pytorch \
  --camera-index 0 \
  --sensor-roi 0 0 640 480 \
  --frames 120
```

Expected result: camera acquisition and ROCm inference complete without model-shape errors, coordinate drift, or unbounded frame backlog.

### Production launcher

```bash
python3 Stream-DeepLabCut/run_eye_stream_production.py --help
```

Run a production session only after the offline and camera smoke checks pass. If the bridge contract changed, also run:

```bash
python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --duration 10
```

## Acceptance Criteria

### Functional

- A full DeepLabCut 3 PyTorch project exists with reviewed labels and `engine: pytorch`.
- A tiny clean dataset can be overfit on the AMD GPU.
- A full model can train, evaluate, save, and reload on ROCm.
- DeepLabCut exports a native `.pt` artifact.
- DLCLive loads the artifact with explicit `model_type=pytorch`.
- The live pipeline returns eight finite `(x, y, likelihood)` records in the expected order.
- No NVIDIA package or runtime is required on the AMD computer.

### Scientific quality

- The held-out split is separated by mouse and/or session.
- Label QA is complete and documented.
- The PyTorch model is no worse than the TensorFlow baseline on the agreed primary metric.
- The PyTorch model improves the specifically curated current-model failure set.
- Pupil center, size, and temporal stability are reviewed in addition to aggregate keypoint error.
- Any expected numerical differences are documented before rollout.

### Runtime quality

- Crop, resize, orientation, and coordinate-frame parity are demonstrated.
- Achieved FPS and latency are measured at the intended ROI and camera settings.
- Dropped frames and queue behavior are bounded and documented.
- CSV, metadata, and ZMQ contracts remain unchanged unless separately approved and validated.

### Reproducibility

- Environment versions and AMD device details are recorded.
- Training configuration, random seed, split definition, and selected snapshot are recorded.
- Export metadata identifies its source model and bodypart order.
- Model and data artifacts remain outside git while their placement rules are documented.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Original labels cannot be recovered | Larger annotation effort | Use the TensorFlow export for drafts, then manually correct and expand labels |
| Draft labels reproduce current model errors | Biased PyTorch model | Inspect every draft and deliberately sample known failure modes |
| Adjacent-frame leakage | Inflated evaluation accuracy | Split by mouse/session and reserve an untouched holdout |
| TensorFlow and PyTorch preprocessing differ | Apparent coordinate or quality regression | Freeze an image corpus and validate crop, color order, normalization, and resize independently |
| Legacy `RVupil` name drifts | Wrong point mapping | Preserve numeric index 5 and record one explicit compatibility mapping |
| PyTorch head differs from TensorFlow head | Direct weight loading fails | Use native retraining; keep weight port optional and layer-validated |
| ROCm APU operations fail or underperform | Training or live inference blocked | Perform matrix, autograd, tiny-overfit, and inference gates before full training |
| AMD officially validates limited data types | Numerical or operator uncertainty | Start with supported settings and measure actual DeepLabCut training behavior |
| PySpin Python version conflicts with ROCm Python | Single-process live stack blocked | Use GenTL, request CPython 3.12 PySpin, or split capture and inference processes |
| Remote TensorFlow package drift | Teacher inference may be fragile | Freeze its current environment and baseline outputs before changes |
| Converted graph appears correct on a few images | Silent scientific errors | Use a broad equivalence corpus and derived pupil metrics |
| Model is accurate but too slow live | Runtime requirement missed | Measure early, then compare resize, ROI, and supported architectures without changing coordinate semantics silently |

## Rollback Strategy

- Never modify the existing TensorFlow export in place.
- Store the PyTorch export under a new model directory.
- Keep model type and path explicit in launch commands.
- Preserve TensorFlow baseline predictions and environment metadata.
- Do not switch production defaults until acceptance is signed off.
- If the PyTorch model fails quality or runtime gates, continue using the TensorFlow model on the connected computer while labels and training are improved.
- A failed conversion spike is discarded without affecting native retraining or runtime artifacts.

## Open Decisions

1. What is the original model download URL and license, and does that source publish any editable project data?
2. Is transitional use of the connected RTX computer for TensorFlow prelabeling acceptable if the final AMD runtime and training stack are NVIDIA-free?
3. Should the canonical new-project spelling be `RVpupil`, with `RVupil` retained only as a legacy import alias?
4. What held-out pixel error, pupil-center error, failure rate, FPS, and latency thresholds define success?
5. Which FLIR path will be used with Python 3.12: custom PySpin, GenTL/Harvesters, or a split capture process?
6. Is the optional weight-conversion spike worth time before a native PyTorch baseline has been trained?
7. Should `resnet_50` remain the production architecture if a faster or more accurate supported PyTorch architecture performs better?

## Recommended Next Action

Before installing packages or changing code, record the model download URL and license if available, then identify a small immutable image corpus containing both ordinary eye frames and known failures. The implementation path is now teacher-assisted relabeling: create a replacement project, generate draft labels with the TensorFlow model, correct every point manually, and use that reviewed corpus as the baseline for later training, conversion, and export decisions.
