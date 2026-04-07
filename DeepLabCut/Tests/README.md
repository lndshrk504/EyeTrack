# Tests

This folder contains focused Python-side smoke and environment checks for the active eye-tracking stack.

These are not a full automated test suite. They are targeted scripts for dependency, camera, and inference-path checks.

The DLCLive smoke scripts resolve the default model path in this order:

- `../../models/active/<model-name>/`
- `../../models/<model-name>/`

You can also pass an explicit `--model-path`.
