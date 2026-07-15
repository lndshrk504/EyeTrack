# EyeTrack SSH/X11 And Documentation Remediation Plan

- Status: Implemented
- Created: 2026-07-09
- Last updated: 2026-07-09

## Goal

Resolve the SSH/X11, receive-test, metadata, provenance, and documentation
defects found during the 2026-07-09 review of `ssh_x11/` and `Docs/`.

The completed change must make the documented commands safe to run, make
status and validation results mean what they say, and preserve enough runtime
metadata to audit how each eye-tracking session was acquired.

## Review Findings Covered

| ID | Finding | Required outcome |
| --- | --- | --- |
| F1 | SSH pass-through arguments are re-parsed by the remote shell | Preserve every argument boundary and treat spaces and shell metacharacters as literal data |
| F2 | `setup_eye_host_ssh_x11.sh --conf-file` can write an inactive or arbitrary root-owned file | Restrict the target to an active SSH drop-in, write atomically, validate, and roll back on failure |
| F3 | The MATLAB receive test finds the BehaviorBox root only through hidden MATLAB path state | Resolve or accept the BehaviorBox root explicitly and fail with an actionable path error |
| F4 | A stream containing only `no_points` samples can print `MATLAB_EYE_STREAM_RECEIVE_OK` | Separate transport success from valid-eye success and require valid samples for the full smoke test |
| F5 | MATLAB metadata drops or mislabels streamer metadata and file paths | Preserve the complete static stream metadata and distinguish streamer files from receiver chunk files |
| F6 | Two-computer MATLAB sessions can record localhost as the source endpoint | Reconcile the configured address with the receiver's effective address and save both when they differ |
| F7 | The two-computer minimal command block puts a foreground receiver and its test in one shell | Split the receiver, smoke test, and MATLAB startup into separate terminals or services |
| F8 | The default X11 check can pass without opening the forwarded display | Require a real noninteractive X client probe before reporting success |
| F9 | Status and stop helpers can report misleading success | Make status honor configured paths/endpoints and make stop wait, verify, and return nonzero on failure |
| F10 | The documented remote output override expands `~` on the behavior computer | Preserve a literal remote-home path or use an explicit remote absolute path |

## Active Paths And Ownership

### EyeTrack repository

Active implementation paths:

- `ssh_x11/start_eye_stream_over_ssh.sh`
- `ssh_x11/open_alignment_preview_over_ssh.sh`
- `ssh_x11/open_training_capture_over_ssh.sh`
- `ssh_x11/stop_eye_stream_over_ssh.sh`
- `ssh_x11/eye_stream_status_over_ssh.sh`
- `ssh_x11/test_x11_forwarding_over_ssh.sh`
- `ssh_x11/setup_eye_host_ssh_x11.sh`
- new `ssh_x11/ssh_x11_common.sh`
- new `ssh_x11/test_ssh_x11_wrappers.sh`
- `Stream-DeepLabCut/dlc_eye_streamer.py`
- `Stream-DeepLabCut/behavior_eye_receiver.py`
- `Stream-DeepLabCut/test_behavior_eye_receiver.py`
- `Stream-DeepLabCut/run_eye_stream_receive_test.m`
- `Stream-DeepLabCut/run_matlab_eye_receive_test.py`
- new `Stream-DeepLabCut/test_matlab_eye_receive_contract.py`
- `Stream-DeepLabCut/setup_two_computer_eye_link.sh`
- `Docs/README_eye_stream.md`
- `Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Docs/SSH_X11_forwarding_PopOS.md`
- `Docs/Capture-FLIR-Images-Over-SSH.md`
- `README.md` and `Stream-DeepLabCut/README.md` only where
  their summaries repeat a corrected contract

### BehaviorBox repository

Active implementation paths:

- `BehaviorBoxEyeTrack.m`
- new `tests/testBehaviorBoxEyeTrackReceiverContract.m`
- `startup.m` only as a validation input; do not broaden its path behavior

### Out of scope

- No model replacement or model blob changes.
- No camera ROI, crop, coordinate-frame, timestamp, FPS, or latency changes.
- No change to the BehaviorBox trial, mapping, reward, or display loops.
- No rewrite of the receiver API or replacement of ZeroMQ.
- No package installation during implementation. A live host may use an
  explicitly approved install step only if the required X probe utility is
  absent.

## Behavior Changes To Declare Before Implementation

The implementation is expected to change these observable behaviors:

1. SSH wrapper values containing spaces, quotes, globs, `$()`, semicolons,
   redirects, or other shell syntax will arrive remotely as literal arguments.
2. Unsafe `--conf-file` values will be rejected before privilege escalation or
   file writes.
3. The X11 test will fail when it cannot open the forwarded display, even when
   `DISPLAY` and `xauth` look plausible.
4. The full MATLAB receive test will fail for `no_points`-only streams. A
   separate transport-only mode will remain available for diagnosing ZMQ and
   receiver connectivity without an eye in frame.
5. `EyeTrackingMeta.Address` will describe the receiver's effective source
   endpoint after connection. The originally configured value and any mismatch
   will be retained explicitly.
6. `EyeTrackingMeta.StreamMetadata` and receiver session metadata will gain
   additive static fields. Existing dynamic sample fields and CSV columns will
   not change.
7. Stop/status commands will return nonzero when they cannot verify their
   requested outcome.
8. An optional detached headless start mode may create a PID/state file and
   remote log. Foreground behavior remains the default for compatibility.

## Contracts To Preserve

- Default streamer/receiver ZMQ endpoint: `tcp://127.0.0.1:5555`.
- Explicit two-computer endpoint: `tcp://10.55.0.1:5555`.
- Default receiver API URL: `http://127.0.0.1:8765`.
- Default streamer output directory: `/tmp/EyeTrack`.
- Default training-frame output root: `~/Desktop/EyeTrackTrainingFrames` on
  the eye-tracking computer.
- MATLAB-visible dynamic fields:
  `frame_id`, `capture_time_unix_s`, `publish_time_unix_s`, `center_x`,
  `center_y`, `diameter_px`, `confidence_mean`, and `latency_ms`.
- The sample-versus-metadata split.
- Receiver-managed chunk CSVs and metadata JSON remain the durable BehaviorBox
  ingest artifacts.
- `EyeTrackingMeta.CsvPath` and `EyeTrackingMeta.MetadataPath` remain receiver
  chunk paths for compatibility; documentation and console labels must say so.
- Streamer-side CSV and sidecar paths live under
  `EyeTrackingMeta.StreamMetadata.csv_path` and
  `EyeTrackingMeta.StreamMetadata.metadata_path`.
- Saved eye coordinates remain acquired-frame coordinates.
- Model placement remains deterministic under `models/`.
- Foreground SSH launch remains available and keeps its current default.

## Contract Reconciliation

### Readiness contract

| Concept | Before | After |
| --- | --- | --- |
| Receiver transport activity | `samples_received > 0` is exposed indirectly as `IsReady` | Keep this meaning, but label it transport/sample readiness |
| Valid eye sample | Not a separate receive-test criterion | Count rows where `is_valid` is true, or equivalently status is `ok`/`partial_points` with finite center and positive valid-point count |
| Full receive-test pass | Any rows plus expected columns | Minimum total rows, expected columns, and minimum valid rows |
| No-eye transport diagnosis | Can accidentally pass the full test | Explicit `--transport-only` mode with a distinct success marker |

`MATLAB_EYE_STREAM_RECEIVE_OK` must mean that at least the configured minimum
number of valid eye samples reached MATLAB. Transport-only success should print
`MATLAB_EYE_STREAM_TRANSPORT_OK` and must not print the full success marker.

### Static metadata contract

The streamer should build one common static metadata object used by both the
periodic ZMQ metadata message and the local sidecar. The ZMQ message may omit
the sidecar-only CSV column list, but it must include the acquisition and model
provenance needed downstream:

- a new additive `stream_metadata_version`
- source name and effective ZMQ address
- streamer CSV and streamer sidecar paths
- model path, preset, type, and keypoint mapping
- point names, point count, and `pcutoff`
- camera index, model, serial, and pixel format
- requested and applied sensor ROI
- pose coordinate frame and fixed crop
- requested and applied exposure, gain, gain-auto mode, and frame rate
- display settings and dynamic-crop settings
- metadata interval and publisher high-water mark

The existing sample `schema_version` remains unchanged because sample fields are
unchanged. `stream_metadata_version` versions the additive static contract.

The receiver must retain this metadata without silently discarding known
fields. It must expose the current snapshot through `/health` and persist a
snapshot in `receiver_session.json`. Later periodic metadata should refresh the
active session snapshot before finalization.

### Source endpoint contract

`BehaviorBoxEyeTrack` should retain three concepts:

- `ConfiguredAddress`: constructor/environment value before receiver contact
- `ReceiverAddress`: effective address reported by receiver `/health`
- `Address`: effective address used for saved provenance

Add `AddressMismatch` to saved metadata. After a successful health response,
derive `SourceHost`, `SourcePort`, and `SourceMode` from `ReceiverAddress`. If a
nonempty configured value differs, warn once and retain both values. If the
receiver does not advertise an address, preserve the configured fallback.

The MATLAB receive test must stop forcing `SourceMode="localhost"`; it should
infer the mode from the supplied/effective address.

## Planned Edits And Implementation Sequence

### Phase 1: Add regression tests before behavior changes

1. Add `ssh_x11/test_ssh_x11_wrappers.sh` or an equivalently focused shell
   harness.
2. Put a fake `ssh` executable first on `PATH`. It should reproduce OpenSSH's
   documented command joining and the remote login-shell parse without making a
   network connection.
3. Demonstrate the current failure with:
   - a remote repository path containing spaces
   - a conda path containing spaces
   - a `--session-name` or window name containing spaces
   - literal glob characters
   - literal `$()`, semicolon, quote, and redirect characters
   - the default literal `~/...` paths
4. Assert that no sentinel command embedded in a value executes.
5. Extend `test_behavior_eye_receiver.py` with metadata containing ROI, crop,
   camera settings, model path, display settings, dynamic crop, and both
   streamer file paths. Assert the current drop, then update the expectation
   with the implementation.
6. Add a `no_points` sample fixture and a valid sample fixture.
7. Add `tests/testBehaviorBoxEyeTrackReceiverContract.m` using the existing
   `functiontests(localfunctions)` style. Use `ClientAdapter` or another local
   fake so the test does not require hardware.

### Phase 2: Make SSH argument transport literal and testable

1. Add `ssh_x11/ssh_x11_common.sh` for producing one POSIX-shell-safe remote
   command string from an argv array. Do not use `eval`.
2. Encode each argument with a portable single-quote strategy, including the
   embedded-single-quote case. Send one command string to `ssh` so OpenSSH does
   not destroy argument boundaries.
3. Apply the helper to:
   - `start_eye_stream_over_ssh.sh`
   - `open_alignment_preview_over_ssh.sh`
   - `open_training_capture_over_ssh.sh`
   - `stop_eye_stream_over_ssh.sh`
4. Correct the remote `expand_path` implementation so a now-literal `~/...`
   removes the literal `~/` prefix exactly once and expands against the remote
   `$HOME`.
5. Add explicit missing-value checks before every option access to prevent
   `set -u` from producing an unhelpful `$2` error.
6. Preserve the `--` pass-through boundary exactly and verify that the Python
   target receives byte-for-byte-equivalent ordinary shell strings.

Acceptance gate:

- all special-value fixtures reach the remote stub as one argument
- no sentinel command executes
- default remote repository and conda paths resolve under the remote test HOME
- existing simple commands remain unchanged

### Phase 3: Make SSH host setup transactional and constrained

1. Keep `--conf-file` only if it is constrained to a canonical file ending in
   `.conf` directly under `/etc/ssh/sshd_config.d`.
2. Reject symlinks, parent traversal, the main `sshd_config`, and paths outside
   the active include directory.
3. Verify the main configuration includes the allowed drop-in glob before any
   write.
4. Run `sshd -t` before changing anything so an unrelated existing error is not
   attributed to EyeTrack.
5. Stage the two EyeTrack directives in a root-owned temporary file, use fixed
   mode/ownership, and atomically install the final drop-in.
6. If post-install `sshd -t` fails, restore the previous file or remove the new
   file, revalidate the restored configuration, and do not restart SSH.
7. Verify effective values with `sshd -T` before reporting completion:
   `x11forwarding yes` and `x11uselocalhost yes`.
8. Restart SSH only after syntax and effective-value checks pass.
9. Add `--dry-run` so path validation and intended actions can be reviewed
   without privilege escalation or writes.
10. Keep package installation behind the existing explicit
    `--install-missing` flag.

Acceptance gate:

- an unsafe path is rejected in dry-run mode
- a path outside the included directory cannot be written
- a failed syntax check restores the previous state
- success means `sshd -T` reports both required effective settings

### Phase 4: Make X11 and process operations truthful

#### X11 probe

1. Keep the local and remote `DISPLAY` checks and the remote `xauth` check.
2. Require a noninteractive X request with `xdpyinfo` or `xset q`.
3. If neither probe exists, fail with an actionable message rather than print a
   pass. Do not silently install anything.
4. Keep `--try-xclock` as an optional human-visible test after the mandatory
   probe.
5. Document that `ssh -Y` grants trusted X11 access and should only be used with
   a trusted eye host on the private link.

#### Status and stop

1. Add status options matching the launcher's configurable surface, at minimum
   `--address` or `--port` and `--csv-dir`, with existing defaults preserved.
2. Report the exact endpoint and directory being checked.
3. Add `--timeout-s` to stop, poll until all targeted processes exit, and return
   nonzero if they remain.
4. Do not send `SIGKILL` by default. If a force option is added, make it explicit
   and document the camera-cleanup tradeoff.
5. Ensure a no-process condition is distinguishable from a successful stop of
   an active process.

#### Optional detached headless mode

1. Add `--detach` only for headless production mode; reject it with `--display`.
2. Use a new process group, a PID/PGID file, and an explicit remote log so an SSH
   disconnect does not ambiguously own the stream lifetime.
3. Verify the process remains alive before reporting detached-start success.
4. Teach status and stop to prefer the state file and exact process group.
5. Keep foreground mode as the default and preserve Ctrl+C behavior.

Acceptance gate:

- a failed X client request fails the X11 test
- custom endpoint/output status checks do not produce false negatives
- stop returns zero only after verified exit
- if detached mode is implemented, a client disconnect does not stop the
  streamer and the stop helper still performs graceful cleanup

### Phase 5: Repair streamer-to-receiver metadata preservation

1. Refactor `dlc_eye_streamer.py` so periodic metadata and sidecar metadata use
   one common static metadata builder.
2. Add `stream_metadata_version` and the static fields listed in the contract
   section.
3. Keep dynamic sample messages and streamer CSV columns unchanged.
4. Replace the receiver's partial metadata allowlist with an explicit complete
   static contract or a safely filtered copy of metadata messages.
5. Do not copy dynamic sample fields into `stream_metadata`.
6. Include the current stream metadata snapshot in receiver health.
7. Add the snapshot to `SessionState` and persist it in
   `receiver_session.json`; update it when later metadata arrives.
8. Preserve receiver chunk `csv_path` and `metadata_path` fields as receiver
   paths. Do not overwrite them with streamer paths.

Acceptance gate:

- every expected static field survives streamer -> receiver health -> receiver
  session JSON
- streamer and receiver file paths are simultaneously available and cannot be
  confused by name or label
- existing sample rows and CSV headers are byte-for-byte compatible

### Phase 6: Repair MATLAB discovery, provenance, and smoke semantics

#### BehaviorBox root discovery

1. Add a `BehaviorBoxRoot` option to `run_eye_stream_receive_test.m`.
2. When omitted, derive the default as the parent of the EyeTrack repository,
   not the parent of the desktop directory.
3. Validate that `BehaviorBoxEyeTrack.m` exists before calling `addpath`.
4. Add `--behaviorbox-root` to `run_matlab_eye_receive_test.py` and pass the
   resolved value explicitly.
5. Fail with a dedicated error containing the checked path when the class is
   absent. Do not depend on a previously saved MATLAB path or automatic
   `startup.m` state.
6. Keep path setup narrow: add the BehaviorBox root and run its explicit
   `startup.m`; do not add `genpath`.

#### Effective source provenance

1. Add `ConfiguredAddress`, `ReceiverAddress`, and `AddressMismatch` state and
   saved metadata to `BehaviorBoxEyeTrack`.
2. In `applyHealthPayload_`, read the receiver's advertised address, parse it,
   and update effective `Address`, `SourceHost`, `SourcePort`, and `SourceMode`.
3. Warn once on mismatch while retaining both values.
4. Remove the hardcoded localhost source mode from
   `run_eye_stream_receive_test.m`.

#### Receive-test criteria

1. Add `MinValidSamples` with a default of `1`.
2. Add an explicit transport-only option for intentional no-eye diagnostics.
3. Count valid rows from the persisted `is_valid` column and verify the status,
   finite center, and valid-point count remain internally consistent.
4. Return and print both `transport_ok` and `valid_sample_count`.
5. Reserve `MATLAB_EYE_STREAM_RECEIVE_OK` for full valid-eye success.
6. Correct path labels:
   - `meta.CsvPath` / `meta.MetadataPath`: receiver chunk files
   - `meta.StreamMetadata.csv_path` / `.metadata_path`: streamer files

Acceptance gate:

- a clean MATLAB path finds `BehaviorBoxEyeTrack` using only the supplied or
  derived root
- a two-computer address infers `SourceMode="remote"`
- a receiver/config mismatch is visible and both addresses are saved
- no-points-only input fails the full test but passes transport-only mode
- valid input passes the full test

### Phase 7: Correct all operator documentation

Update the five reviewed docs and any repeated root/runtime README summaries.

Required documentation changes:

1. State the exact local-versus-remote role for every command block.
2. Split the two-computer minimal workflow into:
   - terminal A: receiver service
   - terminal B: receive smoke test
   - terminal C: MATLAB/BehaviorBox
3. Export both variables before two-computer MATLAB startup:

   ```bash
   export BB_EYETRACK_ZMQ_ADDRESS=tcp://10.55.0.1:5555
   export BB_EYETRACK_RECEIVER_URL=http://127.0.0.1:8765
   ```

4. Define transport readiness separately from a valid-eye smoke pass.
5. Explain the full and transport-only success markers.
6. Describe `EyeTrackingMeta.CsvPath` and `.MetadataPath` as receiver chunk
   paths and document the streamer equivalents under `StreamMetadata`.
7. Quote the remote output example so `~` reaches the remote process literally:

   ```bash
   --output-dir '~/Desktop/EyeTrackTrainingFrames'
   ```

8. Document matching status options when a nondefault endpoint or CSV directory
   is used.
9. Document foreground SSH lifetime, optional detached mode if implemented,
   state/log locations, and shutdown verification.
10. Document the trusted-X11 security boundary and the mandatory display probe.
11. Keep installation commands clearly separated from validation commands.

## Validation Plan

### Static shell validation

```bash
bash -n ssh_x11/*.sh
bash ssh_x11/test_ssh_x11_wrappers.sh
for script in ssh_x11/*.sh; do "$script" --help >/dev/null; done
git diff --check
```

Run `shellcheck -x ssh_x11/*.sh` if `shellcheck` is already installed. Do not
install it as part of this change.

### Python validation

```bash
python3 -m py_compile \
  Stream-DeepLabCut/dlc_eye_streamer.py \
  Stream-DeepLabCut/behavior_eye_receiver.py \
  Stream-DeepLabCut/run_matlab_eye_receive_test.py \
  Stream-DeepLabCut/test_behavior_eye_receiver.py

$HOME/miniforge3/envs/bbeyezmq/bin/python \
  Stream-DeepLabCut/test_behavior_eye_receiver.py

python3 Stream-DeepLabCut/run_eye_stream_production.py --help
python3 Stream-DeepLabCut/run_matlab_eye_receive_test.py --help
```

The receiver test must cover metadata round-trip, receiver/streamer path
separation, a `no_points` row, and a valid row.

### MATLAB validation

From the BehaviorBox repository:

```bash
matlab -batch "results=runtests('tests/testBehaviorBoxEyeTrackReceiverContract.m'); assertSuccess(results);"
```

Add `Stream-DeepLabCut/test_matlab_eye_receive_contract.py` as a camera-free
end-to-end contract test using the receiver's debug endpoint:

1. launch a receiver on dynamic localhost ports
2. launch MATLAB from a clean path
3. publish metadata and only `no_points` samples
4. verify full mode fails and transport-only mode passes
5. repeat with valid samples and verify full mode passes
6. inspect the saved MAT and receiver session JSON for both effective source
   addresses and the complete static metadata snapshot

### Documentation validation

```bash
rg -n "CSV path advertised by streamer|Metadata path advertised by streamer|Ready: 1" Docs Stream-DeepLabCut
rg -n "run_eye_receiver_service.py|run_matlab_eye_receive_test.py|matlab" Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md
rg -n "BB_EYETRACK_ZMQ_ADDRESS|BB_EYETRACK_RECEIVER_URL" Docs README.md
git diff --check
```

Also validate every relative Markdown link and compare every documented option
against the corresponding `--help` output.

### Live two-host validation

Run only after static, Python, and camera-free MATLAB validation pass.

Eye host prerequisites:

- Pop!_OS/Ubuntu SSH service
- approved SSH drop-in maintenance window or console access
- remote `dlclivegui` environment
- FLIR camera and exported model
- an available actual X client probe

Sequence:

1. Run setup dry-run and review the exact drop-in path and firewall actions.
2. Apply setup, then run `sudo sshd -t` and verify effective values with
   `sudo sshd -T`.
3. From the behavior computer, run the X11 test and require the real probe to
   succeed.
4. Open and close the alignment preview.
5. Open training capture with a spaced session name and a quoted remote-home
   output path; verify the exact remote output location.
6. Start the production stream headless with the two-computer endpoint.
7. If detached mode is implemented, disconnect and reconnect SSH and confirm
   the stream remains active.
8. Run status using the effective endpoint and output directory.
9. Start the receiver on the behavior computer and run the full MATLAB receive
   test with an eye in frame.
10. Verify the receiver health payload, receiver session JSON, and MATLAB meta
    agree on the effective source address and static acquisition metadata.
11. Stop the stream and confirm the stop command returns zero only after both
    launcher and streamer have exited.

## Rollout And Recovery

1. Land regression tests and non-root changes before applying any SSH daemon
   configuration on the eye host.
2. Keep foreground stream startup as the compatibility default.
3. Treat metadata additions as backward-compatible; do not remove or rename
   existing sample fields or receiver chunk fields.
4. Back up the existing EyeTrack SSH drop-in during setup and restore it
   automatically on validation failure.
5. Do not use a forced process kill until graceful stop has timed out and the
   operator explicitly requests force.
6. Keep the previous docs commands available in git history; do not leave two
   contradictory active workflows in current docs.

## Definition Of Done

- Every F1-F10 row has a regression test or a deterministic validation check.
- SSH arguments with spaces and metacharacters are preserved literally.
- Unsafe SSH config paths cannot be written.
- X11 success includes a real display-open request.
- A no-points-only stream cannot emit the full MATLAB success marker.
- Complete static stream metadata reaches receiver health, receiver session
  JSON, and MATLAB `StreamMetadata`.
- Receiver and streamer file paths are both available and clearly labeled.
- Saved MATLAB source provenance matches the receiver's effective endpoint.
- The two-computer quickstart can be followed top to bottom without a blocked
  command sequence.
- Status and stop results are accurate for default and documented custom
  configurations.
- Static, Python, MATLAB, and live two-host validations are recorded with exact
  commands and short results.
- The EyeTrack working plan is marked `Implemented` and `.agents/PLANS.md` is
  appended only after all required implementation and validation work lands.

## Implementation Summary

Implemented on 2026-07-09 on the local Linux behavior host.

### Delivered

- Added literal, POSIX-safe SSH argument serialization and regression coverage
  for spaces, quotes, globs, command substitutions, redirects, and remote-home
  paths.
- Constrained SSH drop-in writes to the active include directory, added a
  nonprivileged dry run, made install/validation/restart transactional, and
  preserved the prior backup even if automatic restoration itself fails.
- Made X11 success require a real `xdpyinfo` or `xset` display request.
- Made status verify that a matching EyeTrack PID owns a listener serving the
  requested host and port. Made stop canonicalize the repository path, match
  both relative launchers and absolute streamer children, poll for exit, and
  fail on timeout.
- Unified periodic and sidecar static metadata, added
  `stream_metadata_version=1`, requested/applied camera provenance, model and
  keypoint provenance, display/crop settings, and distinct streamer file paths.
  The receiver now exposes and persists the filtered static snapshot without
  letting sample fields overwrite it.
- Added explicit BehaviorBox-root discovery, receiver-effective address
  reconciliation, mismatch provenance, a valid-eye minimum for the full MATLAB
  smoke test, and a separately marked transport-only mode.
- Corrected the operator docs and generated two-computer handoff text so the
  receiver, smoke test, and MATLAB run in separate terminals with both source
  environment variables set.

Timing, FPS, timestamp units, acquired-frame coordinate semantics, fixed and
dynamic crop behavior, dynamic sample fields, streamer and receiver CSV
columns, default endpoints, `/tmp/EyeTrack`, and model-path conventions were
not changed. Foreground SSH launch remains the default. The optional detached
mode was not implemented.

### Changed Files

EyeTrack repository:

- `ssh_x11/ssh_x11_common.sh`
- `ssh_x11/test_ssh_x11_wrappers.sh`
- `ssh_x11/start_eye_stream_over_ssh.sh`
- `ssh_x11/open_alignment_preview_over_ssh.sh`
- `ssh_x11/open_training_capture_over_ssh.sh`
- `ssh_x11/setup_eye_host_ssh_x11.sh`
- `ssh_x11/test_x11_forwarding_over_ssh.sh`
- `ssh_x11/eye_stream_status_over_ssh.sh`
- `ssh_x11/stop_eye_stream_over_ssh.sh`
- `Stream-DeepLabCut/dlc_eye_streamer.py`
- `Stream-DeepLabCut/behavior_eye_receiver.py`
- `Stream-DeepLabCut/test_behavior_eye_receiver.py`
- `Stream-DeepLabCut/run_eye_stream_receive_test.m`
- `Stream-DeepLabCut/run_matlab_eye_receive_test.py`
- `Stream-DeepLabCut/test_matlab_eye_receive_contract.py`
- `Stream-DeepLabCut/setup_two_computer_eye_link.sh`
- `Stream-DeepLabCut/README.md`
- `Docs/Capture-FLIR-Images-Over-SSH.md`
- `Docs/README_eye_stream.md`
- `Docs/SINGLE_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `Docs/SSH_X11_forwarding_PopOS.md`
- `Docs/TWO_COMPUTER_EYE_TRACKING_QUICKSTART.md`
- `.agents/plans/2026-07-09-ssh-x11-docs-remediation.md`
- `.agents/PLANS.md`

BehaviorBox repository:

- `BehaviorBoxEyeTrack.m`
- `tests/testBehaviorBoxEyeTrackReceiverContract.m`

### Validation

- `bash -n ssh_x11/*.sh` passed.
- `bash ssh_x11/test_ssh_x11_wrappers.sh` passed with
  `SSH_X11_WRAPPERS_OK`. The fake-host suite covers literal argv transport,
  wrong-bind and unrelated-listener failures, relative-launcher shutdown,
  syntax/effective-config rollback, failed-restore backup preservation, and a
  successful transactional setup.
- `ssh_x11/setup_eye_host_ssh_x11.sh --dry-run --skip-ufw` passed against the
  local SSH include layout without writing or escalating privileges.
- All seven SSH wrapper help commands, the production launcher help, MATLAB
  receive-test help, training-capture help, and two-computer setup help passed.
- `python3 -m py_compile` passed for the changed streamer, receiver, MATLAB
  launcher, and both Python contract tests.
- `$HOME/miniforge3/envs/bbeyezmq/bin/python
  Stream-DeepLabCut/test_behavior_eye_receiver.py` passed with
  `BEHAVIOR_EYE_RECEIVER_OK`.
- `matlab -batch "results=runtests('tests/testBehaviorBoxEyeTrackReceiverContract.m');
  assertSuccess(results);"` passed all seven tests from the BehaviorBox root.
- `matlab -batch "cd('/home/wbs/Desktop/BehaviorBox');
  run('fcns/testBehaviorBoxEyeTrack.m');"` passed with
  `BEHAVIORBOX_EYETRACK_OK`.
- `$HOME/miniforge3/envs/bbeyezmq/bin/python
  Stream-DeepLabCut/test_matlab_eye_receive_contract.py` passed with
  `MATLAB_EYE_STREAM_CONTRACT_OK`, covering no-points full failure,
  transport-only success, valid-eye full success, complete static metadata,
  receiver session JSON, and saved MAT provenance.
- The full CLI rejected `--min-valid-samples 0` with exit status `2`; explicit
  transport-only mode accepted a zero valid minimum.
- Stale-contract scans and relative Markdown-link checks passed.
- `git diff --check` passed in both EyeTrack and BehaviorBox.

### Remaining Risks And Follow-Up

- No live FLIR/PySpin acquisition, DLCLive inference, or real ZeroMQ PUB/SUB
  path was exercised. The receiver tests use dependency stubs and the HTTP
  debug-ingest endpoint.
- No real two-host SSH/X11 session, forwarded OpenCV window, remote process
  signaling, listener inspection, or disconnect behavior was exercised.
- No privileged production SSH drop-in install, `sshd` restart, or firewall
  change was performed. Transaction behavior was tested with fake commands and
  a nonprivileged temporary config root.
- `shellcheck` was not installed. The local host also has no `dlclivegui`
  environment, so FLIR preview/import validation remains an eye-host task.
- Run the plan's live two-host sequence on the eye-tracking and behavior
  computers before treating the workflow as hardware-validated.
