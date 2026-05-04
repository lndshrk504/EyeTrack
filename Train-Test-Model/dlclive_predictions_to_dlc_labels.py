#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_KEY = "df_with_missing"


@dataclass(frozen=True)
class PointMapping:
    bodypart: str
    prediction_prefix: str
    strategy: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert flattened DLCLive predictions from validate_models_folder.py "
            "into editable DeepLabCut CollectedData labels."
        )
    )
    parser.add_argument("--config", type=Path, required=True, help="Path to the target DLC config.yaml")
    parser.add_argument(
        "--image-dir",
        type=Path,
        required=True,
        help=(
            "DLC extracted-frame folder to label. Pass either an absolute path or "
            "a folder name under <project>/labeled-data/."
        ),
    )
    parser.add_argument(
        "--predictions-csv",
        type=Path,
        required=True,
        help="predictions.csv written by Train-Test-Model/validate_models_folder.py",
    )
    parser.add_argument(
        "--scorer",
        default=None,
        help="Scorer name for CollectedData_<scorer>.h5. Defaults to config.yaml scorer.",
    )
    parser.add_argument(
        "--min-likelihood",
        type=float,
        default=0.0,
        help=(
            "Set a keypoint to NaN when the model likelihood is below this value. "
            "Default 0 keeps all predicted points as editable drafts."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing CollectedData_<scorer>.h5/.csv in --image-dir.",
    )
    parser.add_argument(
        "--backup-existing",
        action="store_true",
        help="When overwriting, copy existing CollectedData files to .bak first.",
    )
    parser.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="Do not fail if a prediction row references an image missing from --image-dir.",
    )
    return parser.parse_args()


def read_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def project_root_for_config(config_path: Path, cfg: dict[str, Any]) -> Path:
    project_path = cfg.get("project_path")
    if isinstance(project_path, str) and project_path:
        candidate = Path(project_path).expanduser()
        if candidate.is_dir() and (candidate / "config.yaml").resolve() == config_path.resolve():
            return candidate.resolve()
    return config_path.resolve().parent


def resolve_image_dir(config_path: Path, cfg: dict[str, Any], image_dir_arg: Path) -> Path:
    expanded = image_dir_arg.expanduser()
    if expanded.is_dir():
        return expanded.resolve()

    project_root = project_root_for_config(config_path, cfg)
    candidate = project_root / "labeled-data" / str(image_dir_arg)
    if candidate.is_dir():
        return candidate.resolve()

    raise FileNotFoundError(
        f"Could not find --image-dir as either {expanded} or {candidate}"
    )


def require_dlc_labeled_data_folder(config_path: Path, cfg: dict[str, Any], image_dir: Path) -> None:
    project_root = project_root_for_config(config_path, cfg)
    labeled_root = (project_root / "labeled-data").resolve()
    try:
        image_dir.relative_to(labeled_root)
    except ValueError as exc:
        raise ValueError(
            f"--image-dir must be inside the DLC project's labeled-data folder: {labeled_root}"
        ) from exc


def config_bodyparts(cfg: dict[str, Any]) -> list[str]:
    bodyparts = cfg.get("bodyparts") or []
    if not isinstance(bodyparts, list) or not bodyparts:
        raise ValueError("config.yaml must contain a non-empty bodyparts list")
    return [str(part) for part in bodyparts]


def config_scorer(cfg: dict[str, Any], override: str | None) -> str:
    scorer = override if override is not None else cfg.get("scorer")
    if not isinstance(scorer, str) or not scorer:
        raise ValueError("Could not determine scorer. Pass --scorer or set scorer in config.yaml.")
    return scorer


def read_predictions(path: Path) -> Any:
    import pandas as pd

    if not path.is_file():
        raise FileNotFoundError(f"--predictions-csv does not exist: {path}")
    data = pd.read_csv(path)
    if "image" not in data.columns:
        raise ValueError(f"{path} must contain an 'image' column")
    if data.empty:
        raise ValueError(f"{path} contains no prediction rows")
    return data


def prediction_prefixes(columns: list[str]) -> list[str]:
    prefixes: list[str] = []
    for column in columns:
        if not column.endswith("_x"):
            continue
        prefix = column[:-2]
        if f"{prefix}_y" in columns and prefix not in prefixes:
            prefixes.append(prefix)
    return prefixes


def make_point_mappings(bodyparts: list[str], data: Any) -> list[PointMapping]:
    columns = [str(column) for column in data.columns]
    prefixes = prediction_prefixes(columns)
    if len(prefixes) < len(bodyparts):
        raise ValueError(
            "Prediction CSV has fewer keypoint columns than config.yaml bodyparts: "
            f"{len(prefixes)} predictions for {len(bodyparts)} bodyparts."
        )

    mappings: list[PointMapping] = []
    used: set[str] = set()
    for index, bodypart in enumerate(bodyparts):
        if bodypart in prefixes and bodypart not in used:
            prefix = bodypart
            strategy = "exact"
        else:
            prefix = prefixes[index]
            if prefix in used:
                prefix = next((candidate for candidate in prefixes if candidate not in used), prefix)
            strategy = "order"
        used.add(prefix)
        mappings.append(PointMapping(bodypart=bodypart, prediction_prefix=prefix, strategy=strategy))
    return mappings


def likelihood_for_row(row: Any, prefix: str) -> float:
    for suffix in ("likelihood", "p"):
        key = f"{prefix}_{suffix}"
        if key in row:
            value = row[key]
            if value is None:
                return 1.0
            try:
                value = float(value)
            except (TypeError, ValueError):
                return 1.0
            if math.isnan(value):
                return 1.0
            return value
    return 1.0


def finite_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def image_name_for_row(value: Any) -> str:
    name = Path(str(value)).name
    if not name:
        raise ValueError(f"Invalid image value in predictions CSV: {value!r}")
    return name


def build_collected_dataframe(
    data: Any,
    image_dir: Path,
    bodyparts: list[str],
    scorer: str,
    mappings: list[PointMapping],
    min_likelihood: float,
    allow_missing_images: bool,
) -> Any:
    import numpy as np
    import pandas as pd

    row_index: list[tuple[str, str, str]] = []
    values = np.full((len(data), len(bodyparts) * 2), np.nan, dtype=float)
    missing_images: list[str] = []

    for row_number, row in data.iterrows():
        image_name = image_name_for_row(row["image"])
        if not (image_dir / image_name).is_file():
            missing_images.append(image_name)

        row_index.append(("labeled-data", image_dir.name, image_name))

        for point_index, mapping in enumerate(mappings):
            likelihood = likelihood_for_row(row, mapping.prediction_prefix)
            if likelihood < min_likelihood:
                continue
            x = finite_float(row.get(f"{mapping.prediction_prefix}_x"))
            y = finite_float(row.get(f"{mapping.prediction_prefix}_y"))
            values[row_number, point_index * 2] = x
            values[row_number, point_index * 2 + 1] = y

    if missing_images and not allow_missing_images:
        sample = ", ".join(missing_images[:5])
        extra = "" if len(missing_images) <= 5 else f", ... ({len(missing_images)} total)"
        raise FileNotFoundError(f"Prediction rows reference images missing from --image-dir: {sample}{extra}")

    columns = pd.MultiIndex.from_product(
        [[scorer], bodyparts, ["x", "y"]],
        names=["scorer", "bodyparts", "coords"],
    )
    index = pd.MultiIndex.from_tuples(row_index)
    return pd.DataFrame(values, index=index, columns=columns)


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)
    return backup


def write_collected_data(
    df: Any,
    image_dir: Path,
    scorer: str,
    overwrite: bool,
    backup_existing: bool,
) -> tuple[Path, Path, list[Path]]:
    h5_path = image_dir / f"CollectedData_{scorer}.h5"
    csv_path = image_dir / f"CollectedData_{scorer}.csv"
    existing = [path for path in (h5_path, csv_path) if path.exists()]
    if existing and not overwrite:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing labels: {names}. Pass --overwrite after backing up or reviewing them."
        )

    backups: list[Path] = []
    if existing and backup_existing:
        for path in existing:
            backup = backup_file(path)
            if backup is not None:
                backups.append(backup)

    df.to_hdf(h5_path, key=DEFAULT_OUTPUT_KEY, mode="w")
    df.to_csv(csv_path)
    return h5_path, csv_path, backups


def summary_dict(
    config_path: Path,
    image_dir: Path,
    predictions_csv: Path,
    scorer: str,
    bodyparts: list[str],
    mappings: list[PointMapping],
    min_likelihood: float,
    h5_path: Path,
    csv_path: Path,
    backups: list[Path],
    rows: int,
) -> dict[str, Any]:
    return {
        "config": str(config_path),
        "image_dir": str(image_dir),
        "predictions_csv": str(predictions_csv),
        "scorer": scorer,
        "bodyparts": bodyparts,
        "point_mappings": [
            {
                "bodypart": mapping.bodypart,
                "prediction_prefix": mapping.prediction_prefix,
                "strategy": mapping.strategy,
            }
            for mapping in mappings
        ],
        "min_likelihood": float(min_likelihood),
        "rows_written": int(rows),
        "h5": str(h5_path),
        "csv": str(csv_path),
        "backups": [str(path) for path in backups],
        "next_step": (
            "Open this image folder in the DLC/napari labeler, correct every draft point, "
            "save the points layer, then run deeplabcut.check_labels(config_path)."
        ),
    }


def main() -> int:
    args = parse_args()
    config_path = args.config.expanduser().resolve()
    if not config_path.is_file():
        raise SystemExit(f"--config does not exist: {config_path}")

    try:
        cfg = read_yaml(config_path)
        image_dir = resolve_image_dir(config_path, cfg, args.image_dir)
        require_dlc_labeled_data_folder(config_path, cfg, image_dir)
        bodyparts = config_bodyparts(cfg)
        scorer = config_scorer(cfg, args.scorer)
        data = read_predictions(args.predictions_csv.expanduser().resolve())
        mappings = make_point_mappings(bodyparts, data)
        df = build_collected_dataframe(
            data=data,
            image_dir=image_dir,
            bodyparts=bodyparts,
            scorer=scorer,
            mappings=mappings,
            min_likelihood=float(args.min_likelihood),
            allow_missing_images=bool(args.allow_missing_images),
        )
        h5_path, csv_path, backups = write_collected_data(
            df=df,
            image_dir=image_dir,
            scorer=scorer,
            overwrite=bool(args.overwrite),
            backup_existing=bool(args.backup_existing),
        )
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    print(
        json.dumps(
            summary_dict(
                config_path=config_path,
                image_dir=image_dir,
                predictions_csv=args.predictions_csv.expanduser().resolve(),
                scorer=scorer,
                bodyparts=bodyparts,
                mappings=mappings,
                min_likelihood=float(args.min_likelihood),
                h5_path=h5_path,
                csv_path=csv_path,
                backups=backups,
                rows=len(df),
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
