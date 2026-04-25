#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import platform
import signal
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "EyeTrackTrainingFrames"
DEFAULT_SENSOR_ROI = [0, 0, 640, 480]
MANIFEST_FIELDS = [
    "relative_path",
    "saved_index",
    "frame_id",
    "capture_time_unix_s",
    "capture_time_iso",
    "trigger",
    "shape",
    "dtype",
    "min_intensity",
    "max_intensity",
    "mean_intensity",
]


def positive_or_zero_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def positive_or_zero_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture raw FLIR/PySpin frames for later DeepLabCut/TensorFlow retraining.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Root directory for timestamped capture sessions.",
    )
    parser.add_argument(
        "--session-name",
        default="",
        help="Optional session folder name. Default uses session_YYYYMMDD_HHMMSS.",
    )
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=1000, help="PySpin GetNextImage timeout.")
    parser.add_argument("--buffer-count", type=int, default=3, help="Host stream buffer count.")
    parser.add_argument("--pixel-format", default="Mono8", help="GenICam PixelFormat value.")
    parser.add_argument("--exposure-us", type=float, default=6000.0, help="Manual exposure in microseconds.")
    parser.add_argument("--gain-db", type=float, default=0.0, help="Manual gain in dB when gain auto is off.")
    parser.add_argument("--frame-rate", type=float, default=60.0, help="Target camera acquisition frame rate.")
    parser.add_argument(
        "--gain-auto",
        choices=["off", "once", "continuous"],
        default="off",
        help="Camera GainAuto mode.",
    )
    parser.add_argument(
        "--sensor-roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=list(DEFAULT_SENSOR_ROI),
        help="Camera sensor ROI: offset_x offset_y width height.",
    )
    parser.add_argument(
        "--no-restore-settings",
        dest="restore_settings",
        action="store_false",
        help="Leave capture camera settings on the camera after exit.",
    )
    parser.set_defaults(restore_settings=True)

    parser.add_argument("--no-preview", dest="preview", action="store_false", help="Run without a preview window.")
    parser.set_defaults(preview=True)
    parser.add_argument("--scale", type=float, default=0.75, help="Preview display scale factor.")
    parser.add_argument("--auto-contrast", action="store_true", help="Stretch preview contrast only; saved frames stay raw.")
    parser.add_argument("--window-name", default="FLIR Training Frame Capture")

    parser.add_argument(
        "--save-every",
        type=positive_or_zero_int,
        default=0,
        help="Autosave every N complete camera frames. 0 disables autosave.",
    )
    parser.add_argument(
        "--seconds",
        type=positive_or_zero_float,
        default=0.0,
        help="Optional capture duration. 0 means run until stopped.",
    )
    parser.add_argument(
        "--frames",
        type=positive_or_zero_int,
        default=0,
        help="Optional complete-frame limit. 0 means no frame-count limit.",
    )

    args = parser.parse_args()
    if not args.preview and args.save_every <= 0:
        parser.error("--no-preview requires --save-every so headless capture can save frames.")
    args.full_frame = False
    return args


def timestamp_iso(timestamp_s: float) -> str:
    return datetime.fromtimestamp(timestamp_s, tz=timezone.utc).isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session_paths(output_dir: Path, session_name: str) -> dict[str, Path]:
    root = output_dir.expanduser()
    name = session_name.strip() or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir = root / name
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=False)
    return {
        "root": root,
        "session_dir": session_dir,
        "frames_dir": frames_dir,
        "manifest": session_dir / "manifest.csv",
        "metadata": session_dir / "metadata.json",
    }


def json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    return value


def frame_stats(frame: Any) -> dict[str, Any]:
    return {
        "shape": json.dumps(list(frame.shape)),
        "dtype": str(frame.dtype),
        "min_intensity": int(frame.min()) if frame.size else None,
        "max_intensity": int(frame.max()) if frame.size else None,
        "mean_intensity": float(frame.mean()) if frame.size else None,
    }


def save_frame(
    cv2: Any,
    writer: csv.DictWriter[str],
    frames_dir: Path,
    frame: Any,
    saved_index: int,
    frame_id: int,
    capture_time_s: float,
    trigger: str,
) -> Path:
    filename = f"capture_{saved_index:06d}_frame_{frame_id:06d}.png"
    frame_path = frames_dir / filename
    if not cv2.imwrite(str(frame_path), frame):
        raise RuntimeError(f"Could not write frame image: {frame_path}")

    row = {
        "relative_path": f"frames/{filename}",
        "saved_index": saved_index,
        "frame_id": frame_id,
        "capture_time_unix_s": f"{capture_time_s:.9f}",
        "capture_time_iso": timestamp_iso(capture_time_s),
        "trigger": trigger,
        **frame_stats(frame),
    }
    writer.writerow(row)
    return frame_path


def preview_frame(cv2: Any, np: Any, frame: Any, frame_count: int, saved_count: int, fps: float, args: argparse.Namespace) -> Any:
    display_frame = frame
    if args.auto_contrast and frame.size:
        lo = float(np.percentile(frame, 1))
        hi = float(np.percentile(frame, 99))
        if hi > lo:
            scaled = (frame.astype(np.float32) - lo) * (255.0 / (hi - lo))
            display_frame = np.clip(scaled, 0, 255).astype(np.uint8)

    if display_frame.ndim == 2:
        vis = cv2.cvtColor(display_frame, cv2.COLOR_GRAY2BGR)
    else:
        vis = display_frame.copy()

    lines = [
        f"frame {frame_count}",
        f"saved {saved_count}",
        f"fps {fps:.1f}",
        f"shape {frame.shape}",
        "s/Space: save raw frame",
        "q/Esc/close window: quit",
    ]
    y = 28
    for line in lines:
        cv2.putText(vis, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        y += 24

    if args.scale != 1.0:
        vis = cv2.resize(vis, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_NEAREST)
    return vis


def write_metadata(
    metadata_path: Path,
    args: argparse.Namespace,
    paths: dict[str, Path],
    camera_info: dict[str, Any],
    started_at: str,
    completed_at: str,
    frames_acquired: int,
    frames_saved: int,
    incomplete_frames: int,
    elapsed_s: float,
) -> None:
    mean_fps = frames_acquired / elapsed_s if elapsed_s > 0 else None
    metadata = {
        "session": {
            "started_at": started_at,
            "completed_at": completed_at,
            "elapsed_s": elapsed_s,
            "frames_acquired": frames_acquired,
            "frames_saved": frames_saved,
            "incomplete_frames": incomplete_frames,
            "mean_fps": mean_fps,
        },
        "command": {
            "argv": sys.argv,
            "python_executable": sys.executable,
            "cwd": str(Path.cwd()),
        },
        "host": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
        },
        "paths": {
            "output_root": paths["root"],
            "session_dir": paths["session_dir"],
            "frames_dir": paths["frames_dir"],
            "manifest": paths["manifest"],
            "metadata": paths["metadata"],
        },
        "camera_settings_requested": {
            "camera_index": args.camera_index,
            "sensor_roi": args.sensor_roi,
            "pixel_format": args.pixel_format,
            "frame_rate": args.frame_rate,
            "exposure_us": args.exposure_us,
            "gain_auto": args.gain_auto,
            "gain_db": args.gain_db,
            "buffer_count": args.buffer_count,
            "timeout_ms": args.timeout_ms,
            "restore_settings": args.restore_settings,
        },
        "camera_info": camera_info,
        "capture_policy": {
            "preview": args.preview,
            "save_every": args.save_every,
            "seconds": args.seconds,
            "frames": args.frames,
            "format": "png",
            "saved_frames_are_raw": True,
            "preview_auto_contrast": args.auto_contrast,
            "preview_scale": args.scale,
        },
    }
    metadata_path.write_text(json.dumps(json_ready(metadata), indent=2, sort_keys=True) + "\n")


def main() -> int:
    args = parse_args()

    try:
        import cv2
        import numpy as np
        import PySpin
        from FLIRCam import configure_camera, restore_settings, window_is_closed
    except ModuleNotFoundError as exc:
        print(
            f"Could not import required camera module {exc.name!r}. "
            "Run this from the EyeTrack FLIR/PySpin environment.",
            file=sys.stderr,
        )
        return 1

    stop_requested = False

    def request_stop(_signum: int, _frame: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    cam = None
    acquired = False
    original_settings: dict[str, dict[str, Any]] | None = None
    camera_info: dict[str, Any] = {}
    paths: dict[str, Path] | None = None
    manifest_file: Any = None
    start_time = time.perf_counter()
    started_at = now_iso()
    frame_count = 0
    saved_count = 0
    incomplete_frames = 0
    fps = 0.0

    try:
        n_cameras = cam_list.GetSize()
        print(f"Detected cameras: {n_cameras}", flush=True)
        if n_cameras == 0:
            return 1
        if args.camera_index < 0 or args.camera_index >= n_cameras:
            raise ValueError(f"camera-index {args.camera_index} out of range for {n_cameras} camera(s)")

        cam = cam_list.GetByIndex(args.camera_index)
        camera_info, original_settings = configure_camera(cam, args)
        print(
            f"Using camera {args.camera_index}: {camera_info.get('model', '')} "
            f"serial={camera_info.get('serial', '')}",
            flush=True,
        )
        if "sensor_roi_applied" in camera_info:
            print(f"sensor_roi_applied={camera_info['sensor_roi_applied']}", flush=True)
        if "exposure_us" in camera_info:
            print(f"exposure_us={camera_info['exposure_us']}", flush=True)
        if "gain_auto" in camera_info:
            print(f"gain_auto={camera_info['gain_auto']}", flush=True)
        if "gain_db" in camera_info:
            print(f"gain_db={camera_info['gain_db']}", flush=True)
        if "frame_rate" in camera_info:
            print(f"frame_rate={camera_info['frame_rate']}", flush=True)

        paths = create_session_paths(args.output_dir, args.session_name)
        manifest_file = paths["manifest"].open("w", newline="")
        writer = csv.DictWriter(manifest_file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()

        print(f"Writing frames to: {paths['frames_dir']}", flush=True)
        print(f"Writing manifest to: {paths['manifest']}", flush=True)
        print(f"Writing metadata to: {paths['metadata']}", flush=True)

        if args.preview:
            cv2.namedWindow(args.window_name, cv2.WINDOW_NORMAL)
            print("Preview controls: s or Space saves; q or Esc quits; closing the window quits.", flush=True)

        cam.BeginAcquisition()
        acquired = True
        last_tick = time.perf_counter()

        while not stop_requested:
            if args.frames > 0 and frame_count >= args.frames:
                break
            if args.seconds > 0 and (time.perf_counter() - start_time) >= args.seconds:
                break

            image = cam.GetNextImage(args.timeout_ms)
            try:
                if image.IsIncomplete():
                    incomplete_frames += 1
                    continue
                frame = image.GetNDArray().copy()
            finally:
                image.Release()

            frame_count += 1
            capture_time_s = time.time()
            now = time.perf_counter()
            dt = now - last_tick
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps > 0 else 1.0 / dt
            last_tick = now

            trigger_parts: list[str] = []
            if args.save_every > 0 and frame_count % args.save_every == 0:
                trigger_parts.append("auto")

            if args.preview:
                vis = preview_frame(cv2, np, frame, frame_count, saved_count, fps, args)
                cv2.imshow(args.window_name, vis)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("s"), ord(" ")):
                    trigger_parts.append("manual")
                if key in (27, ord("q")) or window_is_closed(args.window_name):
                    stop_requested = True

            if trigger_parts:
                saved_count += 1
                trigger = "+".join(trigger_parts)
                frame_path = save_frame(
                    cv2,
                    writer,
                    paths["frames_dir"],
                    frame,
                    saved_count,
                    frame_count,
                    capture_time_s,
                    trigger,
                )
                print(f"saved {saved_count}: {frame_path}", flush=True)

        elapsed_s = time.perf_counter() - start_time
        print(f"frames_acquired={frame_count}", flush=True)
        print(f"frames_saved={saved_count}", flush=True)
        print(f"incomplete_frames={incomplete_frames}", flush=True)
        print(f"elapsed_s={elapsed_s:.3f}", flush=True)
        return 0 if frame_count > 0 else 1
    finally:
        if args.preview:
            cv2.destroyAllWindows()
        if cam is not None:
            if acquired:
                try:
                    cam.EndAcquisition()
                except Exception:
                    pass
            if args.restore_settings and original_settings is not None:
                try:
                    restore_settings(cam.GetNodeMap(), cam.GetTLStreamNodeMap(), original_settings)
                    print("Restored camera settings.", flush=True)
                except Exception as exc:
                    print(f"Could not restore every camera setting: {exc}", flush=True)
            try:
                cam.DeInit()
            except Exception:
                pass
            del cam
        if manifest_file is not None:
            manifest_file.close()
        if paths is not None:
            elapsed_s = time.perf_counter() - start_time
            write_metadata(
                paths["metadata"],
                args,
                paths,
                camera_info,
                started_at,
                now_iso(),
                frame_count,
                saved_count,
                incomplete_frames,
                elapsed_s,
            )
        cam_list.Clear()
        system.ReleaseInstance()


if __name__ == "__main__":
    raise SystemExit(main())
