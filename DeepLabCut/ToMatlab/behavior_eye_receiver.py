#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import zmq


DEFAULT_POINT_NAMES = [
    "Lpupil",
    "LDpupil",
    "Dpupil",
    "DRpupil",
    "Rpupil",
    "RVpupil",
    "Vpupil",
    "VLpupil",
]


def _safe_float(value: Any) -> float:
    if value is None or value == "":
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _safe_int_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:
            return ""
        return f"{value:.0f}"
    return str(value)


def _safe_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _point_column_names(point_names: list[str]) -> list[str]:
    columns: list[str] = []
    for point_name in point_names:
        columns.extend([f"{point_name}_x", f"{point_name}_y", f"{point_name}_likelihood"])
    return columns


def _record_fieldnames(point_names: list[str]) -> list[str]:
    return [
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
        *_point_column_names(point_names),
    ]


def _points_from_payload(payload: dict[str, Any], point_names: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    points = payload.get("points") or {}
    for point_name in point_names:
        point = points.get(point_name) or [float("nan"), float("nan"), float("nan")]
        if len(point) < 3:
            point = list(point) + [float("nan")] * (3 - len(point))
        out[f"{point_name}_x"] = _safe_float(point[0])
        out[f"{point_name}_y"] = _safe_float(point[1])
        out[f"{point_name}_likelihood"] = _safe_float(point[2])
    return out


@dataclass
class SegmentWriter:
    session_id: str
    segment_id: str
    segment_kind: str
    trial_number: float
    mode: str
    scan_image_file: float
    output_dir: Path
    point_names: list[str]
    session_start_unix_ns: int
    opened_unix_ns: int
    writer: csv.DictWriter = field(init=False)
    file_handle: Any = field(init=False)
    csv_path: Path = field(init=False)
    metadata_path: Path = field(init=False)
    fieldnames: list[str] = field(init=False)
    row_count: int = 0
    receive_start_unix_ns: Optional[int] = None
    receive_end_unix_ns: Optional[int] = None

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{self.segment_id}"
        self.csv_path = self.output_dir / f"{stem}.csv"
        self.metadata_path = self.output_dir / f"{stem}_metadata.json"
        self.fieldnames = _record_fieldnames(self.point_names)
        self.file_handle = self.csv_path.open("w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file_handle, fieldnames=self.fieldnames)
        self.writer.writeheader()
        self.file_handle.flush()

    def write_sample(self, payload: dict[str, Any], receive_unix_ns: int) -> None:
        if self.receive_start_unix_ns is None:
            self.receive_start_unix_ns = receive_unix_ns
        self.receive_end_unix_ns = receive_unix_ns
        receive_rel_us = max(0, round((receive_unix_ns - self.session_start_unix_ns) / 1000.0))
        sample_status = _safe_string(payload.get("sample_status"))
        if not sample_status:
            sample_status = "ok"
        valid_points = _safe_float(payload.get("valid_points"))
        center_x = _safe_float(payload.get("center_x"))
        center_y = _safe_float(payload.get("center_y"))
        is_valid = (
            sample_status in {"ok", "partial_points"}
            and valid_points > 0
            and center_x == center_x
            and center_y == center_y
        )
        row = {
            "trial": self.trial_number,
            "t_us": receive_rel_us,
            "t_receive_us": receive_rel_us,
            "frame_id": _safe_float(payload.get("frame_id")),
            "capture_time_unix_s": _safe_float(payload.get("capture_time_unix_s")),
            "capture_time_unix_ns": _safe_int_text(payload.get("capture_time_unix_ns")),
            "publish_time_unix_s": _safe_float(payload.get("publish_time_unix_s")),
            "publish_time_unix_ns": _safe_int_text(payload.get("publish_time_unix_ns")),
            "center_x": center_x,
            "center_y": center_y,
            "diameter_px": _safe_float(payload.get("diameter_px")),
            "diameter_h_px": _safe_float(payload.get("diameter_h_px")),
            "diameter_v_px": _safe_float(payload.get("diameter_v_px")),
            "confidence_mean": _safe_float(payload.get("confidence_mean")),
            "valid_points": valid_points,
            "camera_fps": _safe_float(payload.get("camera_fps")),
            "inference_fps": _safe_float(payload.get("inference_fps")),
            "latency_ms": _safe_float(payload.get("latency_ms")),
            "is_valid": is_valid,
            "sample_status": sample_status,
        }
        row.update(_points_from_payload(payload, self.point_names))
        self.writer.writerow(row)
        self.file_handle.flush()
        self.row_count += 1

    def close(self, *, partial: bool) -> dict[str, Any]:
        if not self.file_handle.closed:
            self.file_handle.close()
        t_start_us = float("nan")
        t_end_us = float("nan")
        if self.receive_start_unix_ns is not None:
            t_start_us = max(0, round((self.receive_start_unix_ns - self.session_start_unix_ns) / 1000.0))
        if self.receive_end_unix_ns is not None:
            t_end_us = max(0, round((self.receive_end_unix_ns - self.session_start_unix_ns) / 1000.0))
        metadata = {
            "session_id": self.session_id,
            "segment_id": self.segment_id,
            "segment_kind": self.segment_kind,
            "trial_number": self.trial_number,
            "mode": self.mode,
            "scan_image_file": self.scan_image_file,
            "session_start_unix_ns": self.session_start_unix_ns,
            "opened_unix_ns": self.opened_unix_ns,
            "receive_start_unix_ns": self.receive_start_unix_ns,
            "receive_end_unix_ns": self.receive_end_unix_ns,
            "t_receive_start_us": t_start_us,
            "t_receive_end_us": t_end_us,
            "row_count": self.row_count,
            "partial": bool(partial),
            "closed": True,
            "csv_path": str(self.csv_path),
            "metadata_path": str(self.metadata_path),
            "point_names": list(self.point_names),
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata


@dataclass
class SessionState:
    session_id: str
    session_kind: str
    session_label: str
    output_dir: Path
    session_start_unix_ns: int
    source_address: str
    model_name: str
    point_names: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    manifest: list[dict[str, Any]] = field(default_factory=list)
    active_segment: Optional[SegmentWriter] = None

    @property
    def manifest_path(self) -> Path:
        return self.output_dir / "receiver_manifest.json"

    @property
    def session_metadata_path(self) -> Path:
        return self.output_dir / "receiver_session.json"

    def write_metadata(self) -> None:
        payload = {
            "session_id": self.session_id,
            "session_kind": self.session_kind,
            "session_label": self.session_label,
            "output_dir": str(self.output_dir),
            "session_start_unix_ns": self.session_start_unix_ns,
            "source_address": self.source_address,
            "model_name": self.model_name,
            "point_names": list(self.point_names),
            "metadata": self.metadata,
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session_metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def write_manifest(self) -> None:
        payload = {
            "session_id": self.session_id,
            "segments": self.manifest,
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ReceiverState:
    def __init__(
        self,
        *,
        address: str,
        api_host: str,
        api_port: int,
        rcv_high_water_mark: int,
        poll_timeout_ms: int,
    ) -> None:
        self.address = address
        self.api_host = api_host
        self.api_port = api_port
        self.rcv_high_water_mark = int(rcv_high_water_mark)
        self.poll_timeout_ms = int(poll_timeout_ms)
        self.model_name = "DLC_PupilTracking_YangLab_resnet_50_iteration-0_shuffle-1"
        self.point_names = list(DEFAULT_POINT_NAMES)
        self.last_error_message = ""
        self.last_sample_receive_unix_ns: Optional[int] = None
        self.messages_received = 0
        self.samples_received = 0
        self.metadata_messages_received = 0
        self.frame_gap_count = 0
        self.missing_frame_count = 0
        self.last_frame_id: Optional[int] = None
        self.stream_metadata: dict[str, Any] = {}
        self.current_session: Optional[SessionState] = None
        self.session_history: dict[str, SessionState] = {}
        self._zmq_enabled = str(self.address).lower() not in {"", "disabled", "disabled://", "none"}
        self._context = None
        self._socket = None
        if self._zmq_enabled:
            self._context = zmq.Context.instance()
            self._socket = self._context.socket(zmq.SUB)
            self._socket.setsockopt(zmq.SUBSCRIBE, b"")
            self._socket.setsockopt(zmq.RCVHWM, self.rcv_high_water_mark)
            self._socket.connect(self.address)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._recv_loop, name="BehaviorEyeReceiver", daemon=True)

    def start(self) -> None:
        if self._zmq_enabled:
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._zmq_enabled:
            self._thread.join(timeout=2.0)
        try:
            if self._socket is not None:
                self._socket.close(0)
        except Exception:
            pass

    def _recv_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self._socket.poll(self.poll_timeout_ms) == 0:
                    continue
                payload = self._socket.recv_json(flags=0)
                receive_unix_ns = time.time_ns()
                self.handle_payload(payload, receive_unix_ns)
            except Exception as err:  # pragma: no cover - exercised in integration
                with self._lock:
                    self.last_error_message = str(err)
                time.sleep(0.05)

    def handle_payload(self, payload: dict[str, Any], receive_unix_ns: int) -> None:
        message_type = _safe_string(payload.get("message_type") or "sample")
        with self._lock:
            self.messages_received += 1
            self.last_sample_receive_unix_ns = receive_unix_ns
            self._update_metadata(payload)
            if message_type == "metadata":
                self.metadata_messages_received += 1
                return
            self.samples_received += 1
            self._update_frame_gap(payload.get("frame_id"))
            session = self.current_session
            if session is None or session.active_segment is None:
                return
            session.active_segment.write_sample(payload, receive_unix_ns)

    def _update_metadata(self, payload: dict[str, Any]) -> None:
        point_names = payload.get("point_names")
        if isinstance(point_names, list) and point_names:
            self.point_names = [_safe_string(value) for value in point_names]
        model_name = payload.get("model_preset") or payload.get("model_name")
        if model_name:
            self.model_name = _safe_string(model_name)
        for field_name in (
            "schema_version",
            "source",
            "address",
            "model_preset",
            "model_type",
            "point_names",
            "point_count",
            "camera_model",
            "camera_serial",
            "pose_coordinate_frame",
        ):
            if field_name in payload:
                self.stream_metadata[field_name] = payload[field_name]

    def _update_frame_gap(self, frame_id_value: Any) -> None:
        try:
            frame_id = int(frame_id_value)
        except (TypeError, ValueError):
            return
        if self.last_frame_id is not None and frame_id > self.last_frame_id + 1:
            self.frame_gap_count += 1
            self.missing_frame_count += frame_id - self.last_frame_id - 1
        self.last_frame_id = frame_id

    def health_payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "address": self.address,
                "api_host": self.api_host,
                "api_port": self.api_port,
                "model_name": self.model_name,
                "point_names": list(self.point_names),
                "messages_received": self.messages_received,
                "samples_received": self.samples_received,
                "metadata_messages_received": self.metadata_messages_received,
                "frame_gap_count": self.frame_gap_count,
                "missing_frame_count": self.missing_frame_count,
                "last_frame_id": self.last_frame_id,
                "last_error_message": self.last_error_message,
                "active_session_id": None if self.current_session is None else self.current_session.session_id,
                "zmq_enabled": self._zmq_enabled,
                "active_segment_id": None
                if self.current_session is None or self.current_session.active_segment is None
                else self.current_session.active_segment.segment_id,
                "stream_metadata": dict(self.stream_metadata),
            }

    def debug_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.handle_payload(payload, time.time_ns())
        return {
            "ok": True,
            "messages_received": self.messages_received,
            "samples_received": self.samples_received,
        }

    def start_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session_id = _safe_string(payload.get("session_id"))
            if not session_id:
                raise ValueError("session_id is required")
            output_dir = Path(_safe_string(payload.get("output_dir"))).expanduser()
            if not output_dir:
                raise ValueError("output_dir is required")
            session = SessionState(
                session_id=session_id,
                session_kind=_safe_string(payload.get("session_kind") or "session"),
                session_label=_safe_string(payload.get("session_label") or session_id),
                output_dir=output_dir,
                session_start_unix_ns=int(payload.get("session_start_unix_ns") or time.time_ns()),
                source_address=self.address,
                model_name=_safe_string(payload.get("model_name") or self.model_name),
                point_names=list(payload.get("point_names") or self.point_names or DEFAULT_POINT_NAMES),
                metadata=dict(payload.get("metadata") or {}),
            )
            if self.current_session is not None and self.current_session.session_id != session_id:
                self._finalize_current_session_locked(partial=True)
                self.current_session = None
            self.current_session = session
            self.session_history[session_id] = session
            session.write_metadata()
            session.write_manifest()
            return {
                "session_id": session.session_id,
                "output_dir": str(session.output_dir),
                "point_names": list(session.point_names),
                "model_name": session.model_name,
            }

    def open_segment(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self._require_current_session(payload)
            if session.active_segment is not None:
                self._close_active_segment_locked(session, partial=True)
            segment_id = _safe_string(payload.get("segment_id"))
            if not segment_id:
                segment_id = f"{session.session_id}_segment_{len(session.manifest) + 1:04d}"
            segment = SegmentWriter(
                session_id=session.session_id,
                segment_id=segment_id,
                segment_kind=_safe_string(payload.get("segment_kind") or "segment"),
                trial_number=_safe_float(payload.get("trial_number")),
                mode=_safe_string(payload.get("mode")),
                scan_image_file=_safe_float(payload.get("scan_image_file")),
                output_dir=session.output_dir,
                point_names=list(session.point_names),
                session_start_unix_ns=session.session_start_unix_ns,
                opened_unix_ns=time.time_ns(),
            )
            session.active_segment = segment
            session.write_manifest()
            return {
                "session_id": session.session_id,
                "segment_id": segment.segment_id,
                "segment_kind": segment.segment_kind,
            }

    def close_segment(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self._require_current_session(payload)
            return self._close_active_segment_locked(session, partial=bool(payload.get("partial", False)))

    def finalize_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self._require_current_session(payload)
            self._finalize_current_session_locked(partial=bool(payload.get("partial", False)))
            return {
                "session_id": session.session_id,
                "segments": list(session.manifest),
            }

    def stop_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            session = self._require_current_session(payload)
            self._finalize_current_session_locked(partial=bool(payload.get("partial", False)))
            self.current_session = None
            return {
                "session_id": session.session_id,
                "segments": list(session.manifest),
            }

    def manifest_payload(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            session = self.session_history.get(session_id)
            if session is None:
                raise ValueError(f"Unknown session_id: {session_id}")
            return {
                "session_id": session.session_id,
                "segments": list(session.manifest),
            }

    def _require_current_session(self, payload: dict[str, Any]) -> SessionState:
        session_id = _safe_string(payload.get("session_id"))
        if self.current_session is None:
            raise ValueError("No active session")
        if session_id and session_id != self.current_session.session_id:
            raise ValueError(f"Active session is {self.current_session.session_id}, not {session_id}")
        return self.current_session

    def _close_active_segment_locked(self, session: SessionState, *, partial: bool) -> dict[str, Any]:
        if session.active_segment is None:
            return {
                "session_id": session.session_id,
                "segment_id": "",
                "closed": False,
            }
        manifest_entry = session.active_segment.close(partial=partial)
        session.manifest.append(manifest_entry)
        session.active_segment = None
        session.write_manifest()
        return manifest_entry

    def _finalize_current_session_locked(self, *, partial: bool) -> None:
        if self.current_session is None:
            return
        if self.current_session.active_segment is not None:
            self._close_active_segment_locked(self.current_session, partial=partial)
        self.current_session.write_metadata()
        self.current_session.write_manifest()


class ReceiverRequestHandler(BaseHTTPRequestHandler):
    server: "ReceiverHttpServer"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/health":
                self._send_json(self.server.state.health_payload())
            elif parsed.path == "/status":
                self._send_json(self.server.state.health_payload())
            elif parsed.path == "/manifest":
                query = parse_qs(parsed.query)
                session_id = _safe_string((query.get("session_id") or [""])[0])
                self._send_json(self.server.state.manifest_payload(session_id))
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
        except Exception as err:
            self._send_error(err)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self._read_json_body()
        try:
            if parsed.path == "/session/start":
                payload = self.server.state.start_session(body)
            elif parsed.path == "/session/finalize":
                payload = self.server.state.finalize_session(body)
            elif parsed.path == "/session/stop":
                payload = self.server.state.stop_session(body)
            elif parsed.path == "/segment/open":
                payload = self.server.state.open_segment(body)
            elif parsed.path == "/segment/close":
                payload = self.server.state.close_segment(body)
            elif parsed.path == "/debug/sample":
                payload = self.server.state.debug_ingest(body)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
                return
            self._send_json(payload)
        except Exception as err:
            self._send_error(err)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_error(self, err: Exception) -> None:
        payload = {
            "ok": False,
            "error": str(err),
        }
        self._send_json(payload, status=HTTPStatus.BAD_REQUEST)


class ReceiverHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], state: ReceiverState) -> None:
        super().__init__(server_address, ReceiverRequestHandler)
        self.state = state


def serve_receiver(
    *,
    address: str = "tcp://127.0.0.1:5555",
    api_host: str = "127.0.0.1",
    api_port: int = 8765,
    rcv_high_water_mark: int = 10000,
    poll_timeout_ms: int = 50,
) -> None:
    state = ReceiverState(
        address=address,
        api_host=api_host,
        api_port=api_port,
        rcv_high_water_mark=rcv_high_water_mark,
        poll_timeout_ms=poll_timeout_ms,
    )
    state.start()
    server = ReceiverHttpServer((api_host, api_port), state)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        state.stop()
