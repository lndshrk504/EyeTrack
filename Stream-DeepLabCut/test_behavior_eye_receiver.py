#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib import parse, request

HERE = Path(__file__).resolve().parent
POINT_NAMES = ["Lpupil", "LDpupil", "Dpupil", "DRpupil", "Rpupil", "RVpupil", "Vpupil", "VLpupil"]
STREAMER_CSV_PATH = "/tmp/EyeTrack/streamer_test.csv"
STREAMER_METADATA_PATH = "/tmp/EyeTrack/streamer_test_metadata.json"
REQUIRED_STREAM_METADATA_FIELDS = {
    "stream_metadata_version",
    "schema_version",
    "source",
    "address",
    "csv_path",
    "metadata_path",
    "model_path",
    "model_preset",
    "model_type",
    "kp_top",
    "kp_bottom",
    "kp_left",
    "kp_right",
    "kp_center",
    "point_names",
    "point_count",
    "pcutoff",
    "pose_coordinate_frame",
    "camera_index",
    "camera_serial",
    "camera_model",
    "timeout_ms",
    "buffer_count",
    "buffer_count_requested",
    "buffer_count_applied",
    "pixel_format",
    "pixel_format_requested",
    "pixel_format_applied",
    "exposure_us_requested",
    "exposure_us_applied",
    "gain_db_requested",
    "gain_db_applied",
    "gain_auto_requested",
    "gain_auto_applied",
    "frame_rate_requested",
    "frame_rate_applied",
    "camera_info",
    "sensor_roi_requested_x",
    "sensor_roi_requested_y",
    "sensor_roi_requested_width",
    "sensor_roi_requested_height",
    "sensor_roi_applied_x",
    "sensor_roi_applied_y",
    "sensor_roi_applied_width",
    "sensor_roi_applied_height",
    "sensor_roi_x",
    "sensor_roi_y",
    "sensor_roi_width",
    "sensor_roi_height",
    "crop_x1",
    "crop_x2",
    "crop_y1",
    "crop_y2",
    "pass_gray_to_dlc",
    "display_enabled",
    "display_scale",
    "display_fps",
    "window_name",
    "dynamic_crop",
    "dynamic_margin",
    "pub_hwm",
    "metadata_interval_s",
}
_STREAMER_METADATA_MODULE = None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_health(base_url: str, timeout_s: float = 5.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            return _request_json("GET", f"{base_url}/health")
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Receiver health endpoint did not become ready.")


def _load_streamer_metadata_module():
    global _STREAMER_METADATA_MODULE
    if _STREAMER_METADATA_MODULE is not None:
        return _STREAMER_METADATA_MODULE

    module_name = "_dlc_eye_streamer_metadata_test"
    fake_dlclive = types.ModuleType("dlclive")
    fake_dlclive.DLCLive = object
    fake_modules = {
        "cv2": types.ModuleType("cv2"),
        "numpy": types.ModuleType("numpy"),
        "PySpin": types.ModuleType("PySpin"),
        "dlclive": fake_dlclive,
    }
    spec = importlib.util.spec_from_file_location(module_name, HERE / "dlc_eye_streamer.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load dlc_eye_streamer.py for metadata testing.")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {**fake_modules, module_name: module}):
        spec.loader.exec_module(module)
    _STREAMER_METADATA_MODULE = module
    return module


def _metadata_payload(*, display_scale: float) -> dict:
    streamer = _load_streamer_metadata_module()
    args = SimpleNamespace(
        address="tcp://10.55.0.1:5555",
        csv=STREAMER_CSV_PATH,
        model_path="/home/eye/EyeTrack/models/yanglab-pupil8",
        model_preset="yanglab-pupil8",
        model_type="base",
        kp_top=2,
        kp_bottom=6,
        kp_left=0,
        kp_right=4,
        kp_center=None,
        pcutoff=0.5,
        pose_coordinate_frame="acquired-frame",
        camera_index=0,
        timeout_ms=1000,
        buffer_count=3,
        pixel_format="Mono8",
        exposure_us=1800.0,
        gain_db=2.0,
        gain_auto="off",
        frame_rate=120.0,
        sensor_roi=[10, 14, 642, 482],
        crop=[100, 500, 50, 350],
        pass_gray_to_dlc=True,
        display=True,
        display_scale=display_scale,
        display_fps=30.0,
        window_name="DLC Eye Tracker",
        dynamic_crop=True,
        dynamic_margin=20,
        pub_hwm=10000,
        metadata_interval_s=1.0,
        camera_info={
            "serial": "TEST-SERIAL-001",
            "model": "Blackfly S BFS-U3-16S2M",
            "sensor_roi_applied": (8, 12, 640, 480),
            "pixel_format": "Mono8",
            "frame_rate": 119.95,
            "exposure_us": 1799.5,
            "gain_auto": "Off",
            "gain_db": 2.0,
            "stream_buffer_count": 3,
        },
    )
    metadata = streamer.make_metadata_message(args, list(POINT_NAMES))
    sidecar = streamer.make_sidecar_metadata(args, list(POINT_NAMES), ["frame_id"])
    metadata = json.loads(json.dumps(metadata))
    sidecar = json.loads(json.dumps(sidecar))
    metadata_static = _expected_stream_metadata(metadata)
    sidecar_static = _expected_stream_metadata(sidecar)
    assert sidecar_static.pop("csv_fieldnames") == ["frame_id"]
    assert sidecar_static == metadata_static, "Periodic and sidecar static metadata drifted."
    missing_fields = REQUIRED_STREAM_METADATA_FIELDS - metadata_static.keys()
    assert not missing_fields, f"Streamer metadata is missing required fields: {sorted(missing_fields)}"
    return metadata


def _expected_stream_metadata(metadata: dict) -> dict:
    excluded = {"message_type", "created_time_unix_s", "created_time_unix_ns"}
    return {field_name: value for field_name, value in metadata.items() if field_name not in excluded}


def _publish_samples_and_metadata_update(base_url: str) -> dict:
    no_points_sample = {
        "message_type": "sample",
        "schema_version": 1,
        "sample_status": "no_points",
        "frame_id": 101,
        "capture_time_unix_s": 1776000000.100000,
        "capture_time_unix_ns": "1776000000100000000",
        "publish_time_unix_s": 1776000000.120000,
        "publish_time_unix_ns": "1776000000120000000",
        "camera_fps": 120.0,
        "inference_fps": 60.0,
        "latency_ms": 11.2,
        "center_x": None,
        "center_y": None,
        "diameter_px": None,
        "diameter_h_px": None,
        "diameter_v_px": None,
        "confidence_mean": None,
        "valid_points": 0,
        "points": {point_name: [None, None, 0.1] for point_name in POINT_NAMES},
        "stream_metadata_version": 999,
        "model_path": "/tmp/sample-must-not-overwrite-metadata",
        "csv_path": "/tmp/sample-must-not-overwrite-paths.csv",
    }
    valid_sample = {
        "message_type": "sample",
        "schema_version": 1,
        "sample_status": "ok",
        "frame_id": 102,
        "capture_time_unix_s": 1776000000.200000,
        "capture_time_unix_ns": "1776000000200000000",
        "publish_time_unix_s": 1776000000.220000,
        "publish_time_unix_ns": "1776000000220000000",
        "camera_fps": 120.0,
        "inference_fps": 60.0,
        "latency_ms": 11.2,
        "center_x": 11.1,
        "center_y": 22.2,
        "diameter_px": 33.3,
        "diameter_h_px": 34.4,
        "diameter_v_px": 32.2,
        "confidence_mean": 0.97,
        "valid_points": 8,
        "points": {
            "Lpupil": [1, 2, 0.91],
            "LDpupil": [2, 3, 0.92],
            "Dpupil": [3, 4, 0.93],
            "DRpupil": [4, 5, 0.94],
            "Rpupil": [5, 6, 0.95],
            "RVpupil": [6, 7, 0.96],
            "Vpupil": [7, 8, 0.97],
            "VLpupil": [8, 9, 0.98],
        },
    }
    valid_sample["points"]["VLpupil"] = [18, 19, 0.88]
    updated_metadata = _metadata_payload(display_scale=1.25)
    _request_json("POST", f"{base_url}/debug/sample", updated_metadata)
    _request_json("POST", f"{base_url}/debug/sample", no_points_sample)
    _request_json("POST", f"{base_url}/debug/sample", valid_sample)
    time.sleep(0.2)
    return updated_metadata


def main() -> int:
    api_port = _free_port()
    pub_address = "disabled"
    base_url = f"http://127.0.0.1:{api_port}"

    process = subprocess.Popen(
        [
            sys.executable,
            str(HERE / "run_eye_receiver_service.py"),
            "--address",
            pub_address,
            "--api-port",
            str(api_port),
        ],
        cwd=HERE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    session_dir = Path(tempfile.mkdtemp(prefix="behavior_eye_receiver_"))
    try:
        health = _wait_for_health(base_url)
        assert health["ok"], "Receiver health endpoint did not return ok=true."
        initial_metadata = _metadata_payload(display_scale=1.0)
        _request_json("POST", f"{base_url}/debug/sample", initial_metadata)
        health = _request_json("GET", f"{base_url}/health")
        assert health["stream_metadata"] == _expected_stream_metadata(initial_metadata), (
            "Initial stream metadata did not survive receiver ingestion."
        )

        session_id = "receiver_test_session"
        _request_json(
            "POST",
            f"{base_url}/session/start",
            {
                "session_id": session_id,
                "session_kind": "mapping",
                "session_label": "receiver-test",
                "output_dir": str(session_dir),
                "session_start_unix_ns": time.time_ns(),
            },
        )
        _request_json(
            "POST",
            f"{base_url}/segment/open",
            {
                "session_id": session_id,
                "segment_id": "segment_0001",
                "segment_kind": "mapping",
                "trial_number": 0,
                "mode": "Map-FlashContourX",
                "scan_image_file": 1,
            },
        )
        updated_metadata = _publish_samples_and_metadata_update(base_url)
        expected_stream_metadata = _expected_stream_metadata(updated_metadata)
        health = _request_json("GET", f"{base_url}/health")
        assert health["metadata_messages_received"] == 2, "Expected initial and refreshed metadata messages."
        assert health["samples_received"] == 2, "Metadata messages must not count as samples."
        assert health["stream_metadata"] == expected_stream_metadata, (
            "Refreshed stream metadata did not survive in the health snapshot."
        )
        assert health["stream_metadata"]["stream_metadata_version"] == 1, (
            "A sample payload overwrote the static metadata version."
        )
        assert health["stream_metadata"]["model_path"] == updated_metadata["model_path"], (
            "A sample payload overwrote the static model path."
        )
        for dynamic_field in ("message_type", "created_time_unix_s", "frame_id", "sample_status", "points"):
            assert dynamic_field not in health["stream_metadata"], (
                f"Dynamic field leaked into stream metadata: {dynamic_field}"
            )
        closed = _request_json(
            "POST",
            f"{base_url}/segment/close",
            {
                "session_id": session_id,
            },
        )
        assert closed["segment_id"] == "segment_0001", "Closed segment id mismatch."
        manifest = _request_json(
            "GET",
            f"{base_url}/manifest?{parse.urlencode({'session_id': session_id})}",
        )
        assert len(manifest["segments"]) == 1, "Expected one finalized manifest segment."
        entry = manifest["segments"][0]
        assert entry["row_count"] == 2, "Receiver should have written both eye samples."
        csv_path = Path(entry["csv_path"])
        receiver_metadata_path = Path(entry["metadata_path"])
        assert csv_path.is_file(), "Receiver CSV chunk was not written."
        assert receiver_metadata_path.is_file(), "Receiver segment metadata was not written."
        assert str(csv_path) != STREAMER_CSV_PATH, "Receiver and streamer CSV paths must remain distinct."
        assert str(receiver_metadata_path) != STREAMER_METADATA_PATH, (
            "Receiver and streamer metadata paths must remain distinct."
        )
        assert csv_path.parent == session_dir, "Receiver CSV should stay in the requested session directory."
        assert receiver_metadata_path.parent == session_dir, (
            "Receiver segment metadata should stay in the requested session directory."
        )
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        expected_fieldnames = [
            "trial",
            "t_us",
            "t_receive_us",
            "frame_id",
            "capture_time_unix_s",
            "capture_time_unix_ns",
            "publish_time_unix_s",
            "publish_time_unix_ns",
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
            "is_valid",
            "sample_status",
            *[
                f"{point_name}_{suffix}"
                for point_name in POINT_NAMES
                for suffix in ("x", "y", "likelihood")
            ],
        ]
        assert reader.fieldnames == expected_fieldnames, "Receiver CSV columns or ordering changed."
        assert len(rows) == 2, "Chunk CSV should contain two rows."
        assert rows[0]["sample_status"] == "no_points", "First row should preserve no_points status."
        assert rows[0]["is_valid"] == "False", "A no_points row must not be marked valid."
        assert rows[1]["sample_status"] == "ok", "Second row should preserve valid status."
        assert rows[1]["is_valid"] == "True", "A valid eye row should be marked valid."
        assert rows[1]["center_x"] == "11.1", "Valid chunk row center_x mismatch."
        assert rows[1]["VLpupil_x"] == "18.0", "Second chunk row exact DLC point mismatch."
        session_metadata_path = session_dir / "receiver_session.json"
        assert session_metadata_path.is_file(), "Receiver session metadata was not written."
        session_metadata = json.loads(session_metadata_path.read_text(encoding="utf-8"))
        assert session_metadata["stream_metadata"] == expected_stream_metadata, (
            "Refreshed stream metadata was not persisted in receiver_session.json."
        )
        assert session_metadata["stream_metadata"]["csv_path"] == STREAMER_CSV_PATH
        assert session_metadata["stream_metadata"]["metadata_path"] == STREAMER_METADATA_PATH
        assert "csv_path" not in session_metadata, "Streamer CSV path leaked into receiver session path fields."
        assert "metadata_path" not in session_metadata, (
            "Streamer metadata path leaked into receiver session path fields."
        )
        segment_metadata = json.loads(receiver_metadata_path.read_text(encoding="utf-8"))
        assert segment_metadata["csv_path"] == str(csv_path), "Segment metadata lost its receiver CSV path."
        assert segment_metadata["metadata_path"] == str(receiver_metadata_path), (
            "Segment metadata lost its receiver metadata path."
        )
        _request_json("POST", f"{base_url}/session/stop", {"session_id": session_id})
        print("BEHAVIOR_EYE_RECEIVER_OK")
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
