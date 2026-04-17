#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import PySpin

TO_MATLAB_DIR = Path(__file__).resolve().parents[1] / "ToMatlab"
if str(TO_MATLAB_DIR) not in sys.path:
    sys.path.insert(0, str(TO_MATLAB_DIR))


def default_model_path() -> Path:
    eye_track_root = Path(__file__).resolve().parents[2]
    preferred = eye_track_root / "models" / "DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1"
    if preferred.is_dir():
        return preferred

    model_roots = [
        eye_track_root / "models" / "active",
        eye_track_root / "models",
    ]
    for model_root in model_roots:
        if not model_root.is_dir():
            continue
        child_dirs = sorted(path for path in model_root.iterdir() if path.is_dir())
        if len(child_dirs) == 1:
            return child_dirs[0]
        if child_dirs:
            raise FileNotFoundError(
                f"Found multiple candidate models under {model_root}. Pass --model-path."
            )
    raise FileNotFoundError("No exported DLCLive model found. Pass --model-path.")


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * (pct / 100.0)
    lo = int(np.floor(rank))
    hi = int(np.ceil(rank))
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)


def summarize(label: str, values: list[float]) -> None:
    print(
        f"{label:14s} mean={statistics.fmean(values):7.2f} ms "
        f"p50={statistics.median(values):7.2f} ms "
        f"p95={percentile(values, 95):7.2f} ms "
        f"max={max(values):7.2f} ms"
    )


def apply_model_preset(args: argparse.Namespace) -> argparse.Namespace:
    from dlc_eye_streamer import MODEL_PRESETS

    if args.model_preset != "none":
        preset = MODEL_PRESETS[args.model_preset]
        for attr in ("kp_top", "kp_bottom", "kp_left", "kp_right", "kp_center"):
            if getattr(args, attr) is None:
                setattr(args, attr, preset[attr])
        if not args.point_names:
            args.point_names = list(preset["point_names"])
    return args


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded FLIR + DLCLive inference timing smoke test."
    )
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument("--model-preset", choices=["yanglab-pupil8", "none"], default="yanglab-pupil8")
    parser.add_argument("--model-type", choices=["base", "pytorch", "tensorrt", "tflite"], default="base")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--frames", type=int, default=120, help="Timed inference frames after warmup.")
    parser.add_argument("--warmup", type=int, default=5, help="Warmup frames after init before timing.")
    parser.add_argument("--report-every", type=int, default=20)
    parser.add_argument("--timeout-ms", type=int, default=1000)
    parser.add_argument("--buffer-count", type=int, default=3)
    parser.add_argument("--pixel-format", default="Mono8")
    parser.add_argument("--exposure-us", type=float, default=2000.0)
    parser.add_argument("--gain-db", type=float, default=0.0)
    parser.add_argument("--frame-rate", type=float, default=None)
    parser.add_argument("--sensor-roi", type=int, nargs=4, metavar=("X", "Y", "W", "H"), default=None)
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X1", "X2", "Y1", "Y2"), default=None)
    parser.add_argument("--dynamic-crop", action="store_true")
    parser.add_argument("--dynamic-margin", type=int, default=20)
    parser.add_argument("--pass-gray-to-dlc", action="store_true")
    parser.add_argument("--pcutoff", type=float, default=0.5)
    parser.add_argument("--kp-top", type=int, default=None)
    parser.add_argument("--kp-bottom", type=int, default=None)
    parser.add_argument("--kp-left", type=int, default=None)
    parser.add_argument("--kp-right", type=int, default=None)
    parser.add_argument("--kp-center", type=int, default=None)
    parser.add_argument("--point-names", nargs="*", default=[])
    parser.add_argument("--display", action="store_true", help="Show camera frames while timing.")
    parser.add_argument("--display-scale", type=float, default=1.0)
    args = apply_model_preset(parser.parse_args())
    if args.model_path is None:
        args.model_path = default_model_path()
    return args


def get_frame(cam: Any, timeout_ms: int) -> tuple[np.ndarray | None, dict[str, float]]:
    timings: dict[str, float] = {}
    acquire_start = time.perf_counter()
    image = cam.GetNextImage(timeout_ms)
    frame_time = time.perf_counter()
    try:
        if image.IsIncomplete():
            return None, timings
        copy_start = time.perf_counter()
        frame = image.GetNDArray().copy()
        copy_end = time.perf_counter()
    finally:
        image.Release()
    release_end = time.perf_counter()
    timings["capture"] = (frame_time - acquire_start) * 1000.0
    timings["copy"] = (copy_end - copy_start) * 1000.0
    timings["release"] = (release_end - copy_end) * 1000.0
    return frame, timings


def main() -> int:
    args = parse_args()
    from dlclive import DLCLive
    from dlc_eye_streamer import configure_camera, normalize_pose, prepare_frame_for_dlc

    print("model_path:", args.model_path)
    print("model_type:", args.model_type)
    print("model_preset:", args.model_preset)
    print("point_names:", ", ".join(args.point_names))

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    cam = None
    acquired = False

    try:
        if cam_list.GetSize() == 0:
            print("No PySpin cameras detected")
            return 1
        cam = cam_list.GetByIndex(args.camera_index)
        camera_info = configure_camera(cam, args)
        print("camera_model:", camera_info.get("model"))
        print("camera_serial:", camera_info.get("serial"))
        if "sensor_roi_applied" in camera_info:
            print("sensor_roi_applied:", camera_info["sensor_roi_applied"])

        dlc = DLCLive(
            str(args.model_path),
            model_type=args.model_type,
            cropping=args.crop,
            dynamic=(args.dynamic_crop, args.pcutoff, args.dynamic_margin),
            display=False,
        )

        cam.BeginAcquisition()
        acquired = True
        first_frame = None
        while first_frame is None:
            first_frame, _ = get_frame(cam, args.timeout_ms)

        init_img = prepare_frame_for_dlc(first_frame, rgb_for_dlc=not args.pass_gray_to_dlc)
        init_start = time.perf_counter()
        dlc.init_inference(init_img)
        init_ms = (time.perf_counter() - init_start) * 1000.0
        print(f"init_inference_ms={init_ms:.2f}")

        for _ in range(max(args.warmup, 0)):
            frame = None
            while frame is None:
                frame, _ = get_frame(cam, args.timeout_ms)
            dlc.get_pose(prepare_frame_for_dlc(frame, rgb_for_dlc=not args.pass_gray_to_dlc))

        fps_window: deque[float] = deque(maxlen=120)
        timings = {
            "capture": [],
            "copy": [],
            "release": [],
            "prepare": [],
            "inference": [],
            "display": [],
            "total": [],
            "overhead": [],
        }
        valid_frames = 0
        incomplete_frames = 0
        last_pose = None
        first_shape = None

        while valid_frames < args.frames:
            loop_start = time.perf_counter()
            frame, frame_timings = get_frame(cam, args.timeout_ms)
            if frame is None:
                incomplete_frames += 1
                continue
            if first_shape is None:
                first_shape = frame.shape

            prepare_start = time.perf_counter()
            infer_img = prepare_frame_for_dlc(frame, rgb_for_dlc=not args.pass_gray_to_dlc)
            prepare_end = time.perf_counter()

            infer_start = time.perf_counter()
            pose = normalize_pose(dlc.get_pose(infer_img))
            infer_end = time.perf_counter()

            display_start = time.perf_counter()
            if args.display:
                vis = frame
                if args.display_scale != 1.0:
                    vis = cv2.resize(vis, None, fx=args.display_scale, fy=args.display_scale)
                cv2.imshow("FLIR DLC inference smoke", vis)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break
            display_end = time.perf_counter()
            loop_end = time.perf_counter()

            capture_ms = frame_timings.get("capture", float("nan"))
            copy_ms = frame_timings.get("copy", float("nan"))
            release_ms = frame_timings.get("release", float("nan"))
            prepare_ms = (prepare_end - prepare_start) * 1000.0
            infer_ms = (infer_end - infer_start) * 1000.0
            display_ms = (display_end - display_start) * 1000.0
            total_ms = (loop_end - loop_start) * 1000.0
            overhead_ms = total_ms - sum(
                value for value in [capture_ms, copy_ms, release_ms, prepare_ms, infer_ms, display_ms]
                if np.isfinite(value)
            )

            timings["capture"].append(capture_ms)
            timings["copy"].append(copy_ms)
            timings["release"].append(release_ms)
            timings["prepare"].append(prepare_ms)
            timings["inference"].append(infer_ms)
            timings["display"].append(display_ms)
            timings["total"].append(total_ms)
            timings["overhead"].append(overhead_ms)
            valid_frames += 1
            last_pose = pose
            fps_window.append(loop_end)

            if args.report_every > 0 and valid_frames % args.report_every == 0:
                fps = 0.0
                if len(fps_window) > 1:
                    fps = (len(fps_window) - 1) / (fps_window[-1] - fps_window[0])
                print(
                    f"[{valid_frames}] fps={fps:.2f} "
                    f"capture={capture_ms:.2f} ms copy={copy_ms:.2f} ms "
                    f"release={release_ms:.2f} ms prepare={prepare_ms:.2f} ms "
                    f"inference={infer_ms:.2f} ms overhead={overhead_ms:.2f} ms "
                    f"total={total_ms:.2f} ms"
                )

        print()
        print("frames_timed:", valid_frames)
        print("incomplete_frames:", incomplete_frames)
        print("first_shape:", first_shape)
        if last_pose is not None:
            print("last_pose_shape:", tuple(last_pose.shape))
            print("last_pose_finite:", bool(np.isfinite(last_pose).all()))
            print("last_likelihood_mean:", float(np.nanmean(last_pose[:, 2])))
        if valid_frames > 0:
            print()
            summarize("capture", timings["capture"])
            summarize("copy", timings["copy"])
            summarize("release", timings["release"])
            summarize("prepare", timings["prepare"])
            summarize("inference", timings["inference"])
            summarize("display", timings["display"])
            summarize("overhead", timings["overhead"])
            summarize("total", timings["total"])
            mean_total_ms = statistics.fmean(timings["total"])
            print(f"mean_loop_fps={1000.0 / mean_total_ms:.2f}")
        return 0 if valid_frames > 0 else 1
    finally:
        if args.display:
            cv2.destroyAllWindows()
        if cam is not None:
            if acquired:
                try:
                    cam.EndAcquisition()
                except Exception:
                    pass
            try:
                cam.DeInit()
            except Exception:
                pass
            del cam
        cam_list.Clear()
        system.ReleaseInstance()


if __name__ == "__main__":
    raise SystemExit(main())
