# Active Model Layout

This repo intentionally does not track the heavy active runtime model artifacts in git.

Copy the active model you want to use into this directory tree manually.

Current recommended layout:

```text
models/
  active/
    <model-name>/
      snapshot-*.data-00000-of-00001
      snapshot-*.index
      snapshot-*.meta
      snapshot-*.pb
      snapshot-*.pbtxt
      pose_cfg.yaml
```

Notes:

- Keep only active model artifacts here.
- Legacy binary placement is documented in the top-level `README.md`, not here.
- `models/` contents other than this file are ignored by git in this local repo.
- The test scripts under `EyeTrack/Tests/` look here by default and will use the single directory under `models/active/`, or you can pass `--model-path`.
