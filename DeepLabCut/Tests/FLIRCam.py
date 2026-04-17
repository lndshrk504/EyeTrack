#!/usr/bin/env python3
from __future__ import annotations

import argparse
import signal
import time
from typing import Any

import cv2
import numpy as np
import PySpin


def get_string_node(node_map: Any, name: str) -> str:
    node = PySpin.CStringPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return ""
    return str(node.GetValue())


def get_enum_node(node_map: Any, name: str) -> str | None:
    node = PySpin.CEnumerationPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return None
    entry = node.GetCurrentEntry()
    if entry is None or not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        return None
    return str(entry.GetSymbolic())


def set_enum_node(node_map: Any, name: str, entry_name: str) -> bool:
    node = PySpin.CEnumerationPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return False
    entry = node.GetEntryByName(entry_name)
    if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        return False
    node.SetIntValue(entry.GetValue())
    return True


def get_bool_node(node_map: Any, name: str) -> bool | None:
    node = PySpin.CBooleanPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return None
    return bool(node.GetValue())


def set_bool_node(node_map: Any, name: str, value: bool) -> bool:
    node = PySpin.CBooleanPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return False
    node.SetValue(bool(value))
    return True


def set_first_bool_node(node_map: Any, names: tuple[str, ...], value: bool) -> str | None:
    for name in names:
        if set_bool_node(node_map, name, value):
            return name
    return None


def get_float_node(node_map: Any, name: str) -> float | None:
    node = PySpin.CFloatPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return None
    return float(node.GetValue())


def set_float_node(node_map: Any, name: str, value: float) -> float | None:
    node = PySpin.CFloatPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return None
    actual = min(max(float(value), node.GetMin()), node.GetMax())
    node.SetValue(actual)
    return float(node.GetValue())


def get_int_node(node_map: Any, name: str) -> int | None:
    node = PySpin.CIntegerPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return None
    return int(node.GetValue())


def get_int_node_max(node_map: Any, name: str) -> int | None:
    node = PySpin.CIntegerPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return None
    return int(node.GetMax())


def set_int_node(node_map: Any, name: str, value: int) -> int | None:
    node = PySpin.CIntegerPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return None
    lo = int(node.GetMin())
    hi = int(node.GetMax())
    inc = int(node.GetInc()) if hasattr(node, "GetInc") else 1
    actual = min(max(int(value), lo), hi)
    if inc > 1:
        actual = lo + ((actual - lo) // inc) * inc
    node.SetValue(actual)
    return int(node.GetValue())


def read_settings(node_map: Any, stream_node_map: Any) -> dict[str, dict[str, Any]]:
    return {
        "enum": {
            "AcquisitionMode": get_enum_node(node_map, "AcquisitionMode"),
            "PixelFormat": get_enum_node(node_map, "PixelFormat"),
            "ExposureAuto": get_enum_node(node_map, "ExposureAuto"),
            "GainAuto": get_enum_node(node_map, "GainAuto"),
            "AcquisitionFrameRateAuto": get_enum_node(node_map, "AcquisitionFrameRateAuto"),
        },
        "bool": {
            "AcquisitionFrameRateEnable": get_bool_node(node_map, "AcquisitionFrameRateEnable"),
            "AcquisitionFrameRateEnabled": get_bool_node(node_map, "AcquisitionFrameRateEnabled"),
        },
        "float": {
            "ExposureTime": get_float_node(node_map, "ExposureTime"),
            "Gain": get_float_node(node_map, "Gain"),
            "AcquisitionFrameRate": get_float_node(node_map, "AcquisitionFrameRate"),
        },
        "int": {
            "Width": get_int_node(node_map, "Width"),
            "Height": get_int_node(node_map, "Height"),
            "OffsetX": get_int_node(node_map, "OffsetX"),
            "OffsetY": get_int_node(node_map, "OffsetY"),
        },
        "stream_enum": {
            "StreamBufferCountMode": get_enum_node(stream_node_map, "StreamBufferCountMode"),
            "StreamBufferHandlingMode": get_enum_node(stream_node_map, "StreamBufferHandlingMode"),
        },
        "stream_int": {
            "StreamBufferCountManual": get_int_node(stream_node_map, "StreamBufferCountManual"),
        },
    }


def restore_settings(node_map: Any, stream_node_map: Any, settings: dict[str, dict[str, Any]]) -> None:
    stream_mode = settings["stream_enum"].get("StreamBufferCountMode")
    if stream_mode:
        set_enum_node(stream_node_map, "StreamBufferCountMode", stream_mode)
    stream_count = settings["stream_int"].get("StreamBufferCountManual")
    if stream_count is not None:
        set_int_node(stream_node_map, "StreamBufferCountManual", stream_count)
    stream_handling = settings["stream_enum"].get("StreamBufferHandlingMode")
    if stream_handling:
        set_enum_node(stream_node_map, "StreamBufferHandlingMode", stream_handling)

    restore_roi(node_map, settings["int"])

    pixel_format = settings["enum"].get("PixelFormat")
    if pixel_format:
        set_enum_node(node_map, "PixelFormat", pixel_format)

    frame_auto = settings["enum"].get("AcquisitionFrameRateAuto")
    if frame_auto == "Off":
        set_enum_node(node_map, "AcquisitionFrameRateAuto", "Off")
        for name in ("AcquisitionFrameRateEnable", "AcquisitionFrameRateEnabled"):
            value = settings["bool"].get(name)
            if value is not None:
                set_bool_node(node_map, name, value)
        frame_rate = settings["float"].get("AcquisitionFrameRate")
        if frame_rate is not None:
            set_float_node(node_map, "AcquisitionFrameRate", frame_rate)
    elif frame_auto:
        set_enum_node(node_map, "AcquisitionFrameRateAuto", frame_auto)

    exposure_auto = settings["enum"].get("ExposureAuto")
    if exposure_auto == "Off":
        set_enum_node(node_map, "ExposureAuto", "Off")
        exposure = settings["float"].get("ExposureTime")
        if exposure is not None:
            set_float_node(node_map, "ExposureTime", exposure)
    elif exposure_auto:
        set_enum_node(node_map, "ExposureAuto", exposure_auto)

    gain_auto = settings["enum"].get("GainAuto")
    if gain_auto == "Off":
        set_enum_node(node_map, "GainAuto", "Off")
        gain = settings["float"].get("Gain")
        if gain is not None:
            set_float_node(node_map, "Gain", gain)
    elif gain_auto:
        set_enum_node(node_map, "GainAuto", gain_auto)

    acquisition_mode = settings["enum"].get("AcquisitionMode")
    if acquisition_mode:
        set_enum_node(node_map, "AcquisitionMode", acquisition_mode)


def restore_roi(node_map: Any, original_ints: dict[str, Any]) -> None:
    width = original_ints.get("Width")
    height = original_ints.get("Height")
    offset_x = original_ints.get("OffsetX")
    offset_y = original_ints.get("OffsetY")

    set_int_node(node_map, "OffsetX", 0)
    set_int_node(node_map, "OffsetY", 0)
    if width is not None:
        set_int_node(node_map, "Width", width)
    if height is not None:
        set_int_node(node_map, "Height", height)
    if offset_x is not None:
        set_int_node(node_map, "OffsetX", offset_x)
    if offset_y is not None:
        set_int_node(node_map, "OffsetY", offset_y)


def configure_full_frame(node_map: Any) -> tuple[int | None, int | None, int | None, int | None]:
    set_int_node(node_map, "OffsetX", 0)
    set_int_node(node_map, "OffsetY", 0)
    max_w = get_int_node_max(node_map, "Width")
    max_h = get_int_node_max(node_map, "Height")
    actual_w = set_int_node(node_map, "Width", max_w) if max_w is not None else get_int_node(node_map, "Width")
    actual_h = set_int_node(node_map, "Height", max_h) if max_h is not None else get_int_node(node_map, "Height")
    actual_x = set_int_node(node_map, "OffsetX", 0)
    actual_y = set_int_node(node_map, "OffsetY", 0)
    return actual_x, actual_y, actual_w, actual_h


def configure_roi(node_map: Any, roi: list[int] | None) -> tuple[int | None, int | None, int | None, int | None] | None:
    if roi is None:
        return None
    x, y, width, height = roi
    set_int_node(node_map, "OffsetX", 0)
    set_int_node(node_map, "OffsetY", 0)
    actual_w = set_int_node(node_map, "Width", width)
    actual_h = set_int_node(node_map, "Height", height)
    actual_x = set_int_node(node_map, "OffsetX", x)
    actual_y = set_int_node(node_map, "OffsetY", y)
    return actual_x, actual_y, actual_w, actual_h


def configure_frame_rate(node_map: Any, frame_rate: float | None) -> dict[str, Any]:
    if frame_rate is None:
        return {}

    info: dict[str, Any] = {}
    if set_enum_node(node_map, "AcquisitionFrameRateAuto", "Off"):
        info["frame_rate_auto"] = "Off"

    enable_node = set_first_bool_node(
        node_map,
        ("AcquisitionFrameRateEnable", "AcquisitionFrameRateEnabled"),
        True,
    )
    if enable_node is not None:
        info["frame_rate_enable_node"] = enable_node

    actual = set_float_node(node_map, "AcquisitionFrameRate", frame_rate)
    if actual is None:
        raise RuntimeError("Could not set AcquisitionFrameRate.")
    info["frame_rate"] = actual
    return info


def gain_auto_entry_name(value: str | None) -> str | None:
    if value is None:
        return None
    return {
        "off": "Off",
        "once": "Once",
        "continuous": "Continuous",
    }[value]


def configure_camera(cam: Any, args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    cam.Init()
    node_map = cam.GetNodeMap()
    tl_node_map = cam.GetTLDeviceNodeMap()
    stream_node_map = cam.GetTLStreamNodeMap()
    original_settings = read_settings(node_map, stream_node_map)

    info: dict[str, Any] = {
        "model": get_string_node(tl_node_map, "DeviceModelName"),
        "serial": get_string_node(tl_node_map, "DeviceSerialNumber"),
        "restore_settings": bool(args.restore_settings),
    }

    set_enum_node(node_map, "AcquisitionMode", "Continuous")
    if args.pixel_format:
        info["pixel_format_set"] = set_enum_node(node_map, "PixelFormat", args.pixel_format)

    if args.sensor_roi is not None:
        roi = configure_roi(node_map, args.sensor_roi)
        if roi is not None:
            info["sensor_roi_applied"] = roi
    elif args.full_frame:
        info["full_frame_applied"] = configure_full_frame(node_map)

    info.update(configure_frame_rate(node_map, args.frame_rate))

    if args.exposure_us is not None:
        set_enum_node(node_map, "ExposureAuto", "Off")
        info["exposure_us"] = set_float_node(node_map, "ExposureTime", args.exposure_us)

    gain_auto_entry = gain_auto_entry_name(args.gain_auto)
    if gain_auto_entry is not None and set_enum_node(node_map, "GainAuto", gain_auto_entry):
        info["gain_auto"] = gain_auto_entry

    if args.gain_auto == "off" and args.gain_db is not None:
        info["gain_db"] = set_float_node(node_map, "Gain", args.gain_db)

    set_enum_node(stream_node_map, "StreamBufferCountMode", "Manual")
    info["stream_buffer_count"] = set_int_node(stream_node_map, "StreamBufferCountManual", args.buffer_count)
    set_enum_node(stream_node_map, "StreamBufferHandlingMode", "NewestOnly")

    info["width"] = get_int_node(node_map, "Width")
    info["height"] = get_int_node(node_map, "Height")
    info["offset_x"] = get_int_node(node_map, "OffsetX")
    info["offset_y"] = get_int_node(node_map, "OffsetY")
    return info, original_settings


def auto_contrast(frame: np.ndarray) -> np.ndarray:
    if frame.size == 0:
        return frame
    lo = float(np.percentile(frame, 1))
    hi = float(np.percentile(frame, 99))
    if hi <= lo:
        return frame
    scaled = (frame.astype(np.float32) - lo) * (255.0 / (hi - lo))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def window_is_closed(window_name: str) -> bool:
    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def scale_for_display(frame: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return frame
    return cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)


def draw_overlay(frame: np.ndarray, frame_count: int, fps: float, args: argparse.Namespace) -> np.ndarray:
    if args.auto_contrast:
        frame = auto_contrast(frame)

    if frame.ndim == 2:
        vis = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        vis = frame.copy()

    if args.flip_horizontal:
        vis = cv2.flip(vis, 1)
    if args.flip_vertical:
        vis = cv2.flip(vis, 0)

    if args.no_overlay:
        return scale_for_display(vis, args.scale)

    lines = [
        f"frame {frame_count}",
        f"fps {fps:.1f}",
        f"shape {frame.shape}",
        "q/Esc/close window: quit",
    ]
    y = 28
    for line in lines:
        cv2.putText(vis, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        y += 24
    return scale_for_display(vis, args.scale)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open a full-frame FLIR/PySpin preview window.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--timeout-ms", type=int, default=1000, help="PySpin GetNextImage timeout.")
    parser.add_argument("--buffer-count", type=int, default=3, help="Host stream buffer count.")
    parser.add_argument("--pixel-format", default="", help="Optional GenICam PixelFormat value. Default leaves it unchanged.")
    parser.add_argument("--exposure-us", type=float, default=None, help="Optional manual exposure in microseconds.")
    parser.add_argument("--gain-db", type=float, default=None, help="Optional manual gain in dB.")
    parser.add_argument("--frame-rate", type=float, default=None, help="Optional target camera frame rate.")
    parser.add_argument(
        "--gain-auto",
        choices=["off", "once", "continuous"],
        default=None,
        help="Optional camera GainAuto mode.",
    )
    parser.add_argument(
        "--sensor-roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=None,
        help="Optional camera sensor ROI. If omitted, the preview uses the full sensor frame.",
    )
    parser.add_argument("--no-full-frame", dest="full_frame", action="store_false", help="Use the camera's current ROI.")
    parser.set_defaults(full_frame=True)
    parser.add_argument(
        "--no-restore-settings",
        dest="restore_settings",
        action="store_false",
        help="Leave preview camera settings on the camera after exit.",
    )
    parser.set_defaults(restore_settings=True)
    parser.add_argument("--scale", type=float, default=0.75, help="Display scale factor.")
    parser.add_argument("--auto-contrast", action="store_true", help="Stretch image contrast for easier setup viewing.")
    parser.add_argument("--flip-horizontal", action="store_true", help="Mirror the preview horizontally.")
    parser.add_argument("--flip-vertical", action="store_true", help="Mirror the preview vertically.")
    parser.add_argument("--no-overlay", action="store_true", help="Hide the status text overlay.")
    parser.add_argument("--window-name", default="FLIR Full Frame Preview")
    parser.add_argument("--frames", type=int, default=0, help="Optional frame limit. Default 0 means run until quit.")
    parser.add_argument("--seconds", type=float, default=0.0, help="Optional time limit. Default 0 means run until quit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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

    try:
        n_cameras = cam_list.GetSize()
        print(f"Detected cameras: {n_cameras}", flush=True)
        if n_cameras == 0:
            return 1
        if args.camera_index < 0 or args.camera_index >= n_cameras:
            raise ValueError(f"camera-index {args.camera_index} out of range for {n_cameras} camera(s)")

        cam = cam_list.GetByIndex(args.camera_index)
        info, original_settings = configure_camera(cam, args)
        print(
            f"Using camera {args.camera_index}: {info.get('model', '')} "
            f"serial={info.get('serial', '')}",
            flush=True,
        )
        print(
            f"preview_roi=({info.get('offset_x')}, {info.get('offset_y')}, "
            f"{info.get('width')}, {info.get('height')})",
            flush=True,
        )
        if "full_frame_applied" in info:
            print(f"full_frame_applied={info['full_frame_applied']}", flush=True)
        if "sensor_roi_applied" in info:
            print(f"sensor_roi_applied={info['sensor_roi_applied']}", flush=True)
        if "exposure_us" in info:
            print(f"exposure_us={info['exposure_us']}", flush=True)
        if "gain_db" in info:
            print(f"gain_db={info['gain_db']}", flush=True)
        if "gain_auto" in info:
            print(f"gain_auto={info['gain_auto']}", flush=True)
        if "frame_rate" in info:
            print(f"frame_rate={info['frame_rate']}", flush=True)
        if "frame_rate_auto" in info:
            print(f"frame_rate_auto={info['frame_rate_auto']}", flush=True)
        if "frame_rate_enable_node" in info:
            print(f"frame_rate_enable_node={info['frame_rate_enable_node']}", flush=True)
        print(f"restore_settings_on_exit={info['restore_settings']}", flush=True)
        print("Preview controls: q or Esc quits; closing the window quits.", flush=True)

        cv2.namedWindow(args.window_name, cv2.WINDOW_NORMAL)
        cam.BeginAcquisition()
        acquired = True

        start = time.perf_counter()
        last_tick = start
        frame_count = 0
        fps = 0.0

        while not stop_requested:
            if args.frames > 0 and frame_count >= args.frames:
                break
            if args.seconds > 0 and (time.perf_counter() - start) >= args.seconds:
                break

            image = cam.GetNextImage(args.timeout_ms)
            try:
                if image.IsIncomplete():
                    continue
                frame = image.GetNDArray().copy()
            finally:
                image.Release()

            frame_count += 1
            now = time.perf_counter()
            dt = now - last_tick
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps > 0 else 1.0 / dt
            last_tick = now

            vis = draw_overlay(frame, frame_count, fps, args)
            cv2.imshow(args.window_name, vis)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")) or window_is_closed(args.window_name):
                break

        elapsed = time.perf_counter() - start
        mean_fps = frame_count / elapsed if elapsed > 0 else float("nan")
        print(f"frames_displayed={frame_count}", flush=True)
        print(f"elapsed_s={elapsed:.3f}", flush=True)
        print(f"mean_fps={mean_fps:.2f}", flush=True)
        return 0 if frame_count > 0 else 1
    finally:
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
        cam_list.Clear()
        system.ReleaseInstance()


if __name__ == "__main__":
    raise SystemExit(main())
