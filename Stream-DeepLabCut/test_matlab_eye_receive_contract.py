#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import request


HERE = Path(__file__).resolve().parent
BEHAVIORBOX_ROOT = HERE.parent.parent


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


def _wait_for_health(base_url: str, timeout_s: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            return _request_json("GET", f"{base_url}/health")
        except Exception:
            time.sleep(0.05)
    raise RuntimeError(f"Receiver health endpoint did not become ready: {base_url}")


def _wait_for_segment(base_url: str, matlab_process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if matlab_process.poll() is not None:
            output, _ = matlab_process.communicate()
            raise RuntimeError(f"MATLAB exited before opening a segment:\n{output}")
        health = _request_json("GET", f"{base_url}/health")
        if health.get("active_segment_id"):
            return
        time.sleep(0.05)
    raise RuntimeError("MATLAB did not open a receiver segment within 45 seconds.")


def _metadata_payload() -> dict:
    return {
        "message_type": "metadata",
        "schema_version": 1,
        "stream_metadata_version": 1,
        "source": "dlc_eye_streamer",
        "address": "tcp://127.0.0.1:5555",
        "csv_path": "/tmp/EyeTrack/stream.csv",
        "metadata_path": "/tmp/EyeTrack/stream_metadata.json",
        "model_path": "/tmp/models/exported-model",
        "model_preset": "yanglab-pupil8",
        "model_type": "base",
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
        "point_count": 8,
        "pcutoff": 0.5,
        "pose_coordinate_frame": "acquired-frame",
        "camera_index": 0,
        "camera_serial": "TEST-SERIAL-001",
        "camera_model": "Blackfly S BFS-U3-16S2M",
        "timeout_ms": 1000,
        "buffer_count": 3,
        "buffer_count_requested": 3,
        "buffer_count_applied": 3,
        "pixel_format": "Mono8",
        "pixel_format_requested": "Mono8",
        "pixel_format_applied": "Mono8",
        "exposure_us_requested": 1800.0,
        "exposure_us_applied": 1799.5,
        "gain_db_requested": 2.0,
        "gain_db_applied": 2.0,
        "gain_auto_requested": "off",
        "gain_auto_applied": "Off",
        "frame_rate_requested": 120.0,
        "frame_rate_applied": 119.95,
        "camera_info": {
            "serial": "TEST-SERIAL-001",
            "model": "Blackfly S BFS-U3-16S2M",
            "sensor_roi_applied": [8, 12, 640, 480],
        },
        "sensor_roi_requested_x": 10,
        "sensor_roi_requested_y": 14,
        "sensor_roi_requested_width": 642,
        "sensor_roi_requested_height": 482,
        "sensor_roi_applied_x": 8,
        "sensor_roi_applied_y": 12,
        "sensor_roi_applied_width": 640,
        "sensor_roi_applied_height": 480,
        "sensor_roi_x": 8,
        "sensor_roi_y": 12,
        "sensor_roi_width": 640,
        "sensor_roi_height": 480,
        "crop_x1": 100,
        "crop_x2": 500,
        "crop_y1": 50,
        "crop_y2": 350,
        "pass_gray_to_dlc": True,
        "display_enabled": True,
        "display_scale": 1.0,
        "display_fps": 30.0,
        "window_name": "DLC Eye Tracker",
        "dynamic_crop": True,
        "dynamic_margin": 20,
        "pub_hwm": 10000,
        "metadata_interval_s": 1.0,
    }


def _sample_payload(*, valid: bool) -> dict:
    points = {}
    if valid:
        names = _metadata_payload()["point_names"]
        points = {
            name: [float(index + 1), float(index + 2), 0.95]
            for index, name in enumerate(names)
        }
    return {
        "message_type": "sample",
        "schema_version": 1,
        "sample_status": "ok" if valid else "no_points",
        "frame_id": 101,
        "capture_time_unix_s": 1776000000.1,
        "capture_time_unix_ns": "1776000000100000000",
        "publish_time_unix_s": 1776000000.12,
        "publish_time_unix_ns": "1776000000120000000",
        "camera_fps": 120.0,
        "inference_fps": 60.0,
        "latency_ms": 11.2,
        "center_x": 11.1 if valid else None,
        "center_y": 22.2 if valid else None,
        "diameter_px": 33.3 if valid else None,
        "diameter_h_px": 34.4 if valid else None,
        "diameter_v_px": 32.2 if valid else None,
        "confidence_mean": 0.95 if valid else None,
        "valid_points": 8 if valid else 0,
        "points": points,
    }


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _run_scenario(
    *,
    name: str,
    matlab_bin: str,
    valid_sample: bool,
    transport_only: bool,
    expect_success: bool,
    verify_saved_mat: bool = False,
) -> None:
    api_port = _free_port()
    zmq_port = _free_port()
    address = f"tcp://127.0.0.1:{zmq_port}"
    base_url = f"http://127.0.0.1:{api_port}"
    temp_root = Path(tempfile.mkdtemp(prefix=f"matlab_eye_{name}_"))
    output_mat = temp_root / "receive.mat"
    receiver = subprocess.Popen(
        [
            sys.executable,
            str(HERE / "run_eye_receiver_service.py"),
            "--address",
            address,
            "--api-port",
            str(api_port),
        ],
        cwd=HERE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    matlab_process: subprocess.Popen[str] | None = None
    try:
        _wait_for_health(base_url)
        command = [
            sys.executable,
            str(HERE / "run_matlab_eye_receive_test.py"),
            "--address",
            address,
            "--receiver-url",
            base_url,
            "--behaviorbox-root",
            str(BEHAVIORBOX_ROOT),
            "--duration",
            "1.5",
            "--min-samples",
            "1",
            "--min-valid-samples",
            "1",
            "--output-mat",
            str(output_mat),
            "--matlab-bin",
            matlab_bin,
        ]
        if transport_only:
            command.append("--transport-only")
        env = os.environ.copy()
        env["TMPDIR"] = str(temp_root)
        matlab_process = subprocess.Popen(
            command,
            cwd=HERE,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _wait_for_segment(base_url, matlab_process)
        _request_json("POST", f"{base_url}/debug/sample", _metadata_payload())
        _request_json(
            "POST",
            f"{base_url}/debug/sample",
            _sample_payload(valid=valid_sample),
        )
        output, _ = matlab_process.communicate(timeout=90)
        if (matlab_process.returncode == 0) != expect_success:
            raise AssertionError(
                f"Scenario {name} returned {matlab_process.returncode}:\n{output}"
            )
        receive_marker = "MATLAB_EYE_STREAM_RECEIVE_OK"
        transport_marker = "MATLAB_EYE_STREAM_TRANSPORT_OK"
        if transport_only and expect_success:
            assert transport_marker in output, output
            assert receive_marker not in output, output
        elif expect_success:
            assert receive_marker in output, output
            assert transport_marker not in output, output
        else:
            assert receive_marker not in output, output
            assert transport_marker not in output, output

        session_metadata_path = (
            temp_root / "behaviorbox_receive_test_eye_raw" / "receiver_session.json"
        )
        assert session_metadata_path.is_file(), (
            f"Scenario {name} did not write receiver session metadata."
        )
        session_metadata = json.loads(session_metadata_path.read_text(encoding="utf-8"))
        assert session_metadata["source_address"] == address
        expected_stream_metadata = {
            key: value for key, value in _metadata_payload().items() if key != "message_type"
        }
        assert session_metadata["stream_metadata"] == expected_stream_metadata
        if verify_saved_mat:
            _verify_valid_mat(matlab_bin, output_mat, address)
    finally:
        if matlab_process is not None and matlab_process.poll() is None:
            _terminate(matlab_process)
        _terminate(receiver)
        shutil.rmtree(temp_root, ignore_errors=True)


def _matlab_quote(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _verify_valid_mat(matlab_bin: str, output_mat: Path, address: str) -> None:
    code = (
        f"s=load({_matlab_quote(output_mat)},'record','meta'); "
        "assert(height(s.record)>=1,'saved record is empty'); "
        "assert(any(s.record.is_valid),'saved record has no valid row'); "
        f"assert(s.meta.ConfiguredAddress=={_matlab_quote(address)},'configured address mismatch'); "
        f"assert(s.meta.ReceiverAddress=={_matlab_quote(address)},'receiver address mismatch'); "
        f"assert(s.meta.Address=={_matlab_quote(address)},'effective address mismatch'); "
        "assert(~s.meta.AddressMismatch,'unexpected address mismatch'); "
        "assert(s.meta.SourceMode=='localhost','source mode mismatch'); "
        "assert(s.meta.StreamMetadata.stream_metadata_version==1,'metadata version mismatch'); "
        "assert(string(s.meta.StreamMetadata.model_path)=='/tmp/models/exported-model','model path mismatch'); "
        "assert(s.meta.StreamMetadata.sensor_roi_requested_width==642,'requested ROI missing'); "
        "assert(s.meta.StreamMetadata.sensor_roi_applied_width==640,'applied ROI missing'); "
        "assert(s.meta.StreamMetadata.exposure_us_applied==1799.5,'applied exposure missing'); "
        "assert(s.meta.StreamMetadata.dynamic_crop,'dynamic crop metadata missing'); "
        "assert(isfield(s.meta.StreamMetadata,'csv_path'),'streamer csv_path missing'); "
        "assert(string(s.meta.StreamMetadata.csv_path)=='/tmp/EyeTrack/stream.csv','streamer csv_path mismatch'); "
        "disp('MATLAB_EYE_STREAM_SAVED_CONTRACT_OK');"
    )
    completed = subprocess.run(
        [matlab_bin, "-batch", code],
        cwd=HERE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=90,
    )
    if completed.returncode != 0:
        raise AssertionError(f"Saved MAT contract validation failed:\n{completed.stdout}")
    assert "MATLAB_EYE_STREAM_SAVED_CONTRACT_OK" in completed.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run camera-free MATLAB eye receiver contract scenarios."
    )
    parser.add_argument(
        "--matlab-bin",
        default=os.environ.get("MATLAB_BIN", "matlab"),
        help="MATLAB executable to call.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _run_scenario(
        name="no_points_full",
        matlab_bin=args.matlab_bin,
        valid_sample=False,
        transport_only=False,
        expect_success=False,
    )
    _run_scenario(
        name="no_points_transport",
        matlab_bin=args.matlab_bin,
        valid_sample=False,
        transport_only=True,
        expect_success=True,
    )
    _run_scenario(
        name="valid_full",
        matlab_bin=args.matlab_bin,
        valid_sample=True,
        transport_only=False,
        expect_success=True,
        verify_saved_mat=True,
    )
    print("MATLAB_EYE_STREAM_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
