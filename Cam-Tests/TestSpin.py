#!/usr/bin/env python3
from __future__ import annotations

import argparse
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


def set_enum_node(node_map: Any, name: str, entry_name: str) -> bool:
    node = PySpin.CEnumerationPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return False
    entry = node.GetEntryByName(entry_name)
    if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        return False
    node.SetIntValue(entry.GetValue())
    return True


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded PySpin camera frame-grab smoke test.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--frames", type=int, default=120, help="Number of complete frames to grab.")
    parser.add_argument("--timeout-ms", type=int, default=1000, help="PySpin GetNextImage timeout.")
    parser.add_argument("--pixel-format", default="Mono8", help="Optional GenICam PixelFormat value.")
    parser.add_argument(
        "--sensor-roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=None,
        help="Optional camera sensor ROI.",
    )
    parser.add_argument("--display", action="store_true", help="Show frames while grabbing.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    cam = None
    acquired = False

    try:
        n_cameras = cam_list.GetSize()
        print(f"Detected cameras: {n_cameras}")
        if n_cameras == 0:
            return 1
        if args.camera_index < 0 or args.camera_index >= n_cameras:
            raise ValueError(f"camera-index {args.camera_index} out of range for {n_cameras} camera(s)")

        cam = cam_list.GetByIndex(args.camera_index)
        tl_node_map = cam.GetTLDeviceNodeMap()
        print(
            f"Using camera {args.camera_index}: "
            f"{get_string_node(tl_node_map, 'DeviceModelName')} "
            f"serial={get_string_node(tl_node_map, 'DeviceSerialNumber')}"
        )

        cam.Init()
        node_map = cam.GetNodeMap()
        if args.pixel_format:
            print(f"PixelFormat {args.pixel_format}: {set_enum_node(node_map, 'PixelFormat', args.pixel_format)}")
        roi = configure_roi(node_map, args.sensor_roi)
        if roi is not None:
            print(f"sensor_roi_applied={roi}")

        shapes: list[tuple[int, ...]] = []
        incomplete = 0
        first_mean = np.nan
        cam.BeginAcquisition()
        acquired = True
        start = time.perf_counter()

        while len(shapes) < args.frames:
            image = cam.GetNextImage(args.timeout_ms)
            try:
                if image.IsIncomplete():
                    incomplete += 1
                    continue
                frame = image.GetNDArray().copy()
            finally:
                image.Release()

            if not shapes:
                first_mean = float(np.mean(frame))
            shapes.append(frame.shape)

            if args.display:
                cv2.imshow("PySpin smoke", frame)
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break

        elapsed = time.perf_counter() - start
        fps = len(shapes) / elapsed if elapsed > 0 else float("nan")
        print(f"frames_acquired={len(shapes)}")
        print(f"incomplete_frames={incomplete}")
        print(f"first_shape={shapes[0] if shapes else None}")
        print(f"first_frame_mean={first_mean:.3f}")
        print(f"elapsed_s={elapsed:.3f}")
        print(f"fps={fps:.2f}")
        return 0 if shapes else 1
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
