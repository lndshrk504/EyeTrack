#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_MODEL_PATH = (
    str(
        Path(__file__).resolve().parents[1]
        / "Models"
        / "DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1"
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the production FLIR -> DLCLive eye stream.")
    parser.add_argument("--model-path", default=DEFAULT_MODEL_PATH)
    parser.add_argument("--model-preset", default="yanglab-pupil8")
    parser.add_argument("--model-type", default="base")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument(
        "--sensor-roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=[0, 0, 640, 480],
    )
    parser.add_argument("--address", default="tcp://127.0.0.1:5555")
    parser.add_argument("--metadata-interval-s", type=float, default=1.0)
    parser.add_argument(
        "--frame-rate",
        type=float,
        default=60.0,
        help="Target FLIR acquisition frame rate. Keep this above the DLC inference rate.",
    )
    parser.add_argument(
        "--exposure-us",
        type=float,
        default=6000.0,
        help="Manual exposure in microseconds. Longer exposure brightens the real image.",
    )
    parser.add_argument("--gain-db", type=float, default=0.0)
    parser.add_argument(
        "--gain-auto",
        choices=["off", "once", "continuous"],
        default="off",
        help="Camera GainAuto mode. If not off, manual --gain-db is ignored.",
    )
    parser.add_argument("--display", dest="display", action="store_true", default=True)
    parser.add_argument("--no-display", dest="display", action="store_false")
    parser.add_argument("--display-scale", type=float, default=0.75)
    parser.add_argument("--display-fps", type=float, default=20.0)
    parser.add_argument("--csv-dir", default="/tmp/EyeTrack")
    return parser.parse_args()


def run_eye_stream_production() -> int:
    args = parse_args()
    here = Path(__file__).resolve().parent
    csv_dir = Path(args.csv_dir).expanduser()
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / f"eye_stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    metadata_path = csv_path.with_name(f"{csv_path.stem}_metadata.json")

    env = os.environ.copy()
    env["MPLCONFIGDIR"] = "/tmp"

    command = [
        sys.executable,
        str(here / "dlc_eye_streamer.py"),
        "--model-path",
        args.model_path,
        "--model-preset",
        args.model_preset,
        "--model-type",
        args.model_type,
        "--camera-index",
        str(args.camera_index),
        "--sensor-roi",
        *(str(v) for v in args.sensor_roi),
        "--address",
        args.address,
        "--metadata-interval-s",
        str(args.metadata_interval_s),
        "--frame-rate",
        str(args.frame_rate),
        "--exposure-us",
        str(args.exposure_us),
        "--gain-db",
        str(args.gain_db),
        "--gain-auto",
        args.gain_auto,
        "--display-scale",
        str(args.display_scale),
        "--display-fps",
        str(args.display_fps),
        "--csv",
        str(csv_path),
    ]
    if args.display:
        command.append("--display")

    print(f"Writing CSV to: {csv_path}", flush=True)
    print(f"Writing metadata to: {metadata_path}", flush=True)
    print(
        f"Camera settings: frame_rate={args.frame_rate:g} Hz, "
        f"exposure={args.exposure_us:g} us, gain_auto={args.gain_auto}, "
        f"gain={args.gain_db:g} dB",
        flush=True,
    )
    return subprocess.run(command, cwd=here, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(run_eye_stream_production())
