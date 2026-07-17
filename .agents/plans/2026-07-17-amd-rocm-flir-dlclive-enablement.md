# AMD ROCm DLCLive and FLIR Runtime Enablement

- Status: Ready for implementation
- Created: 2026-07-17
- Last updated: 2026-07-17

## Goal

Create the expected `dlclivegui` conda environment on the local EyeTrack host,
install a supported FLIR camera stack, and run DeepLabCut/DLCLive inference on
the integrated AMD Radeon 8060S through ROCm without installing or depending on
NVIDIA drivers, CUDA, cuDNN, TensorRT, or `nvidia-*` Python packages.

The production target is the existing FLIR capture -> DLCLive inference -> ZMQ
publisher path. The implementation must preserve the repository's transport,
coordinate, serialization, model-path, and output-directory contracts.

## Scope and host assumptions

- Local, single-computer Linux setup unless a later implementation explicitly
  validates the two-computer workflow.
- Host OS: Ubuntu 24.04.4 LTS x86_64.
- Current kernel: `7.0.0-28-generic`.
- Processor: AMD Ryzen AI MAX+ 395 with Radeon 8060S.
- GPU PCI ID: `1002:1586`; AMD architecture: `gfx1151`.
- Kernel driver: inbox `amdgpu` is loaded.
- GPU device nodes: `/dev/kfd` and `/dev/dri/renderD128` exist.
- Current user is not yet in the `render` or `video` groups.
- Secure Boot is disabled.
- Miniforge/conda is installed under `/home/wbs/miniforge3`.
- The expected `/home/wbs/miniforge3/envs/dlclivegui` environment does not
  currently exist.
- No ROCm tools or runtime packages are currently installed.
- No camera was connected or visible during planning.
- `models/` currently contains only its README; no runnable TensorFlow or
  PyTorch model is present.

## Research findings

### AMD support

- AMD's ROCm 7.2 Ryzen support matrix explicitly lists the Ryzen AI MAX+ 395 and
  `gfx1151` as supported on Linux.
- The supported framework combination for this APU is ROCm 7.2, PyTorch 2.9,
  and Python 3.12. AMD labels that combination production-supported.
- AMD documents only FP16 as formally validated on this Ryzen APU. Other data
  types may work but must be treated as unverified until benchmarked.
- AMD's current matrix lists Ubuntu 24.04.3 with preliminary support. This host
  is Ubuntu 24.04.4, so an implementation must verify rather than assume OS
  compatibility.
- AMD requires the OEM Ubuntu kernel line, the inbox AMD driver, and
  `amdgpu-install --usecase=rocm --no-dkms` for Ryzen APUs. Installing
  `amdgpu-dkms` would contradict the supported Ryzen procedure.
- The locally available `linux-oem-24.04` package is not installed. Its current
  candidate is `6.17.0-1028.28`; it can be installed alongside the existing
  generic kernels to preserve rollback.
- PyTorch retains the `torch.cuda` API name when built for ROCm. A successful
  `torch.cuda.is_available()` result is not evidence of NVIDIA software;
  `torch.version.hip` and the reported Radeon device name establish that the
  backend is AMD ROCm.

### Existing Python environment

- The active base Python is 3.13 and lacks NumPy, OpenCV, pyzmq, PySpin,
  DLCLive, and TensorFlow.
- The current `environment.yaml` is a machine export rather than a minimal,
  reproducible runtime specification. It pins Python 3.10, TensorFlow, both
  CUDA 11 and CUDA 12 libraries, NVIDIA runtime packages, two OpenCV wheels,
  and a non-public `spinnaker-python` package.
- The conda portion of the existing file resolves, but a Python 3.10 pip dry
  run fails on the pinned CUDA bindings and the unavailable
  `spinnaker-python==4.3.0.189` distribution.
- The supported AMD path must therefore replace the exported specification with
  a curated Python 3.12 ROCm/PyTorch environment rather than editing individual
  NVIDIA pins.

### DeepLabCut and DLCLive

- DeepLabCut 3.x uses a PyTorch backend and can retrain an existing labeled DLC
  project by selecting `engine: pytorch`.
- DeepLabCut-Live 1.1 supports PyTorch models with the existing `DLCLive` API.
  It expects `model_type="pytorch"` and a `.pt` file created by
  `deeplabcut.export_model`.
- DeepLabCut-Live requires the inference engine to match the model's export
  engine. A legacy TensorFlow `.pb` export cannot simply be loaded by PyTorch or
  renamed to `.pt`.
- The local streamer already accepts `--model-type pytorch`, and its inference
  loop already passes NumPy frames into `DLCLive`. Its camera import and
  acquisition path are still hard-wired to PySpin.
- The current camera-free model validator constructs only
  `DLCLive(..., model_type="base")` and must be generalized before it can
  validate a PyTorch export.

### FLIR and camera compatibility

- The Chameleon3 is a USB3 Vision/GenICam camera and is listed with Spinnaker
  resources by Teledyne.
- Teledyne currently publishes Spinnaker SDK 4.3.0.189 Linux downloads labeled
  for Ubuntu 22.04, not Ubuntu 24.04. The implementation must inspect and
  simulate package installation on this host before making system changes.
- Teledyne's current PySpin guidance and Spinnaker 4.3 release notes document a
  Python 3.10 wheel. No official Python 3.12 PySpin wheel was found during this
  research, and `spinnaker-python` is not available from the configured public
  Python package index.
- Spinnaker 4.x includes a GenTL producer (`Spinnaker_GenTL.cti`) for Teledyne
  USB3 Vision and GigE Vision devices. A Python 3.12 GenTL consumer such as
  `harvesters` can use this producer without importing PySpin.
- The current DeepLabCut-Live GUI has a GenTL backend through its `gentl`
  optional dependency.
- Aravis 0.8 supports USB3 Vision on Linux and is the fallback if the vendor
  Spinnaker package cannot be installed safely. Ubuntu 24.04 provides
  `aravis-tools`, `libaravis-0.8-0`, and `gir1.2-aravis-0.8`.

## Architecture decision

Use one Python 3.12 conda environment named `dlclivegui` for DeepLabCut,
DLCLive, ROCm PyTorch, ZeroMQ, display, and camera-consumer code.

Use the following backend order:

1. Preferred camera path: Spinnaker SDK system libraries and
   `Spinnaker_GenTL.cti`, consumed by Python 3.12 through `harvesters`.
2. Conditional legacy path: PySpin only if Teledyne supplies a matching Python
   3.12 wheel and it passes an isolated import/camera smoke test.
3. Fallback camera path: Aravis USB3 Vision if the Ubuntu 22.04 Spinnaker
   package does not install cleanly on Ubuntu 24.04.4.

Do not create a Python 3.10 AMD environment using unsupported ROCm wheels. Do
not use `tensorflow-rocm` for the production path because AMD's Ryzen APU matrix
documents PyTorch, not TensorFlow, as the supported framework. A separate
CPU-only TensorFlow environment may be used temporarily to run a supplied
legacy model for comparison or prelabeling, but it is not the production
environment and must contain no NVIDIA packages.

## Active paths

- `environment.yaml`
- `Stream-DeepLabCut/dlc_eye_streamer.py`
- `Stream-DeepLabCut/run_eye_stream_production.py`
- `Stream-DeepLabCut/check_pyspin_camera.py`
- `Cam-Tests/VerCheck.py`
- `Cam-Tests/CheckReqs.py`
- `Cam-Tests/GSTOCV.py`
- `Cam-Tests/smoke_dlc_flir_inference.py`
- `Train-Test-Model/validate_models_folder.py`
- `Train-Test-Model/train_dlc_eye_model.py`
- `README.md`
- `Stream-DeepLabCut/README.md`
- `Cam-Tests/README.md`
- `Docs/README_eye_stream.md`
- `Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `models/README.md`
- `.agents/plans/2026-07-17-amd-rocm-flir-dlclive-enablement.md`
- `.agents/PLANS.md` only after implementation is complete

Likely new focused files:

- `Cam-Tests/check_amd_rocm.py`
- `Cam-Tests/check_gentl_camera.py`
- `Cam-Tests/smoke_dlc_gentl_inference.py`
- `Docs/AMD_ROCM_FLIR_SETUP.md`

New files should be added only when the existing diagnostic scripts cannot
express the required check cleanly. Do not duplicate checks merely to rename
them.

## Contracts to preserve

- Default ZMQ publisher endpoint remains `tcp://127.0.0.1:5555`.
- Default output directory remains `/tmp/EyeTrack`.
- CSV column names and ordering remain unchanged.
- Metadata JSON and CSV sidecar pairing remains unchanged.
- ZMQ sample and metadata field names remain unchanged.
- Sample-vs-metadata message separation remains unchanged.
- Timestamp units and capture/publish timestamp meanings remain unchanged.
- Sensor ROI and DLCLive crop remain separate concepts.
- Published coordinates remain in the acquired-frame coordinate system unless
  the existing explicit crop-frame option is selected.
- The `yanglab-pupil8` keypoint names, ordering, and index mapping remain
  unchanged in any replacement PyTorch model.
- Active model artifacts remain untracked under `models/` and are supplied
  explicitly through `--model-path`.
- Model blobs, generated CSV/JSON files, and camera captures are not committed.
- The PySpin path remains available for previously supported hosts unless a
  separate reviewed change intentionally removes it.

## Expected behavior changes

- Inference initialization time, per-frame latency, throughput, and frame-drop
  behavior will change when moving from TensorFlow to ROCm PyTorch.
- A newly trained PyTorch model will not produce bitwise-identical coordinates
  or likelihoods to the legacy TensorFlow model. Pupil diameter, center, and
  confidence-derived outputs can therefore change.
- GenTL or Aravis acquisition can report different capture timing, buffering,
  timeout, and applied-camera-setting behavior than PySpin.
- GPU inference should use the Radeon 8060S through HIP/ROCm. The implementation
  must not claim GPU acceleration until `torch.version.hip`, Radeon device
  enumeration, and measured inference timing all pass.
- No top-level CSV or ZMQ schema changes are planned. The existing nested
  `camera_info` metadata object may gain a `backend` value such as `gentl`,
  `pyspin`, or `aravis`; this is a backward-compatible metadata addition but
  must still be documented and validated.

## External prerequisites and decision gates

### Camera gate

- Connect the Chameleon3 directly to a USB 3.x port before camera validation.
- Record the exact camera model, serial, firmware version, and USB topology.
- Do not diagnose a missing camera as a software regression while the device is
  disconnected.

### Vendor software gate

- A Teledyne Vision Solutions account is required to download Spinnaker SDK
  4.3.0.189 for Linux Ubuntu 22.04 x64.
- Inspect the SDK README, license, included Debian packages, GenTL producer, and
  available Python wheels before installation.
- Run package metadata and dependency simulations before invoking the vendor
  installer.
- Do not force Ubuntu 22.04 packages onto Ubuntu 24.04.4 if dependencies do not
  resolve cleanly.
- If a `cp312` PySpin wheel is present, test it in an isolated throwaway conda
  environment before deciding whether the production environment should expose
  PySpin.
- If only a `cp310` wheel is present, keep it out of `dlclivegui` and use GenTL.

### Model gate

- Obtain the original DLC project with reviewed labeled frames and its
  eight-keypoint definition, or obtain a representative image set that can be
  labeled and reviewed.
- A TensorFlow export alone is insufficient for an equivalent PyTorch export.
- If only a TensorFlow export is available, use it in a separate CPU-only
  comparison environment to generate draft labels, then review those labels
  manually before PyTorch training.
- Do not begin production acceptance testing until a PyTorch `.pt` export is
  present under `models/` and its point order is confirmed.

### Scientific acceptance gate

- Define the acceptable coordinate error, pupil-metric error, confidence
  behavior, and minimum inference FPS before replacing the current production
  model.
- Use a fixed, manually reviewed evaluation set for the legacy-vs-PyTorch
  comparison.
- Do not choose tolerances solely from model-to-model agreement; compare both
  models against reviewed ground truth.

## Planned implementation

### Phase 1: Record a pre-install baseline

- Save the OS, kernel, GPU PCI ID, loaded driver, group membership, device-node
  permissions, conda inventory, and currently installed camera/GStreamer tools
  in the implementation notes.
- Confirm the existing generic kernels remain installed as a boot fallback.
- Confirm sufficient disk space before downloading ROCm and PyTorch wheels.
- Confirm that no NVIDIA packages or drivers are currently required by another
  local workflow before removing NVIDIA pins from this repository environment.

### Phase 2: Install the supported AMD system stack

- Install `linux-oem-24.04` alongside, not in place of, the existing kernel.
- Reboot into the OEM kernel and record the exact version.
- Install AMD's ROCm 7.2.1 Ryzen package using the official Ubuntu 24.04
  installer flow.
- Use `amdgpu-install --usecase=rocm --no-dkms`; do not install AMD DKMS.
- Add the user to `render` and `video`, then reboot so `/dev/kfd` is accessible.
- Verify `rocminfo` reports a `gfx1151` GPU agent before creating the Python
  environment.
- Stop this phase if AMD's installer rejects Ubuntu 24.04.4 or the OEM kernel;
  do not bypass its compatibility checks without a separately reviewed plan.

### Phase 3: Install and validate the FLIR system layer

- Download the official Spinnaker 4.3.0.189 Ubuntu 22.04 x64 archive through
  Teledyne's authenticated download page.
- Inspect package metadata and simulate dependencies on Ubuntu 24.04.4.
- Install the full SDK only if the simulation is clean and the installer does
  not require forced dependency resolution.
- Verify SpinView starts and can enumerate the connected Chameleon3.
- Locate `Spinnaker_GenTL.cti` and verify `GENICAM_GENTL64_PATH` points to its
  directory.
- Verify the CTI with a minimal GenTL consumer before using it in production.
- Install the vendor udev rules and verify non-root camera access.
- If Spinnaker is blocked, install Aravis from Ubuntu packages, apply a scoped
  USB3 Vision udev rule, and validate the camera with `arv-tool` and
  `arv-camera-test`.
- Never run SpinView, PySpin, Harvesters, and Aravis against the same camera at
  the same time.

### Phase 4: Replace the conda specification and create `dlclivegui`

- Replace the current machine-exported `environment.yaml` with a concise,
  hand-maintained Linux environment named `dlclivegui`.
- Remove the machine-specific `prefix` entry.
- Pin Python 3.12 and NumPy 1.26.x because DLCLive 1.1 requires NumPy below 2.
- Include only the scientific, display, transport, and camera-consumer packages
  used by this repository.
- Install AMD's official ROCm 7.2.1 PyTorch 2.9.1, torchvision 0.24, and matching
  Triton wheels from `repo.radeon.com`.
- Install DeepLabCut 3.x with its PyTorch engine only.
- Install `deeplabcut-live==1.1.0` and
  `deeplabcut-live-gui==2.0.0rc1` with PyTorch and GenTL support.
- Install `harvesters` for the Spinnaker GenTL producer.
- Include OpenCV, pyzmq, PySide6, pandas, scipy, PyTables, Pillow, matplotlib,
  and the adjacent dependencies required by the runtime and diagnostics.
- Resolve the GUI's pip OpenCV requirement deliberately. Do not install both
  `opencv-python` and `opencv-python-headless` as the old environment did.
- Run a complete conda/pip dry-run and record the final resolved versions before
  creating the environment.
- Reject the solve if it introduces TensorFlow, `nvidia-*`, CUDA, cuDNN, or
  TensorRT packages.
- Export a small explicit lock or package inventory after successful validation;
  do not commit a host-specific absolute prefix.

### Phase 5: Make environment validation backend-aware

- Update `Cam-Tests/VerCheck.py` so strict validation can select an AMD ROCm
  profile rather than requiring PySpin and TensorFlow unconditionally.
- Require NumPy, OpenCV, pyzmq, DLCLive, PyTorch, and the selected camera
  consumer for the AMD profile.
- Report `torch.__version__`, `torch.version.hip`,
  `torch.cuda.is_available()`, and the reported device name.
- Treat `torch.version.cuda` or installed `nvidia-*` distributions as a failure
  for the no-NVIDIA profile.
- Keep the existing TensorFlow/PySpin inventory available as a legacy profile.
- Add or adapt a focused AMD check instead of repurposing
  `Cam-Tests/CheckReqs.py` in a way that hides its TensorFlow purpose.
- Add a focused GenTL enumeration check that reports CTI path, producer,
  camera model, serial, and access errors without starting an unbounded stream.

### Phase 6: Decouple acquisition from PySpin

- In `Stream-DeepLabCut/dlc_eye_streamer.py`, make PySpin imports lazy and load
  them only when `--camera-backend pyspin` is selected.
- Add an explicit camera backend argument with at least `pyspin` and `gentl`.
- Preserve `pyspin` as the default initially to avoid silently changing existing
  deployments; the AMD setup documentation will select `gentl` explicitly.
- Extract the current PySpin camera setup and frame read into a backend object or
  focused helpers without changing `FramePacket` or the inference loop.
- Implement a GenTL/Harvesters backend that copies each buffer before returning
  it, releases buffers promptly, and uses newest-frame/drop semantics compatible
  with the current bounded queue.
- Map pixel format, sensor ROI, exposure, gain, frame rate, and buffer settings
  through GenICam nodes. Record requested and applied values exactly as the
  PySpin path does.
- Keep frame IDs monotonic and retain the current host capture timestamp units.
- Store the selected backend in the existing `camera_info` metadata object.
- Add an Aravis backend only if the Spinnaker GenTL route fails its camera smoke
  test on this host.
- Do not change inference, metrics, ZMQ, CSV, display, or coordinate logic while
  introducing the camera backend.

### Phase 7: Wire PyTorch models through all entrypoints

- Keep `DLCLive(..., model_type=args.model_type)` in the production inference
  loop and validate the existing `pytorch` choice with DLCLive 1.1.
- Update the production launcher to pass the camera backend explicitly.
- Support `.pt` model files in default model discovery without breaking legacy
  TensorFlow model directories.
- Update the camera-free model validator to accept or infer `base` versus
  `pytorch` and to validate both directory and `.pt` model paths.
- Add a GenTL + DLCLive timing smoke test, or generalize the existing FLIR smoke
  test if that remains readable and preserves the PySpin path.
- Confirm the PyTorch single-animal output shape before feeding it to the
  existing eight-point pupil metric code.
- Preserve grayscale/RGB preparation, crop translation, likelihood semantics,
  keypoint ordering, and the `yanglab-pupil8` preset.

### Phase 8: Produce and validate the PyTorch pupil model

- Recover or create a reviewed DLC project containing the eight pupil points in
  the exact production order.
- Set the project engine to PyTorch and create a PyTorch training shuffle.
- Start with a supported architecture that balances accuracy and live latency;
  benchmark the existing ResNet-50 equivalent and at least one lighter supported
  model before selecting the production network.
- Train and evaluate on the Radeon 8060S only after the ROCm environment passes
  inference validation. If local training is impractical, train elsewhere with
  PyTorch and validate the exported `.pt` model locally; the runtime must still
  remain NVIDIA-free.
- Export with `deeplabcut.export_model` to a `.pt` DLCLive model.
- Place the active export under `models/` without committing it.
- Compare the model against reviewed ground truth and, when available, the
  legacy TensorFlow model on the same frames.
- Review overlays for point-order swaps, coordinate offsets, crop errors, and
  confidence drift before live testing.

### Phase 9: Document the supported operating procedure

- Add one AMD/ROCm/FLIR setup document containing the exact tested OS, OEM
  kernel, ROCm, PyTorch, DeepLabCut, DLCLive, camera SDK, CTI, and model versions.
- Update the main and subsystem READMEs to link to that document rather than
  duplicating install commands.
- Update single- and two-computer quickstarts to stop assuming an NVIDIA driver.
- Document that `torch.cuda.*` API names are expected under ROCm and do not imply
  an NVIDIA dependency.
- Document the GenTL CTI path and the rule that only one camera consumer may own
  the camera at a time.
- Document the PySpin Python-version limitation and the Aravis fallback.
- Document all measured inference FPS and the exact sensor ROI/model used.

### Phase 10: Finalize planning records after implementation

- Update this plan's status to `Implemented` only after system, environment,
  camera, model, stream, and receiver validation are complete.
- Fill in the implementation summary with exact changed files and installed
  system/environment versions.
- Append one dated entry to `.agents/PLANS.md` with this plan path, changed
  files, validation, and unresolved follow-ups.

## Validation

### Pre-install and package-resolution validation

```bash
conda env create --dry-run --file environment.yaml
conda env list
apt-cache policy linux-oem-24.04
```

For the downloaded Spinnaker archive, inspect the actual package names before
forming the simulation command:

```bash
dpkg-deb -I /path/to/spinnaker-package.deb
sudo apt-get --simulate install /path/to/spinnaker-package.deb
```

### ROCm system validation

```bash
uname -r
groups
ls -l /dev/kfd /dev/dri/renderD128
rocminfo
```

Expected signals:

- Booted OEM kernel is the AMD-supported line.
- User belongs to `render` and `video`.
- `rocminfo` reports a GPU agent named `gfx1151`.
- `/dev/kfd` and `/dev/dri/renderD128` are accessible without root.

### Python AMD-backend validation

```bash
conda run -n dlclivegui python -c "import torch; print(torch.__version__); print(torch.version.hip); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
conda run -n dlclivegui python -m torch.utils.collect_env
conda list -n dlclivegui
python3 Cam-Tests/VerCheck.py --strict
```

Expected signals:

- `torch.version.hip` is populated.
- `torch.version.cuda` is `None`.
- `torch.cuda.is_available()` is `True` through ROCm.
- Device name identifies the AMD Radeon 8060S/AMD Radeon Graphics.
- No TensorFlow, `nvidia-*`, CUDA, cuDNN, or TensorRT distributions are present.
- DeepLabCut, DLCLive, OpenCV, pyzmq, and the chosen GenTL/Aravis consumer import.

The final `VerCheck.py` command should include the implemented AMD profile flag
if one is added.

### FLIR and camera validation

```bash
SpinView
python3 Stream-DeepLabCut/check_pyspin_camera.py
python3 Cam-Tests/GSTOCV.py --backend gstreamer --width 640 --height 480 --fps 120 --frames 120
```

Run only the command matching the selected backend. Add the planned GenTL
enumeration command and use it as the primary validation when GenTL is selected.

Expected signals:

- Exactly the intended camera is enumerated with model and serial.
- Non-root acquisition succeeds for at least 120 bounded frames.
- Applied ROI, pixel format, exposure, gain, and frame rate are reported.
- No image tearing, stale-frame backlog, unbounded timeout, or unreleased-buffer
  behavior is observed.

### Camera-free model validation

```bash
conda run -n dlclivegui python Train-Test-Model/validate_models_folder.py --model-path /absolute/path/to/model.pt --model-type pytorch
```

The exact CLI may change as part of the planned validator update. Validation
must confirm model load, first inference, output shape, point order, finite
coordinates, and likelihood range before camera access is introduced.

### Live camera and inference timing

```bash
conda run -n dlclivegui python Cam-Tests/smoke_dlc_gentl_inference.py --model-path /absolute/path/to/model.pt --model-preset yanglab-pupil8 --model-type pytorch --sensor-roi 0 0 640 480 --frames 120
```

If the existing smoke script is generalized instead of adding a new script, use
that script with the explicit camera backend. Record camera FPS, inference FPS,
initialization time, median/p95 inference latency, dropped frames, and GPU
memory/compute utilization.

### Production and receive-path validation

```bash
python3 Stream-DeepLabCut/run_eye_stream_production.py --help
python3 -m py_compile Stream-DeepLabCut/run_eye_stream_production.py Stream-DeepLabCut/dlc_eye_streamer.py
conda run -n dlclivegui python Stream-DeepLabCut/run_eye_stream_production.py --camera-backend gentl --model-type pytorch --model-path /absolute/path/to/model.pt
python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --duration 10
```

Expected signals:

- Stream starts with the AMD PyTorch model and selected camera backend.
- CSV and metadata sidecar are created under `/tmp/EyeTrack`.
- ZMQ sample and metadata schemas remain compatible with the receiver.
- MATLAB receive validation prints its documented success marker.
- Coordinate frame, point names, CSV columns, timestamp units, and default paths
  match the pre-change contract.

### Scientific equivalence validation

- Run legacy and PyTorch models on the same fixed, reviewed image set.
- Compare per-keypoint Euclidean error against ground truth.
- Compare likelihood distributions and threshold-crossing behavior.
- Compare pupil center and diameter outputs used downstream.
- Review overlays for every point and representative lighting/occlusion cases.
- Obtain explicit acceptance of numerical tolerances before designating the
  PyTorch model as production-active.

## Rollback and safety boundaries

- Keep the existing generic kernels installed and bootable while validating the
  OEM kernel.
- Use AMD's `--no-dkms` Ryzen path so the inbox `amdgpu` driver is not replaced.
- Do not remove working system graphics packages as part of the first ROCm
  attempt.
- Do not force-install Spinnaker packages with unresolved Ubuntu-version
  dependencies.
- Keep PySpin and GenTL/Aravis selectable until the replacement backend has
  passed real-camera timing tests.
- Keep the legacy TensorFlow model outside the AMD production environment for
  comparison and rollback if it becomes available.
- Do not change the active model path until scientific equivalence and live
  timing are accepted.
- Record every privileged package command and reboot boundary during
  implementation.

## Research sources

- [AMD Ryzen Linux support matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/compatibility/compatibilityryz/native_linux/native_linux_compatibility.html)
- [AMD Ryzen ROCm installation](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installryz/native_linux/install-ryzen.html)
- [AMD PyTorch for Ryzen installation](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installryz/native_linux/install-pytorch.html)
- [DeepLabCut 3 PyTorch guide](https://deeplabcut.github.io/DeepLabCut/docs/pytorch/user_guide.html)
- [DeepLabCut-Live repository and backend guide](https://github.com/DeepLabCut/DeepLabCut-live)
- [DeepLabCut-Live GUI installation](https://deeplabcut.github.io/DeepLabCut/docs/dlc-live/dlc-live-gui/quickstart/install.html)
- [DeepLabCut-Live camera backends](https://deeplabcut.github.io/DeepLabCut/docs/dlc-live/dlc-live-gui/user_guide/cameras_backends/camera_support.html)
- [Teledyne Spinnaker downloads](https://www.teledynevisionsolutions.com/products/spinnaker-sdk/GetResourcesSupportDownloads/)
- [Teledyne Spinnaker release notes](https://www.teledynevisionsolutions.com/support/support-center/technical-guidance/iis/spinnaker-sdk-release-notes/)
- [Teledyne PySpin installation guidance](https://www.teledynevisionsolutions.com/support/support-center/technical-guidance/iis/installing-pyspin-for-the-spinnaker-sdk/)
- [Teledyne Spinnaker GenTL producer guidance](https://softwareservices.flir.com/spinnaker/latest/_gen_i_cam_gen_t_l.html)
- [Teledyne Chameleon3 USB3 product resources](https://www.teledynevisionsolutions.com/products/chameleon3-usb3/)
- [Aravis USB3 Vision guidance](https://aravisproject.github.io/aravis/aravis-stable/usb.html)

## Implementation summary

Not implemented. This record contains research and an implementation plan only.
No packages, drivers, SDKs, conda environments, models, or runtime changes were
installed or created during planning.
