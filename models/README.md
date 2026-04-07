# Active Model Layout

This repo intentionally does not track the heavy active runtime model artifacts in git.

Copy the active model you want to use into this directory tree manually.

Current recommended layout:

```text
models/
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
- For compatibility, `models/active/<model-name>/` also works if you prefer that extra nesting.
- `models/` contents other than this file are ignored by git in this local repo.
- The test scripts under `DeepLabCut/Tests/` look here by default and will use the single directory under `models/`, or `models/active/` if that folder exists. You can also pass `--model-path`.
