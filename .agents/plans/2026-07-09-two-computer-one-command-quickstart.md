# Two-Computer One-Command Quickstart

- Status: Implemented
- Created: 2026-07-09
- Last updated: 2026-07-15

## Goal

Add one behavior-computer entrypoint that turns the eye-stream portion of the
existing two-computer production startup sequence into a supervised,
one-command workflow. On the current lab rig, MATLAB/BehaviorBox may already
be open while the mouse warms up. When the operator is ready to begin eye
tracking, the normal invocation should be:

```bash
cd ~/Desktop/BehaviorBox/EyeTrack
./run_two_computer_eye_tracking.sh
```

The command should check prerequisites, start the remote streamer with its
X11-forwarded production display at 5 display FPS, start the local deferred
receiver, wait for verified readiness, and remain in the foreground supervising
those two services. The normal production invocation must not start MATLAB or
BehaviorBox. The operator starts the behavioral session in the independently
running MATLAB instance, saves and ends that session, and then presses `Ctrl+C`
in the supervisor terminal to stop the local receiver and request a graceful
remote streamer shutdown. Explicit smoke-test modes may start a temporary
MATLAB validation process, but never the BehaviorBox application.

The parent BehaviorBox repository's `startup.m` should provide guarded defaults
for `BB_EYETRACK_ZMQ_ADDRESS` and `BB_EYETRACK_RECEIVER_URL` every time the
BehaviorBox MATLAB startup runs. Explicit values already present in the MATLAB
process environment must remain authoritative.

## Runtime stages and execution path

The feature changes launcher/runtime wiring only. It composes these existing
paths rather than replacing their subsystem logic:

1. New behavior-host supervisor: `run_two_computer_eye_tracking.sh`.
2. Remote X11-forwarded streamer launch:
   `ssh_x11/start_eye_stream_over_ssh.sh` ->
   `Stream-DeepLabCut/run_eye_stream_production.py` ->
   `Stream-DeepLabCut/dlc_eye_streamer.py`.
3. Remote readiness and shutdown:
   `ssh_x11/eye_stream_status_over_ssh.sh` and
   `ssh_x11/stop_eye_stream_over_ssh.sh`.
4. Local receiver:
   `Stream-DeepLabCut/run_eye_receiver_service.py` ->
   `Stream-DeepLabCut/behavior_eye_receiver.py`.
5. Explicit optional/full receive validation:
   `Stream-DeepLabCut/run_matlab_eye_receive_test.py` ->
   `Stream-DeepLabCut/run_eye_stream_receive_test.m`.
6. Independent MATLAB/BehaviorBox configuration and consumer:
   parent `startup.m` -> guarded endpoint environment defaults ->
   `BehaviorBoxEyeTrack.tryCreateFromEnvironment()` when a BehaviorBox session
   begins.

## Active paths

Planned additions or edits:

- new `run_two_computer_eye_tracking.sh`
- new `ssh_x11/test_two_computer_supervisor.sh`
- `ssh_x11/start_eye_stream_over_ssh.sh`
- `README.md`
- `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Docs/SSH_X11_forwarding_PopOS.md`
- `Stream-DeepLabCut/README.md` only if its quickstart summary needs the new
  entrypoint
- parent BehaviorBox `startup.m`
- this working plan
- `.agents/PLANS.md` after implementation only

Existing runtime, receiver, and MATLAB implementation files should remain
unchanged unless implementation exposes a concrete missing interface that
cannot be handled safely by the supervisor. The SSH start wrapper is explicitly
in scope because its default display policy changes.

## Environment assumptions and defaults

The default profile targets the validated lab topology:

- behavior host: Linux graphical desktop at `10.55.0.2`
- eye host SSH target: `wbs@10.55.0.1`
- eye-stream endpoint: `tcp://10.55.0.1:5555`
- local receiver API: `http://127.0.0.1:8765`
- remote repo: `~/Desktop/BehaviorBox/EyeTrack`
- remote conda environment: `dlclivegui`
- local receiver interpreter:
  `~/miniforge3/envs/bbeyezmq/bin/python`
- model:
  `models/DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1`
- MATLAB executable for explicit smoke-test modes: `matlab`
- MATLAB/BehaviorBox production process: independently started and never owned
  by the EyeTrack supervisor
- local graphical display: inherited nonempty `DISPLAY`
- BehaviorBox root: parent of the EyeTrack repository, used for smoke tests and
  the project `startup.m`

Every rig-specific default must have a CLI override. `--help` must explain
which host each path and process belongs to.

## Contracts to preserve

- Explicit two-computer ZMQ endpoint remains `tcp://10.55.0.1:5555`.
- Receiver HTTP API remains local at `http://127.0.0.1:8765`.
- Streamer output remains paired CSV and metadata JSON under `/tmp/EyeTrack`.
- Receiver-managed chunk output and session lifecycle remain unchanged.
- Model lookup remains deterministic under `models/`; no model artifacts are
  copied, edited, or committed.
- Default camera settings remain sensor ROI `0 0 640 480`, target acquisition
  rate 60 FPS, exposure 6000 microseconds, and continuous auto gain.
- `ssh_x11/start_eye_stream_over_ssh.sh` defaults to `--display` when neither
  display flag is supplied, and its forwarded production display defaults to
  `--display-fps 5`. An explicit `--no-display` remains an intentional
  lower-level override outside the normal one-command workflow.
- The new supervisor requests `--display --display-fps 5` and defaults the
  production overlay to `--display-scale 2` for its normal run. A pass-through
  `--display-scale` argument may override that scale.
- Display FPS controls preview refresh cadence, not the requested camera rate.
  The acquisition target remains 60 FPS and the inference algorithm is
  unchanged, but the added X11/OpenCV display work may change observed camera
  FPS, inference FPS, or latency and must be measured during live validation.
- The X11-forwarded production window and its SSH connection must remain open;
  closing the window or losing the forwarded display may stop the streamer.
- No crop, acquired-frame coordinate, timestamp-unit, sample/metadata split,
  CSV-column, or ZMQ-field changes.
- The full smoke-test marker continues to require at least one valid eye
  sample; transport-only mode keeps its distinct marker.

## MATLAB boundary contract

The supervisor owns only the streamer and receiver. The parent BehaviorBox
`startup.m` supplies MATLAB-visible endpoint defaults, and the existing
`BehaviorBoxEyeTrack` discovery path reads them when a BehaviorBox session is
initialized. Neither path transforms payloads or MATLAB records. This changes
startup ownership, not the Python/MATLAB data contract.

| Boundary object | Owner | Type / units | Convention | Kind | Carrier |
| --- | --- | --- | --- | --- | --- |
| `frame_id` | Python streamer | integer frame number | no MATLAB reindexing | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| `capture_time_unix_s` | Python streamer | seconds since Unix epoch | remote capture clock | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| `publish_time_unix_s` | Python streamer | seconds since Unix epoch | remote publish clock | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| `center_x`, `center_y` | Python streamer | pixels | acquired-frame coordinates | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| `diameter_px` | Python streamer | pixels | acquired-frame scale | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| `confidence_mean` | Python streamer | unitless | unchanged numeric value | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| `latency_ms` | Python streamer | milliseconds | unchanged numeric value | dynamic sample | ZMQ JSON -> receiver chunk -> MATLAB table |
| stream metadata | Python streamer | JSON-compatible static values | ROI/crop/model provenance unchanged | static metadata | periodic ZMQ metadata and sidecar |
| `BB_EYETRACK_ZMQ_ADDRESS` | BehaviorBox `startup.m` | endpoint string | remote eye host; set only when empty | static configuration | MATLAB process environment |
| `BB_EYETRACK_RECEIVER_URL` | BehaviorBox `startup.m` | HTTP URL string | behavior-host localhost; set only when empty | static configuration | MATLAB process environment |
| production MATLAB process | operator | independent process | may start before mouse warm-up and eye services | startup control | outside supervisor lifecycle |

Contract before and after: no schema, dtype, unit, coordinate-frame, indexing,
or sample-versus-metadata change.

## Planned behavior

### Default invocation

`./run_two_computer_eye_tracking.sh` should:

1. Refuse to run from the eye host or when the local direct-link address does
   not match the behavior-host role, unless an explicit override is supplied.
2. Verify required local files, the receiver Python executable and `zmq`
   import, a nonempty local `DISPLAY`, SSH/X11 reachability, the remote
   repo/conda environment/model, and remote camera enumeration. Require MATLAB
   and the BehaviorBox root only for an explicit MATLAB smoke-test mode.
3. Refuse to overwrite unrelated listeners already using ports 5555 or 8765.
4. Start the existing remote streamer wrapper as a supervised background child
   using explicit production arguments, `--display`, and `--display-fps 5`.
5. Poll the existing remote status helper until the requested endpoint is
   listening, with a bounded timeout and an actionable error on failure.
6. Start the local receiver as a supervised background child with its log
   visible or written to a clearly reported temporary/log path.
7. Poll `http://127.0.0.1:8765/health` until the API is ready and the receiver
   reports the expected remote source address.
8. Report that eye tracking is ready and tell the operator to start the
   BehaviorBox session in the independently running MATLAB instance.
9. Remain in the foreground until `Ctrl+C`, another trapped shell termination,
   or a supervised service failure. Never invoke MATLAB or BehaviorBox.
10. Stop the exact receiver child and call the existing remote stop helper.
    Cleanup must be idempotent and must not target unrelated processes.

### Useful options

- `--check-only`: run all non-mutating preflight checks and exit.
- `--transport-test`: start the services, run the existing transport-only
  MATLAB validation harness, report its distinct success marker, and shut down.
- `--full-test`: run the valid-eye MATLAB validation harness and shut down.
- `--host`, `--address`, `--receiver-url`, `--remote-repo`, `--model-path`,
  `--receiver-python`, `--matlab-bin`, and `--behaviorbox-root`: override the
  lab defaults. The MATLAB and BehaviorBox options apply only to explicit smoke
  tests. A slash-containing relative `--matlab-bin` path is normalized before
  the smoke-test process changes into the BehaviorBox directory.
- Existing camera/display launcher options should be accepted only through a
  clearly delimited pass-through surface so supervisor options cannot be
  confused with streamer options.

The first implementation should remain a foreground supervisor. Persistent
detached services, boot-time startup, `systemd`, and GUI control panels are out
of scope until the foreground lifecycle is hardware-validated.

## Expected behavior differences

- Operators use one command instead of manually coordinating four terminals.
- Startup fails early with host-specific diagnostics if network, SSH, remote
  camera/model/environment, local receiver Python, X11, or ports are not ready.
  MATLAB readiness is checked only for explicit smoke-test modes.
- BehaviorBox's project startup supplies the correct two-computer endpoint
  variables inside every MATLAB session while preserving explicit overrides.
- MATLAB and BehaviorBox are started independently before or during mouse
  warm-up; the EyeTrack supervisor never starts or owns them.
- Normal startup opens the X11-forwarded production display at 5 display FPS.
- The operator stops the supervisor with `Ctrl+C` after ending and saving the
  BehaviorBox session; MATLAB exit no longer controls EyeTrack cleanup.
- Camera acquisition remains targeted at 60 FPS. Timing and latency definitions
  do not change, but their observed values may shift because the production
  display is now enabled. Coordinates, crop, CSV columns, metadata schema, ZMQ
  fields, output directories, and model contents do not change.

## Validation

Narrow static and command-surface checks:

```bash
bash -n run_two_computer_eye_tracking.sh
./run_two_computer_eye_tracking.sh --help
./run_two_computer_eye_tracking.sh --check-only
python3 Stream-DeepLabCut/run_eye_stream_production.py --help
python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --help
ssh_x11/start_eye_stream_over_ssh.sh --help
command -v matlab
git diff --check
```

Focused shell regression coverage should use fake SSH, receiver, HTTP-health,
MATLAB smoke-test, signal, and port-listener commands to verify:

- correct argument boundaries and host/path ownership
- startup order and readiness timeouts
- local versus remote failure messages
- refusal to reuse conflicting listeners
- the default production path never invokes MATLAB or BehaviorBox
- the default process remains in the foreground until a signal or service
  failure and then performs exact cleanup
- default SSH wrapper arguments include `--display --display-fps 5`, while an
  explicit lower-level `--no-display` remains respected
- explicit smoke-test modes still receive the configured MATLAB executable and
  BehaviorBox root
- cleanup after `Ctrl+C`, streamer failure, receiver failure, and smoke-test
  failure
- no termination of unrelated processes

MATLAB startup validation should run the parent `startup.m` in a clean batch
process, verify both defaults, and verify pre-set alternate values are not
overwritten.

Hardware validation on the current two-machine rig:

```bash
./run_two_computer_eye_tracking.sh --check-only
./run_two_computer_eye_tracking.sh --transport-test
./run_two_computer_eye_tracking.sh --full-test
./run_two_computer_eye_tracking.sh
```

During live validation, confirm:

- the eye host sees camera serial `24251567` and a TensorFlow GPU
- the streamer listens on `10.55.0.1:5555`
- the forwarded production overlay appears and refreshes at no more than 5 FPS
- measured camera FPS, inference FPS, and latency remain acceptable with the
  forwarded production display enabled
- the receiver health API reports the expected source endpoint
- streamer CSV/metadata files appear under remote `/tmp/EyeTrack`
- running the supervisor does not create a new MATLAB process
- the already-running MATLAB instance has the startup-provided endpoint values
  and `BehaviorBoxEyeTrack.discoverSource()` finds the receiver
- BehaviorBox imports finalized receiver chunks after the operator starts a new
  session
- `Ctrl+C` after BehaviorBox save stops both supervised services without
  stopping MATLAB

## Implementation summary

Implemented on 2026-07-10 on the two-computer Linux rig.

### Delivered

- Added the root `run_two_computer_eye_tracking.sh` foreground supervisor with
  local locking, role/route checks, SSH/X11 validation, remote model/environment
  and camera checks, process/port ownership refusal, bounded readiness polling,
  per-run logs, and exact local child tracking.
- The supervisor starts the remote streamer at the explicit two-computer
  address with `--display --display-fps 5`, starts the local receiver, and waits
  for receiver health plus at least one sample before continuing.
- Added `--check-only`, `--transport-test`, and `--full-test` modes plus
  documented rig/path overrides and a delimited streamer-argument surface. The
  configured address and display requirements are appended last so pass-through
  arguments cannot override them accidentally.
- A 2026-07-10 lifecycle follow-up made the default mode service-only. It never
  launches, requires, or stops MATLAB/BehaviorBox; it remains in the foreground
  until `Ctrl+C` or a supervised service failure. The former `--no-matlab`
  option is redundant and was removed.
- Explicit `--transport-test` and `--full-test` diagnostics retain their
  temporary MATLAB validation process. MATLAB executable and BehaviorBox-root
  preflight is now restricted to those modes.
- The parent BehaviorBox `startup.m` now supplies guarded two-computer endpoint
  defaults on MATLAB startup while preserving values already present in the
  process environment. BehaviorBox continues to discover the receiver only
  when a training or mapping session begins.
- After a signal, service failure, or smoke test exits, cleanup signals the exact receiver PID,
  invokes remote stop only for a supervisor-owned launch, waits with bounded
  fallbacks, and terminates only the supervisor-owned SSH process group if the
  wrapper remains.
- Changed `ssh_x11/start_eye_stream_over_ssh.sh` so unspecified display mode
  defaults to X11 `--display` and unspecified displayed refresh defaults to
  `--display-fps 5`; explicit `--no-display` and explicit display FPS remain
  respected.
- The root supervisor now passes `--display-scale 2` by default while keeping
  an explicit pass-through display-scale override available.
- Added fake-process/signal regression coverage and updated the root, runtime,
  single-computer, two-computer, SSH/X11, and parent BehaviorBox documentation.

No coordinate, crop, timestamp, sample/metadata, CSV-column, metadata-schema,
ZMQ-field, `/tmp/EyeTrack`, receiver API, or model-content contract changed.

### Validation

- `bash -n run_two_computer_eye_tracking.sh ssh_x11/*.sh` passed.
- `bash ssh_x11/test_ssh_x11_wrappers.sh` passed with
  `SSH_X11_WRAPPERS_OK`, including default display/FPS, missing-DISPLAY, explicit
  headless, and custom-FPS cases.
- `bash ssh_x11/test_two_computer_supervisor.sh` passed with
  `TWO_COMPUTER_SUPERVISOR_OK`. It covers non-starting preflight without a
  MATLAB executable or BehaviorBox root, remote preflight failure, listener
  refusal, enforced streamer arguments, default service-only supervision,
  proof that production does not invoke MATLAB, signal cleanup, explicit
  transport and full-test modes, exact cleanup, and no child leaks.
- MATLAB batch checks printed `BEHAVIORBOX_EYETRACK_STARTUP_DEFAULTS_OK` and
  `BEHAVIORBOX_EYETRACK_STARTUP_OVERRIDES_OK`, proving that parent `startup.m`
  supplies both defaults and preserves pre-set alternatives.
- All seven parent `testBehaviorBoxEyeTrackReceiverContract` tests passed with
  `BEHAVIORBOX_EYETRACK_RECEIVER_CONTRACT_OK`.
- A new live `--check-only` attempt was ownership-safely refused because the
  operator's existing supervisor held the single-instance lock. Read-only
  inspection confirmed its receiver was healthy at the expected endpoint,
  actively recording a BehaviorBox session, and receiving samples; remote
  status confirmed the production streamer, 5 FPS display, and listener on
  `10.55.0.1:5555`. No live process was changed or stopped.
- A real `--transport-test` on temporary ports 5556/8766 passed with
  `MATLAB_EYE_STREAM_TRANSPORT_OK`, 674 MATLAB samples, 673 valid samples, and
  verified automatic cleanup.
- A real `--full-test` on temporary ports 5557/8767 passed with
  `MATLAB_EYE_STREAM_RECEIVE_OK`, 673 MATLAB samples, 635 valid samples, and
  verified automatic cleanup.
- Stream metadata recorded `display_enabled=true`, `display_fps=5.0`, requested
  camera rate 60 FPS, and the temporary ZMQ endpoint. The transport run measured
  median camera FPS 60.043, median inference FPS 60.049, and median latency
  15.232 ms across 1,307 streamer rows.
- CLI help checks, relative Markdown link checks, stale lifecycle/display
  guidance scans, and whitespace checks passed. `shellcheck` was not installed.

### 2026-07-15 Display Scale Follow-up

- Updated the normal root supervisor production arguments to include
  `--display-scale 2` before pass-through streamer arguments, so the default
  overlay is twice the native display dimensions while an explicit override
  remains possible.
- The active live session was not restarted by this change. Its current
  `inference_fps` is about 7 while `camera_fps` remains about 60 because the
  remote TensorFlow process reports a CUDA driver/kernel mismatch; that is an
  environment issue separate from display scale.

### Remaining risks and follow-up

- The new default service-only code was not started on the real ports because an
  active behavior session already owned them. Run the next production session
  without the removed `--no-matlab` flag and confirm the normal operator
  lifecycle once the current session is safely saved and stopped.
- The project `startup.m` runs automatically only when it is discoverable on
  MATLAB's startup path. Start MATLAB from the BehaviorBox root for this lab
  workflow. An already-running MATLAB needs manual `setenv` once; future
  BehaviorBox-root startups get the defaults automatically.
- Single-computer runs must explicitly override `BB_EYETRACK_ZMQ_ADDRESS` to
  `tcp://127.0.0.1:5555` before the BehaviorBox session begins.
- A BehaviorBox session that begins before receiver readiness does not hot-attach
  later. Start eye services and wait for readiness before beginning the session.
- MATLAB no longer signals EyeTrack shutdown. The operator must wait for the
  BehaviorBox save/import to finish before pressing `Ctrl+C` in the supervisor.
- Closing the forwarded OpenCV window or losing X11 can stop the streamer by
  design. The supervisor reports the service failure and does not terminate
  MATLAB.
- Same-host supervisor concurrency is locked. Another behavior host could still
  race between remote preflight and launch; the remote port/process checks make
  the window small but cannot make cross-host ownership atomic.
