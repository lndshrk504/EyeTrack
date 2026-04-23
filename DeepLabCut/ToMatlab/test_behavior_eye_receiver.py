#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import parse, request

HERE = Path(__file__).resolve().parent


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


def _publish_payloads(base_url: str) -> None:
    metadata = {
        "message_type": "metadata",
        "schema_version": 1,
        "source": "dlc_eye_streamer",
        "model_preset": "yanglab-pupil8",
        "model_type": "base",
        "point_names": ["Lpupil", "LDpupil", "Dpupil", "DRpupil", "Rpupil", "RVpupil", "Vpupil", "VLpupil"],
        "point_count": 8,
    }
    sample = {
        "message_type": "sample",
        "schema_version": 1,
        "sample_status": "ok",
        "frame_id": 101,
        "capture_time_unix_s": 1776000000.100000,
        "capture_time_unix_ns": "1776000000100000000",
        "publish_time_unix_s": 1776000000.120000,
        "publish_time_unix_ns": "1776000000120000000",
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
    sample2 = dict(sample)
    sample2["frame_id"] = 102
    sample2["center_x"] = 44.4
    sample2["center_y"] = 55.5
    sample2["points"] = dict(sample["points"])
    sample2["points"]["VLpupil"] = [18, 19, 0.88]
    _request_json("POST", f"{base_url}/debug/sample", metadata)
    _request_json("POST", f"{base_url}/debug/sample", sample)
    _request_json("POST", f"{base_url}/debug/sample", sample2)
    time.sleep(0.2)


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
        _publish_payloads(base_url)
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
        assert csv_path.is_file(), "Receiver CSV chunk was not written."
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 2, "Chunk CSV should contain two rows."
        assert rows[0]["center_x"] == "11.1", "First chunk row center_x mismatch."
        assert rows[1]["VLpupil_x"] == "18.0", "Second chunk row exact DLC point mismatch."
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
