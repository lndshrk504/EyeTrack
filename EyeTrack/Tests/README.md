# Tests

This folder contains focused Python-side smoke and environment checks for the active eye-tracking stack.

These are not a full automated test suite. They are targeted scripts for dependency, camera, and inference-path checks.

The DLCLive smoke scripts expect an exported model under `../../models/active/<model-name>/` by default, or an explicit `--model-path`.
