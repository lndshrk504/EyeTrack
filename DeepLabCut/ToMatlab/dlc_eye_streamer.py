#!/usr/bin/env python3
from __future__ import annotations

"""
Reference implementation for real-time eye tracking with:
- FLIR / Point Grey camera via PySpin
- DeepLabCut-Live inference
- pupil diameter calculation
- ZeroMQ streaming over localhost
- live overlay window

This script is intentionally conservative and robust:
- camera buffers are copied into NumPy arrays before image release;
- acquisition, inference, and display are decoupled with bounded queues;
- old frames are dropped when downstream consumers fall behind.

That makes the pipeline stable for real experiments at the cost of one copy per
frame. For a small Mono8 eye ROI, that copy is usually not the bottleneck.
"""

import argparse
import csv
import math
import queue
import signal
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
import zmq

try:
    import PySpin
except Exception as exc:  # pragma: no cover - import-time hardware dependency
    raise SystemExit(f"Could not import PySpin: {exc}") from exc

try:
    from dlclive import DLCLive
except Exception as exc:  # pragma: no cover - import-time model dependency
    raise SystemExit(f"Could not import dlclive: {exc}") from exc


@dataclass
class FramePacket:
    frame_id: int
    capture_time_unix_s: float
    capture_time_unix_ns: int
    frame: np.ndarray


@dataclass
class DisplayPacket:
    frame_id: int
    frame: np.ndarray
    pose: np.ndarray
    metrics: dict[str, Any]


SCHEMA_VERSION = 1
SOURCE_NAME = "dlc_eye_streamer"


MODEL_PRESETS: dict[str, dict[str, Any]] = {
    "yanglab-pupil8": {
        "description": "Bundled 8-point YangLab pupil model",
        "kp_top": 2,
        "kp_bottom": 6,
        "kp_left": 0,
        "kp_right": 4,
        "kp_center": None,
        "point_names": [
            "Lpupil",
            "LDpupil",
            "Dpupil",
            "DRpupil",
            "Rpupil",
            "RVpupil",
            "Vpupil",
            "VLpupil",
        ],
    },
}


class RateMeter:
    def __init__(self, window: int = 50) -> None:
        self._times: deque[float] = deque(maxlen=window)
        self._lock = threading.Lock()
        self._last_rate: Optional[float] = None

    def tick(self, t: Optional[float] = None) -> Optional[float]:
        if t is None:
            t = time.perf_counter()
        with self._lock:
            self._times.append(t)
            if len(self._times) < 2:
                self._last_rate = None
            else:
                dt = self._times[-1] - self._times[0]
                self._last_rate = None if dt <= 0 else (len(self._times) - 1) / dt
            return self._last_rate

    def current(self) -> Optional[float]:
        with self._lock:
            return self._last_rate


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr, flush=True)


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def drop_put(q: "queue.Queue[Any]", item: Any) -> None:
    try:
        q.put_nowait(item)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        q.put_nowait(item)


def _get_enum_entry(node: Any, entry_name: str) -> Any:
    entry = node.GetEntryByName(entry_name)
    if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        raise RuntimeError(f"Entry {entry_name!r} not readable")
    return entry


def set_enum_node(node_map: Any, name: str, entry_name: str) -> bool:
    node = PySpin.CEnumerationPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return False
    entry = _get_enum_entry(node, entry_name)
    node.SetIntValue(entry.GetValue())
    return True


def set_bool_node(node_map: Any, name: str, value: bool) -> bool:
    node = PySpin.CBooleanPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return False
    node.SetValue(bool(value))
    return True


def set_float_node(node_map: Any, name: str, value: float) -> Optional[float]:
    node = PySpin.CFloatPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsWritable(node):
        return None
    lo = node.GetMin()
    hi = node.GetMax()
    actual = min(max(float(value), lo), hi)
    node.SetValue(actual)
    return float(node.GetValue())


def set_int_node(node_map: Any, name: str, value: int) -> Optional[int]:
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


def get_string_node(node_map: Any, name: str) -> Optional[str]:
    node = PySpin.CStringPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return None
    return str(node.GetValue())


def configure_sensor_roi(node_map: Any, x: int, y: int, width: int, height: int) -> tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    # Safest order on GenICam cameras: reset offsets, shrink sensor window, then reapply offsets.
    set_int_node(node_map, "OffsetX", 0)
    set_int_node(node_map, "OffsetY", 0)
    actual_w = set_int_node(node_map, "Width", width)
    actual_h = set_int_node(node_map, "Height", height)
    actual_x = set_int_node(node_map, "OffsetX", x)
    actual_y = set_int_node(node_map, "OffsetY", y)
    return actual_x, actual_y, actual_w, actual_h


def configure_camera(cam: Any, args: argparse.Namespace) -> dict[str, Any]:
    cam.Init()
    node_map = cam.GetNodeMap()
    tl_node_map = cam.GetTLDeviceNodeMap()
    stream_node_map = cam.GetTLStreamNodeMap()

    info: dict[str, Any] = {
        "serial": get_string_node(tl_node_map, "DeviceSerialNumber"),
        "model": get_string_node(tl_node_map, "DeviceModelName"),
    }

    set_enum_node(node_map, "AcquisitionMode", "Continuous")
    set_enum_node(node_map, "ExposureAuto", "Off")
    set_enum_node(node_map, "GainAuto", "Off")

    if args.sensor_roi is not None:
        x, y, w, h = args.sensor_roi
        ax, ay, aw, ah = configure_sensor_roi(node_map, x, y, w, h)
        info["sensor_roi_applied"] = (ax, ay, aw, ah)

    if args.pixel_format:
        set_enum_node(node_map, "PixelFormat", args.pixel_format)

    if args.exposure_us is not None:
        info["exposure_us"] = set_float_node(node_map, "ExposureTime", args.exposure_us)

    if args.gain_db is not None:
        info["gain_db"] = set_float_node(node_map, "Gain", args.gain_db)

    if args.frame_rate is not None:
        if set_bool_node(node_map, "AcquisitionFrameRateEnable", True):
            info["frame_rate"] = set_float_node(node_map, "AcquisitionFrameRate", args.frame_rate)

    # Keep the transport queue shallow; for closed-loop work, newest frame wins.
    set_enum_node(stream_node_map, "StreamBufferCountMode", "Manual")
    info["stream_buffer_count"] = set_int_node(stream_node_map, "StreamBufferCountManual", args.buffer_count)
    set_enum_node(stream_node_map, "StreamBufferHandlingMode", "NewestOnly")

    return info


def normalize_pose(pose: np.ndarray) -> np.ndarray:
    arr = np.asarray(pose)
    if arr.ndim == 3:
        # For multi-animal arrays, use the first individual by default.
        arr = arr[0]
    if arr.ndim != 2:
        raise ValueError(f"Unexpected pose shape: {arr.shape}")
    if arr.shape[1] == 2:
        ones = np.ones((arr.shape[0], 1), dtype=arr.dtype)
        arr = np.concatenate([arr, ones], axis=1)
    if arr.shape[1] < 3:
        raise ValueError(f"Unexpected pose width: {arr.shape}")
    return arr.astype(np.float32, copy=False)


def prepare_frame_for_dlc(frame: np.ndarray, rgb_for_dlc: bool) -> np.ndarray:
    if frame.ndim == 2 and rgb_for_dlc:
        return cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    return frame


def point_is_valid(pose: np.ndarray, idx: Optional[int], pcutoff: float) -> bool:
    if idx is None:
        return False
    if idx < 0 or idx >= pose.shape[0]:
        return False
    x, y, p = pose[idx, :3]
    return bool(np.isfinite(x) and np.isfinite(y) and np.isfinite(p) and float(p) >= pcutoff)


def pair_distance(pose: np.ndarray, a: Optional[int], b: Optional[int], pcutoff: float) -> Optional[float]:
    if not point_is_valid(pose, a, pcutoff) or not point_is_valid(pose, b, pcutoff):
        return None
    return safe_float(np.linalg.norm(pose[a, :2] - pose[b, :2]))


def compute_eye_metrics(
    pose: np.ndarray,
    top_idx: int,
    bottom_idx: int,
    left_idx: int,
    right_idx: int,
    center_idx: Optional[int],
    pcutoff: float,
) -> dict[str, Any]:
    pose = normalize_pose(pose)

    valid_mask = pose[:, 2] >= pcutoff
    valid_points = int(np.sum(valid_mask))
    confidence_mean = safe_float(np.mean(pose[:, 2]))

    if point_is_valid(pose, center_idx, pcutoff):
        center_x = safe_float(pose[center_idx, 0])
        center_y = safe_float(pose[center_idx, 1])
    elif valid_points > 0:
        center_x = safe_float(np.mean(pose[valid_mask, 0]))
        center_y = safe_float(np.mean(pose[valid_mask, 1]))
    else:
        center_x = None
        center_y = None

    horiz = pair_distance(pose, left_idx, right_idx, pcutoff)
    vert = pair_distance(pose, top_idx, bottom_idx, pcutoff)

    if horiz is not None and vert is not None:
        diameter = safe_float(0.5 * (horiz + vert))
    elif horiz is not None:
        diameter = horiz
    else:
        diameter = vert

    return {
        "center_x": center_x,
        "center_y": center_y,
        "diameter_px": diameter,
        "diameter_h_px": horiz,
        "diameter_v_px": vert,
        "confidence_mean": confidence_mean,
        "valid_points": valid_points,
    }


def make_points_dict(pose: np.ndarray, point_names: list[str]) -> dict[str, list[Optional[float]]]:
    pose = normalize_pose(pose)
    out: dict[str, list[Optional[float]]] = {}
    for i, row in enumerate(pose):
        name = point_names[i] if i < len(point_names) else f"kp{i}"
        out[name] = [safe_float(row[0]), safe_float(row[1]), safe_float(row[2])]
    return out


def pose_to_acquired_frame(pose: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    pose = normalize_pose(pose).copy()
    if args.pose_coordinate_frame == "crop" and args.crop is not None:
        crop_x1, _crop_x2, crop_y1, _crop_y2 = args.crop
        pose[:, 0] += float(crop_x1)
        pose[:, 1] += float(crop_y1)
    return pose


def sample_status(metrics: dict[str, Any], expected_point_count: int) -> str:
    valid_points = int(metrics.get("valid_points") or 0)
    if expected_point_count > 0 and valid_points >= expected_point_count:
        return "ok"
    if valid_points > 0:
        return "partial_points"
    return "no_points"


def crop_metadata(args: argparse.Namespace) -> dict[str, Optional[int]]:
    if args.crop is None:
        return {"crop_x1": None, "crop_x2": None, "crop_y1": None, "crop_y2": None}
    crop_x1, crop_x2, crop_y1, crop_y2 = args.crop
    return {
        "crop_x1": int(crop_x1),
        "crop_x2": int(crop_x2),
        "crop_y1": int(crop_y1),
        "crop_y2": int(crop_y2),
    }


def sensor_roi_metadata(camera_info: dict[str, Any]) -> dict[str, Optional[int]]:
    roi = camera_info.get("sensor_roi_applied")
    if roi is None:
        return {
            "sensor_roi_x": None,
            "sensor_roi_y": None,
            "sensor_roi_width": None,
            "sensor_roi_height": None,
        }
    x, y, w, h = roi
    return {
        "sensor_roi_x": None if x is None else int(x),
        "sensor_roi_y": None if y is None else int(y),
        "sensor_roi_width": None if w is None else int(w),
        "sensor_roi_height": None if h is None else int(h),
    }


def sample_metadata(args: argparse.Namespace, point_names: list[str]) -> dict[str, Any]:
    camera_info = getattr(args, "camera_info", {}) or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE_NAME,
        "model_preset": args.model_preset,
        "model_type": args.model_type,
        "point_names": list(point_names),
        "point_count": int(len(point_names)),
        "pcutoff": float(args.pcutoff),
        "pose_coordinate_frame": args.pose_coordinate_frame,
        "camera_serial": camera_info.get("serial"),
        "camera_model": camera_info.get("model"),
        **sensor_roi_metadata(camera_info),
        **crop_metadata(args),
    }


def make_metadata_message(args: argparse.Namespace, point_names: list[str]) -> dict[str, Any]:
    csv_path = None if args.csv is None else str(Path(args.csv).expanduser())
    return {
        "message_type": "metadata",
        "created_time_unix_s": time.time(),
        "created_time_unix_ns": time.time_ns(),
        "address": args.address,
        "csv_path": csv_path,
        "display_enabled": bool(args.display),
        "display_scale": float(args.display_scale),
        "display_fps": float(args.display_fps),
        "pub_hwm": int(args.pub_hwm),
        "dynamic_crop": bool(args.dynamic_crop),
        "dynamic_margin": int(args.dynamic_margin),
        **sample_metadata(args, point_names),
    }


CSV_BASE_FIELDNAMES = [
    "message_type",
    "schema_version",
    "sample_status",
    "source",
    "frame_id",
    "capture_time_unix_s",
    "capture_time_unix_ns",
    "publish_time_unix_s",
    "publish_time_unix_ns",
    "model_preset",
    "model_type",
    "point_count",
    "camera_serial",
    "camera_model",
    "sensor_roi_x",
    "sensor_roi_y",
    "sensor_roi_width",
    "sensor_roi_height",
    "crop_x1",
    "crop_x2",
    "crop_y1",
    "crop_y2",
    "pose_coordinate_frame",
    "center_x",
    "center_y",
    "diameter_px",
    "diameter_h_px",
    "diameter_v_px",
    "confidence_mean",
    "valid_points",
    "camera_fps",
    "inference_fps",
    "latency_ms",
]


def csv_point_prefixes(point_names: list[str], n_points: int) -> list[str]:
    prefixes: list[str] = []
    seen: dict[str, int] = {}
    for i in range(n_points):
        base = point_names[i] if i < len(point_names) and point_names[i] else f"kp{i}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        prefixes.append(base if count == 0 else f"{base}_{count}")
    return prefixes


def make_csv_fieldnames(pose: np.ndarray, point_names: list[str]) -> list[str]:
    pose = normalize_pose(pose)
    fieldnames = list(CSV_BASE_FIELDNAMES)
    for name in csv_point_prefixes(point_names, pose.shape[0]):
        fieldnames.extend([f"{name}_x", f"{name}_y", f"{name}_likelihood"])
    return fieldnames


def make_csv_row(payload: dict[str, Any], pose: np.ndarray, point_names: list[str]) -> dict[str, Any]:
    pose = normalize_pose(pose)
    row = {name: payload.get(name) for name in CSV_BASE_FIELDNAMES}
    for name, point in zip(csv_point_prefixes(point_names, pose.shape[0]), pose):
        row[f"{name}_x"] = safe_float(point[0])
        row[f"{name}_y"] = safe_float(point[1])
        row[f"{name}_likelihood"] = safe_float(point[2])
    return row


def draw_overlay(
    frame: np.ndarray,
    pose: np.ndarray,
    metrics: dict[str, Any],
    point_names: list[str],
    pcutoff: float,
    display_scale: float,
    left_idx: int,
    right_idx: int,
    top_idx: int,
    bottom_idx: int,
    center_idx: Optional[int],
) -> np.ndarray:
    if frame.ndim == 2:
        vis = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    else:
        vis = frame.copy()

    pose = normalize_pose(pose)

    # Draw diameter axes first.
    if point_is_valid(pose, left_idx, pcutoff) and point_is_valid(pose, right_idx, pcutoff):
        a = tuple(np.round(pose[left_idx, :2]).astype(int))
        b = tuple(np.round(pose[right_idx, :2]).astype(int))
        cv2.line(vis, a, b, (255, 255, 0), 1, cv2.LINE_AA)

    if point_is_valid(pose, top_idx, pcutoff) and point_is_valid(pose, bottom_idx, pcutoff):
        a = tuple(np.round(pose[top_idx, :2]).astype(int))
        b = tuple(np.round(pose[bottom_idx, :2]).astype(int))
        cv2.line(vis, a, b, (255, 255, 0), 1, cv2.LINE_AA)

    for i, row in enumerate(pose):
        x, y, p = float(row[0]), float(row[1]), float(row[2])
        if not (math.isfinite(x) and math.isfinite(y)):
            continue
        color = (0, 255, 0) if p >= pcutoff else (0, 0, 255)
        cv2.circle(vis, (int(round(x)), int(round(y))), 3, color, -1, cv2.LINE_AA)
        label = point_names[i] if i < len(point_names) else f"kp{i}"
        cv2.putText(
            vis,
            label,
            (int(round(x)) + 5, int(round(y)) - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            color,
            1,
            cv2.LINE_AA,
        )

    if point_is_valid(pose, center_idx, pcutoff):
        cx = int(round(float(pose[center_idx, 0])))
        cy = int(round(float(pose[center_idx, 1])))
        cv2.circle(vis, (cx, cy), 5, (0, 255, 255), 1, cv2.LINE_AA)
    elif metrics.get("center_x") is not None and metrics.get("center_y") is not None:
        cx = int(round(float(metrics["center_x"])))
        cy = int(round(float(metrics["center_y"])))
        cv2.circle(vis, (cx, cy), 5, (0, 255, 255), 1, cv2.LINE_AA)

    text_lines = [
        f"frame: {metrics.get('frame_id', -1)}",
        f"diam(px): {metrics.get('diameter_px') if metrics.get('diameter_px') is not None else 'nan'}",
        f"center: ({metrics.get('center_x') if metrics.get('center_x') is not None else 'nan'}, {metrics.get('center_y') if metrics.get('center_y') is not None else 'nan'})",
        f"conf: {metrics.get('confidence_mean') if metrics.get('confidence_mean') is not None else 'nan'}",
        f"cam_fps: {metrics.get('camera_fps') if metrics.get('camera_fps') is not None else 'nan'}",
        f"dlc_fps: {metrics.get('inference_fps') if metrics.get('inference_fps') is not None else 'nan'}",
        f"lat(ms): {metrics.get('latency_ms') if metrics.get('latency_ms') is not None else 'nan'}",
    ]
    y0 = 36
    for line in text_lines:
        cv2.putText(vis, line, (10, y0), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        y0 += 34

    if display_scale != 1.0:
        vis = cv2.resize(vis, None, fx=display_scale, fy=display_scale, interpolation=cv2.INTER_NEAREST)

    return vis


def acquisition_loop(
    cam: Any,
    frame_queue: "queue.Queue[FramePacket]",
    stop_event: threading.Event,
    timeout_ms: int,
    camera_rate: RateMeter,
) -> None:
    frame_id = 0
    cam.BeginAcquisition()
    try:
        while not stop_event.is_set():
            try:
                image = cam.GetNextImage(timeout_ms)
            except PySpin.SpinnakerException as exc:
                if stop_event.is_set():
                    break
                eprint(f"[acq] GetNextImage failed: {exc}")
                continue

            try:
                if image.IsIncomplete():
                    continue
                frame = image.GetNDArray().copy()
            finally:
                image.Release()

            frame_id += 1
            t_ns = time.time_ns()
            t_s = t_ns / 1e9
            camera_rate.tick()
            pkt = FramePacket(frame_id=frame_id, capture_time_unix_s=t_s, capture_time_unix_ns=t_ns, frame=frame)
            drop_put(frame_queue, pkt)
    finally:
        try:
            cam.EndAcquisition()
        except Exception:
            pass


def inference_loop(
    args: argparse.Namespace,
    frame_queue: "queue.Queue[FramePacket]",
    display_queue: "queue.Queue[DisplayPacket]",
    stop_event: threading.Event,
    camera_rate: RateMeter,
) -> None:
    context = zmq.Context.instance()
    pub = context.socket(zmq.PUB)
    pub.sndhwm = int(args.pub_hwm)
    pub.linger = 0
    pub.bind(args.address)

    csv_file = None
    csv_writer = None

    try:
        dlc = DLCLive(
            args.model_path,
            model_type=args.model_type,
            cropping=args.crop,
            dynamic=(args.dynamic_crop, args.pcutoff, args.dynamic_margin),
            display=False,
        )

        eprint("[inf] waiting for first frame...")
        first_pkt: Optional[FramePacket] = None
        while not stop_event.is_set() and first_pkt is None:
            try:
                first_pkt = frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

        if first_pkt is None:
            return

        init_img = prepare_frame_for_dlc(first_pkt.frame, rgb_for_dlc=not args.pass_gray_to_dlc)
        dlc.init_inference(init_img)
        eprint("[inf] DLCLive initialized")

        point_names = list(args.point_names)
        static_sample_metadata = sample_metadata(args, point_names)
        pub.send_json(make_metadata_message(args, point_names))

        inference_rate = RateMeter(window=50)
        last_display_t = 0.0
        current_pkt = first_pkt

        while not stop_event.is_set():
            infer_img = prepare_frame_for_dlc(current_pkt.frame, rgb_for_dlc=not args.pass_gray_to_dlc)
            pose = pose_to_acquired_frame(dlc.get_pose(infer_img), args)

            metrics = compute_eye_metrics(
                pose,
                top_idx=args.kp_top,
                bottom_idx=args.kp_bottom,
                left_idx=args.kp_left,
                right_idx=args.kp_right,
                center_idx=args.kp_center,
                pcutoff=args.pcutoff,
            )

            t_pub_ns = time.time_ns()
            t_pub_s = t_pub_ns / 1e9
            inf_fps = inference_rate.tick()
            cam_fps = camera_rate.current()
            latency_ms = 1000.0 * (t_pub_s - current_pkt.capture_time_unix_s)

            payload: dict[str, Any] = {
                "message_type": "sample",
                "schema_version": SCHEMA_VERSION,
                **static_sample_metadata,
                "frame_id": int(current_pkt.frame_id),
                "capture_time_unix_s": float(current_pkt.capture_time_unix_s),
                "capture_time_unix_ns": int(current_pkt.capture_time_unix_ns),
                "publish_time_unix_s": float(t_pub_s),
                "publish_time_unix_ns": int(t_pub_ns),
                "camera_fps": safe_float(cam_fps),
                "inference_fps": safe_float(inf_fps),
                "latency_ms": safe_float(latency_ms),
                **metrics,
            }

            payload["sample_status"] = sample_status(metrics, expected_point_count=len(point_names))
            payload["points"] = make_points_dict(pose, point_names)

            if args.csv is not None and csv_writer is None:
                csv_path = Path(args.csv)
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                csv_file = csv_path.open("w", newline="")
                csv_writer = csv.DictWriter(csv_file, fieldnames=make_csv_fieldnames(pose, point_names))
                csv_writer.writeheader()

            pub.send_json(payload)

            if csv_writer is not None:
                csv_writer.writerow(make_csv_row(payload, pose, point_names))
                csv_file.flush()

            now = time.perf_counter()
            if args.display and (now - last_display_t) >= (1.0 / max(args.display_fps, 1e-6)):
                last_display_t = now
                drop_put(
                    display_queue,
                    DisplayPacket(
                        frame_id=current_pkt.frame_id,
                        frame=current_pkt.frame,
                        pose=pose.copy(),
                        metrics=payload,
                    ),
                )

            try:
                current_pkt = frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
    except Exception as exc:
        stop_event.set()
        eprint(f"[inf] stopping because of error: {exc}")
        raise
    finally:
        if csv_file is not None:
            csv_file.close()
        pub.close(0)


def display_window_is_closed(window_name: str) -> bool:
    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


def display_loop(
    display_queue: "queue.Queue[DisplayPacket]",
    stop_event: threading.Event,
    args: argparse.Namespace,
) -> None:
    window_name = args.window_name
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        while not stop_event.is_set():
            try:
                pkt = display_queue.get(timeout=0.1)
            except queue.Empty:
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")) or display_window_is_closed(window_name):
                    stop_event.set()
                    break
                continue

            if display_window_is_closed(window_name):
                stop_event.set()
                break

            vis = draw_overlay(
                frame=pkt.frame,
                pose=pkt.pose,
                metrics=pkt.metrics,
                point_names=list(args.point_names),
                pcutoff=args.pcutoff,
                display_scale=args.display_scale,
                left_idx=args.kp_left,
                right_idx=args.kp_right,
                top_idx=args.kp_top,
                bottom_idx=args.kp_bottom,
                center_idx=args.kp_center,
            )
            cv2.imshow(window_name, vis)
            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")) or display_window_is_closed(window_name):
                stop_event.set()
                break
    finally:
        cv2.destroyAllWindows()


def apply_model_preset(args: argparse.Namespace) -> argparse.Namespace:
    if args.model_preset != "none":
        preset = MODEL_PRESETS[args.model_preset]
        for attr in ("kp_top", "kp_bottom", "kp_left", "kp_right", "kp_center"):
            if getattr(args, attr) is None:
                setattr(args, attr, preset[attr])
        if not args.point_names:
            args.point_names = list(preset["point_names"])

    required = {
        "--kp-top": args.kp_top,
        "--kp-bottom": args.kp_bottom,
        "--kp-left": args.kp_left,
        "--kp-right": args.kp_right,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise SystemExit(
            "Missing keypoint indices: "
            + ", ".join(missing)
            + ". Use --model-preset yanglab-pupil8 for the bundled model, "
            + "or pass all --kp-* arguments for a custom model."
        )
    return args


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FLIR + DLCLive + ZeroMQ eye tracker")
    p.add_argument("--model-path", required=True, help="Path to exported DLCLive model")
    p.add_argument(
        "--model-preset",
        default="yanglab-pupil8",
        choices=["yanglab-pupil8", "none"],
        help=(
            "Keypoint mapping preset. Default matches the bundled YangLab 8-point "
            "pupil model. Use 'none' and pass --kp-* arguments for a custom model."
        ),
    )
    p.add_argument(
        "--model-type",
        default="base",
        choices=["base", "pytorch", "tensorrt", "tflite"],
        help="DLCLive model backend",
    )
    p.add_argument("--address", default="tcp://127.0.0.1:5555", help="ZeroMQ PUB endpoint")
    p.add_argument("--pub-hwm", type=int, default=10000, help="ZeroMQ PUB high-water mark")
    p.add_argument("--camera-index", type=int, default=0, help="PySpin camera index")
    p.add_argument("--timeout-ms", type=int, default=1000, help="PySpin GetNextImage timeout")
    p.add_argument("--buffer-count", type=int, default=3, help="Stream buffer count on host")
    p.add_argument("--pixel-format", default="Mono8", help="Camera pixel format enum name")
    p.add_argument("--exposure-us", type=float, default=2000.0, help="Manual exposure in microseconds")
    p.add_argument("--gain-db", type=float, default=0.0, help="Manual gain in dB")
    p.add_argument("--frame-rate", type=float, default=None, help="Optional target acquisition frame rate")
    p.add_argument(
        "--sensor-roi",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        default=None,
        help="Optional camera sensor ROI: offset_x offset_y width height",
    )
    p.add_argument(
        "--crop",
        type=int,
        nargs=4,
        metavar=("X1", "X2", "Y1", "Y2"),
        default=None,
        help="Optional DLCLive fixed crop in image pixels",
    )
    p.add_argument(
        "--pose-coordinate-frame",
        choices=["acquired-frame", "crop"],
        default="acquired-frame",
        help=(
            "Coordinate frame returned by DLCLive when --crop is used. "
            "Use 'crop' only if your DLCLive build returns crop-relative points; "
            "the streamer will add crop X1/Y1 before publishing."
        ),
    )
    p.add_argument("--dynamic-crop", action="store_true", help="Enable DLCLive dynamic cropping")
    p.add_argument("--dynamic-margin", type=int, default=20, help="Dynamic crop margin in pixels")
    p.add_argument("--pass-gray-to-dlc", action="store_true", help="Pass 2D grayscale frames directly into DLCLive")
    p.add_argument("--pcutoff", type=float, default=0.5, help="Likelihood threshold for valid keypoints")

    p.add_argument("--kp-top", type=int, default=None, help="Index of top pupil keypoint")
    p.add_argument("--kp-bottom", type=int, default=None, help="Index of bottom pupil keypoint")
    p.add_argument("--kp-left", type=int, default=None, help="Index of left pupil keypoint")
    p.add_argument("--kp-right", type=int, default=None, help="Index of right pupil keypoint")
    p.add_argument("--kp-center", type=int, default=None, help="Optional index of center pupil keypoint")
    p.add_argument(
        "--point-names",
        nargs="*",
        default=[],
        help="Optional point names in model order; improves overlay labels and published JSON",
    )

    p.add_argument("--display", action="store_true", help="Open overlay window")
    p.add_argument("--display-fps", type=float, default=30.0, help="Max overlay window refresh rate")
    p.add_argument("--display-scale", type=float, default=1.0, help="Scale factor for display window")
    p.add_argument("--window-name", default="DLC Eye Tracker", help="Display window title")
    p.add_argument("--csv", required=True, help="Required CSV log path")
    return apply_model_preset(p.parse_args())


def main() -> int:
    args = parse_args()
    stop_event = threading.Event()

    def _handle_stop(signum: int, _frame: Any) -> None:
        eprint(f"[main] received signal {signum}; stopping...")
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()

    if cam_list.GetSize() == 0:
        cam_list.Clear()
        system.ReleaseInstance()
        eprint("No PySpin cameras detected")
        return 1

    if args.camera_index < 0 or args.camera_index >= cam_list.GetSize():
        cam_list.Clear()
        system.ReleaseInstance()
        eprint(f"camera-index {args.camera_index} out of range (n={cam_list.GetSize()})")
        return 1

    cam = cam_list.GetByIndex(args.camera_index)

    try:
        info = configure_camera(cam, args)
        args.camera_info = info
        eprint(f"[main] camera model={info.get('model')} serial={info.get('serial')}")
        if "sensor_roi_applied" in info:
            eprint(f"[main] sensor ROI applied={info['sensor_roi_applied']}")
        if "frame_rate" in info and info["frame_rate"] is not None:
            eprint(f"[main] frame_rate={info['frame_rate']}")
        if "exposure_us" in info and info["exposure_us"] is not None:
            eprint(f"[main] exposure_us={info['exposure_us']}")
        if "gain_db" in info and info["gain_db"] is not None:
            eprint(f"[main] gain_db={info['gain_db']}")

        frame_queue: "queue.Queue[FramePacket]" = queue.Queue(maxsize=2)
        display_queue: "queue.Queue[DisplayPacket]" = queue.Queue(maxsize=2)
        camera_rate = RateMeter(window=50)

        acq_thread = threading.Thread(
            target=acquisition_loop,
            name="acquisition",
            args=(cam, frame_queue, stop_event, args.timeout_ms, camera_rate),
            daemon=True,
        )
        inf_thread = threading.Thread(
            target=inference_loop,
            name="inference",
            args=(args, frame_queue, display_queue, stop_event, camera_rate),
            daemon=True,
        )

        acq_thread.start()
        inf_thread.start()

        if args.display:
            display_loop(display_queue, stop_event, args)
        else:
            while not stop_event.is_set():
                time.sleep(0.1)

        stop_event.set()
        acq_thread.join(timeout=2.0)
        inf_thread.join(timeout=2.0)
        return 0
    finally:
        try:
            cam.DeInit()
        except Exception:
            pass
        del cam
        cam_list.Clear()
        system.ReleaseInstance()


if __name__ == "__main__":
    raise SystemExit(main())
