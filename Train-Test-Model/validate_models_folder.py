#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("/tmp/EyeTrack/model_validation")
DEFAULT_SYNTHETIC_SHAPE = (480, 640, 3)


class ModelCompatibilityError(RuntimeError):
    """Raised when TensorFlow/DLCLive cannot load or run the model."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_model_path() -> Path:
    models_root = repo_root() / "Models"
    search_roots = [models_root / "active", models_root]

    for model_root in search_roots:
        if not model_root.is_dir():
            continue
        child_dirs = sorted(
            path
            for path in model_root.iterdir()
            if path.is_dir() and not (model_root == models_root and path.name == "active")
        )
        if len(child_dirs) == 1:
            return child_dirs[0]
        if len(child_dirs) > 1:
            names = ", ".join(path.name for path in child_dirs)
            raise SystemExit(
                f"Found multiple candidate models under {model_root}: {names}. "
                "Pass --model-path explicitly."
            )

    raise SystemExit(f"No model directory found under {models_root}. Pass --model-path.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Models/ DLCLive model without FLIR/PySpin by running a "
            "synthetic smoke test and optional still-image inference."
        )
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Model directory. Defaults to the single model under Models/ or Models/active/.",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=None,
        help="Optional directory of still images to run through DLCLive.",
    )
    parser.add_argument("--frametype", default=".png", help="Image extension filter, such as .png or .jpg.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-images", type=int, default=200)
    parser.add_argument("--pcutoff", type=float, default=0.5)
    return parser.parse_args()


def read_pose_cfg(model_path: Path) -> dict[str, Any]:
    pose_cfg = model_path / "pose_cfg.yaml"
    if not pose_cfg.is_file():
        raise FileNotFoundError(f"Missing pose_cfg.yaml: {pose_cfg}")

    import yaml

    with pose_cfg.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"pose_cfg.yaml did not contain a mapping: {pose_cfg}")
    return data


def point_names_from_pose_cfg(pose_cfg: dict[str, Any]) -> list[str]:
    names = pose_cfg.get("all_joints_names") or pose_cfg.get("bodyparts") or []
    if not isinstance(names, list):
        return []
    return [str(name) for name in names]


def normalize_pose(pose: Any) -> Any:
    import numpy as np

    arr = np.asarray(pose, dtype=float)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim == 1 and arr.size % 3 == 0:
        arr = arr.reshape((-1, 3))
    return arr


def likelihood_mean(pose: Any) -> float | None:
    import numpy as np

    if pose.ndim != 2 or pose.shape[1] < 3:
        return None
    likelihoods = pose[:, 2]
    finite = likelihoods[np.isfinite(likelihoods)]
    if finite.size == 0:
        return None
    return float(np.mean(finite))


def pose_summary(pose: Any) -> dict[str, Any]:
    import numpy as np

    finite = bool(np.isfinite(pose).all()) if pose.size else False
    return {
        "shape": list(pose.shape),
        "finite": finite,
        "nan_count": int(np.isnan(pose).sum()) if pose.size else 0,
        "likelihood_mean": likelihood_mean(pose),
    }


def image_candidates(image_dir: Path, frametype: str, max_images: int) -> list[Path]:
    if not image_dir.is_dir():
        raise FileNotFoundError(f"--image-dir does not exist: {image_dir}")

    suffix = frametype if frametype.startswith(".") else f".{frametype}"
    candidates = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() == suffix.lower()
    )
    if max_images >= 0:
        candidates = candidates[:max_images]
    if not candidates:
        raise FileNotFoundError(f"No {suffix} files found in {image_dir}")
    return candidates


def read_bgr_image(path: Path) -> Any:
    import cv2

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def bgr_to_rgb(image: Any) -> Any:
    import cv2

    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def synthetic_image(shape: tuple[int, int, int]) -> Any:
    import numpy as np

    return np.zeros(shape, dtype=np.uint8)


def create_dlclive(model_path: Path) -> Any:
    try:
        from dlclive import DLCLive

        return DLCLive(str(model_path), model_type="base", display=False)
    except Exception as exc:  # pragma: no cover - depends on external environment
        raise ModelCompatibilityError(
            f"Could not construct DLCLive for {model_path}: {exc}"
        ) from exc


def init_and_run_synthetic(dlc: Any, image: Any) -> Any:
    try:
        dlc.init_inference(image)
        return normalize_pose(dlc.get_pose(image))
    except Exception as exc:  # pragma: no cover - depends on external environment
        raise ModelCompatibilityError(
            "DLCLive could not initialize or run the bundled TensorFlow model. "
            "This is a TensorFlow/DLCLive/model compatibility failure, not a "
            "FLIR/PySpin camera failure. "
            f"Original error: {exc}"
        ) from exc


def run_pose(dlc: Any, image: Any) -> Any:
    try:
        return normalize_pose(dlc.get_pose(image))
    except Exception as exc:  # pragma: no cover - depends on external environment
        raise ModelCompatibilityError(f"DLCLive image inference failed: {exc}") from exc


def names_for_pose(point_names: list[str], pose: Any) -> list[str]:
    n_points = int(pose.shape[0]) if pose.ndim >= 1 else 0
    names = list(point_names[:n_points])
    if len(names) < n_points:
        names.extend(f"point_{idx}" for idx in range(len(names), n_points))
    return names


def flatten_pose_row(image_path: Path, image_shape: tuple[int, ...], pose: Any, point_names: list[str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "image": image_path.name,
        "width": int(image_shape[1]) if len(image_shape) >= 2 else None,
        "height": int(image_shape[0]) if len(image_shape) >= 1 else None,
        "pose_shape": "x".join(str(part) for part in pose.shape),
        "pose_finite": bool(pose_summary(pose)["finite"]),
        "likelihood_mean": likelihood_mean(pose),
    }
    for idx, name in enumerate(names_for_pose(point_names, pose)):
        x = float(pose[idx, 0]) if pose.ndim == 2 and pose.shape[1] > 0 else math.nan
        y = float(pose[idx, 1]) if pose.ndim == 2 and pose.shape[1] > 1 else math.nan
        p = float(pose[idx, 2]) if pose.ndim == 2 and pose.shape[1] > 2 else math.nan
        row[f"{name}_x"] = x
        row[f"{name}_y"] = y
        row[f"{name}_likelihood"] = p
    return row


def write_predictions_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def draw_preview(path: Path, bgr: Any, pose: Any, point_names: list[str], pcutoff: float) -> bool:
    import cv2
    import numpy as np

    names = names_for_pose(point_names, pose)
    for idx, name in enumerate(names):
        if pose.ndim != 2 or pose.shape[1] < 2:
            continue
        x = float(pose[idx, 0])
        y = float(pose[idx, 1])
        p = float(pose[idx, 2]) if pose.shape[1] > 2 else 1.0
        if not all(np.isfinite([x, y, p])) or p < pcutoff:
            continue
        px, py = int(round(x)), int(round(y))
        cv2.circle(bgr, (px, py), 3, (0, 255, 0), -1)
        cv2.putText(
            bgr,
            f"{name} ({p:.2f})",
            (px + 4, py - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return bool(cv2.imwrite(str(path), bgr))


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")


def validate(args: argparse.Namespace) -> dict[str, Any]:
    model_path = (args.model_path or default_model_path()).resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"--model-path is not a directory: {model_path}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pose_cfg = read_pose_cfg(model_path)
    point_names = point_names_from_pose_cfg(pose_cfg)

    images: list[Path] = []
    synthetic_shape = DEFAULT_SYNTHETIC_SHAPE
    first_bgr = None
    if args.image_dir is not None:
        images = image_candidates(args.image_dir.resolve(), args.frametype, int(args.max_images))
        first_bgr = read_bgr_image(images[0])
        synthetic_shape = tuple(first_bgr.shape)

    dlc = create_dlclive(model_path)
    synthetic_pose = init_and_run_synthetic(dlc, synthetic_image(synthetic_shape))
    synthetic = pose_summary(synthetic_pose)

    rows: list[dict[str, Any]] = []
    previews_written = 0
    predictions_csv = None
    preview_dir = None

    if images:
        preview_dir = output_dir / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)

        for idx, image_path in enumerate(images):
            bgr = first_bgr.copy() if idx == 0 and first_bgr is not None else read_bgr_image(image_path)
            rgb = bgr_to_rgb(bgr)
            pose = run_pose(dlc, rgb)
            rows.append(flatten_pose_row(image_path, tuple(bgr.shape), pose, point_names))
            if draw_preview(preview_dir / image_path.name, bgr, pose, point_names, float(args.pcutoff)):
                previews_written += 1

        predictions_csv = output_dir / "predictions.csv"
        write_predictions_csv(predictions_csv, rows)

    passed = bool(synthetic["finite"]) and (not images or bool(rows))
    summary: dict[str, Any] = {
        "status": "pass" if passed else "fail",
        "model_path": str(model_path),
        "pose_cfg": str(model_path / "pose_cfg.yaml"),
        "point_names": point_names,
        "synthetic": synthetic,
        "image_dir": str(args.image_dir.resolve()) if args.image_dir else None,
        "frametype": args.frametype,
        "images_requested": len(images),
        "images_processed": len(rows),
        "predictions_csv": str(predictions_csv) if predictions_csv else None,
        "preview_dir": str(preview_dir) if preview_dir else None,
        "previews_written": previews_written,
        "summary_json": str(output_dir / "validation_summary.json"),
    }
    write_summary(output_dir / "validation_summary.json", summary)
    return summary


def main() -> int:
    args = parse_args()
    try:
        summary = validate(args)
    except ModelCompatibilityError as exc:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        failure = {
            "status": "fail",
            "category": "tensorflow_dlclive_model_compatibility",
            "error": str(exc),
            "summary_json": str(output_dir / "validation_summary.json"),
        }
        write_summary(output_dir / "validation_summary.json", failure)
        print(json.dumps(failure, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
