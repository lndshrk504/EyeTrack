#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

import cv2
import numpy as np


def opencv_has_gstreamer() -> bool:
    try:
        build_info = cv2.getBuildInformation()
    except Exception:
        return False
    for line in build_info.splitlines():
        if "GStreamer" in line:
            return "YES" in line.upper()
    return False


def default_aravis_pipeline(args: argparse.Namespace) -> str:
    source = args.aravis_source
    caps = (
        f"video/x-raw,format={args.pixel_format},"
        f"width={args.width},height={args.height},framerate={args.fps}/1"
    )
    return f"{source} ! {caps} ! videoconvert ! appsink drop=true max-buffers=1"


def open_capture(args: argparse.Namespace) -> tuple[cv2.VideoCapture, str]:
    if args.backend == "gstreamer":
        pipeline = args.pipeline or default_aravis_pipeline(args)
        return cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER), pipeline

    if args.backend == "usb":
        source: int | str
        try:
            source = int(args.source)
        except ValueError:
            source = args.source
        backend = cv2.CAP_V4L2 if hasattr(cv2, "CAP_V4L2") else cv2.CAP_ANY
        cap = cv2.VideoCapture(source, backend)
        if args.width > 0:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        if args.height > 0:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        if args.fps > 0:
            cap.set(cv2.CAP_PROP_FPS, args.fps)
        return cap, str(source)

    raise ValueError(f"Unknown backend: {args.backend}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded OpenCV smoke test for GStreamer/Aravis or USB cameras."
    )
    parser.add_argument(
        "--backend",
        choices=["gstreamer", "usb"],
        default="gstreamer",
        help="Use GStreamer/Aravis pipeline or a regular OpenCV USB camera source.",
    )
    parser.add_argument("--source", default="0", help="USB camera index/path when --backend usb.")
    parser.add_argument(
        "--pipeline",
        default="",
        help="Full GStreamer pipeline. If omitted, an aravissrc pipeline is generated.",
    )
    parser.add_argument(
        "--aravis-source",
        default="aravissrc",
        help="GStreamer Aravis source element, with optional properties.",
    )
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=120)
    parser.add_argument("--pixel-format", default="GRAY8")
    parser.add_argument("--frames", type=int, default=120)
    parser.add_argument("--timeout-s", type=float, default=10)
    parser.add_argument("--display", action="store_true")
    parser.add_argument("--print-build", action="store_true", help="Print OpenCV build information.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("OpenCV:", cv2.__version__)
    print("OpenCV GStreamer support:", opencv_has_gstreamer())
    if args.print_build:
        print(cv2.getBuildInformation())

    cap, description = open_capture(args)
    print(f"backend={args.backend}")
    print(f"source={description}")

    try:
        if not cap.isOpened():
            print("capture_opened=False")
            return 1
        print("capture_opened=True")

        frames = 0
        failed_reads = 0
        first_shape = None
        first_mean = np.nan
        start = time.perf_counter()
        deadline = start + args.timeout_s

        while frames < args.frames and time.perf_counter() < deadline:
            ret, frame = cap.read()
            if not ret or frame is None:
                failed_reads += 1
                time.sleep(0.01)
                continue

            frames += 1
            if first_shape is None:
                first_shape = frame.shape
                first_mean = float(np.mean(frame))

            if args.display:
                cv2.imshow("OpenCV camera smoke", frame)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break

        elapsed = time.perf_counter() - start
        fps = frames / elapsed if elapsed > 0 else float("nan")
        print(f"frames_acquired={frames}")
        print(f"failed_reads={failed_reads}")
        print(f"first_shape={first_shape}")
        print(f"first_frame_mean={first_mean:.3f}")
        print(f"elapsed_s={elapsed:.3f}")
        print(f"fps={fps:.2f}")
        return 0 if frames > 0 else 1
    finally:
        cap.release()
        if args.display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
