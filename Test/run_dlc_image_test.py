#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import deeplabcut
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run DeepLabCut inference on an image directory, export CSV predictions, "
            "and generate labeled preview images for quick visual sanity checks."
        )
    )
    p.add_argument("--config", type=Path, required=True, help="Path to DeepLabCut config.yaml")
    p.add_argument("--image-dir", type=Path, required=True, help="Directory of input images")
    p.add_argument("--frametype", default=".png", help="Image extension filter (e.g. .png, .jpg)")
    p.add_argument("--shuffle", type=int, default=1, help="Shuffle index to evaluate")
    p.add_argument("--trainingsetindex", type=int, default=0, help="TrainingFraction index")
    p.add_argument("--gpu", type=int, default=None, help="Optional GPU id for inference")
    p.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV path for flattened output. Defaults to <image-dir>/dlc_predictions.csv",
    )
    p.add_argument(
        "--preview-dir",
        type=Path,
        default=None,
        help="Optional directory for labeled preview images. Defaults to <image-dir>/dlc_previews",
    )
    p.add_argument(
        "--pcutoff",
        type=float,
        default=0.5,
        help="Likelihood threshold for drawing keypoints in preview images",
    )
    p.add_argument(
        "--max-previews",
        type=int,
        default=200,
        help="Max labeled preview images to render for fast sanity checks",
    )
    p.add_argument(
        "--dot-radius",
        type=int,
        default=3,
        help="Dot radius for keypoint overlays",
    )
    return p.parse_args()


def _flatten_predictions(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df.columns, pd.MultiIndex):
        out = df.copy()
        if "image" not in out.columns:
            out.insert(0, "image", out.index.astype(str))
        return out

    level_names = list(df.columns.names)
    bodypart_level = 1 if len(level_names) > 1 else 0
    coord_level = 2 if len(level_names) > 2 else 1

    flat = pd.DataFrame(index=df.index)
    flat["image"] = [Path(str(idx)).name for idx in df.index]

    bodyparts = sorted({col[bodypart_level] for col in df.columns})
    for bp in bodyparts:
        x_col = next((c for c in df.columns if c[bodypart_level] == bp and c[coord_level] == "x"), None)
        y_col = next((c for c in df.columns if c[bodypart_level] == bp and c[coord_level] == "y"), None)
        l_col = next((c for c in df.columns if c[bodypart_level] == bp and c[coord_level] in {"likelihood", "p"}), None)
        if x_col is not None:
            flat[f"{bp}_x"] = pd.to_numeric(df[x_col], errors="coerce")
        if y_col is not None:
            flat[f"{bp}_y"] = pd.to_numeric(df[y_col], errors="coerce")
        if l_col is not None:
            flat[f"{bp}_p"] = pd.to_numeric(df[l_col], errors="coerce")
        else:
            flat[f"{bp}_p"] = 1.0

    return flat


def _draw_previews(
    flat_df: pd.DataFrame,
    image_dir: Path,
    preview_dir: Path,
    pcutoff: float,
    dot_radius: int,
    max_previews: int,
) -> int:
    preview_dir.mkdir(parents=True, exist_ok=True)

    point_names = sorted(
        {
            col[:-2]
            for col in flat_df.columns
            if col.endswith("_x") and f"{col[:-2]}_y" in flat_df.columns
        }
    )

    written = 0
    for _, row in flat_df.iterrows():
        if written >= max_previews:
            break

        image_name = Path(str(row["image"])).name
        image_path = image_dir / image_name
        bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr is None:
            continue

        for kp in point_names:
            x = float(row.get(f"{kp}_x", np.nan))
            y = float(row.get(f"{kp}_y", np.nan))
            p = float(row.get(f"{kp}_p", np.nan))

            if not np.isfinite(x) or not np.isfinite(y) or not np.isfinite(p) or p < pcutoff:
                continue

            px, py = int(round(x)), int(round(y))
            cv2.circle(bgr, (px, py), dot_radius, (0, 255, 0), -1)
            cv2.putText(
                bgr,
                f"{kp} ({p:.2f})",
                (px + 4, py - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )

        out_path = preview_dir / image_name
        cv2.imwrite(str(out_path), bgr)
        written += 1

    return written


def main() -> int:
    args = parse_args()

    config = args.config.resolve()
    image_dir = args.image_dir.resolve()
    if not config.exists():
        raise SystemExit(f"--config does not exist: {config}")
    if not image_dir.is_dir():
        raise SystemExit(f"--image-dir does not exist: {image_dir}")

    deeplabcut.analyze_time_lapse_frames(
        str(config),
        str(image_dir),
        frametype=args.frametype,
        shuffle=int(args.shuffle),
        trainingsetindex=int(args.trainingsetindex),
        gputouse=args.gpu,
        save_as_csv=True,
    )

    csv_candidates = sorted(image_dir.glob(f"*{args.frametype}*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csv_candidates:
        csv_candidates = sorted(image_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csv_candidates:
        raise SystemExit("DLC inference finished, but no CSV outputs were found in --image-dir")

    dlc_csv = csv_candidates[0]
    df = pd.read_csv(dlc_csv, header=[0, 1, 2], index_col=0)
    flat = _flatten_predictions(df)

    output_csv = args.output_csv.resolve() if args.output_csv else image_dir / "dlc_predictions.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    flat.to_csv(output_csv, index=False)

    preview_dir = args.preview_dir.resolve() if args.preview_dir else image_dir / "dlc_previews"
    written = _draw_previews(
        flat_df=flat,
        image_dir=image_dir,
        preview_dir=preview_dir,
        pcutoff=float(args.pcutoff),
        dot_radius=int(args.dot_radius),
        max_previews=max(int(args.max_previews), 0),
    )

    print(f"[ok] raw_dlc_csv: {dlc_csv}")
    print(f"[ok] flattened_csv: {output_csv}")
    print(f"[ok] preview_dir: {preview_dir}")
    print(f"[ok] preview_images_written: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
