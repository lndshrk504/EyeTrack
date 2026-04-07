from __future__ import annotations

import math
from typing import Any

import zmq

_CONTEXT = None


def _ctx() -> zmq.Context:
    global _CONTEXT
    if _CONTEXT is None:
        _CONTEXT = zmq.Context.instance()
    return _CONTEXT


def _float_or_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    try:
        out = float(value)
    except Exception:
        return float("nan")
    if math.isnan(out) or math.isinf(out):
        return float("nan")
    return out


def open_subscriber(address: str = "tcp://127.0.0.1:5555", rcvhwm: int = 1):
    sock = _ctx().socket(zmq.SUB)
    sock.linger = 0
    sock.setsockopt(zmq.RCVHWM, int(rcvhwm))
    sock.subscribe("")
    sock.connect(address)
    return sock


def close_socket(sock) -> None:
    try:
        sock.close(0)
    except Exception:
        pass


def recv_latest_dict(sock, timeout_ms: int = 0):
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    events = dict(poller.poll(int(timeout_ms)))
    if sock not in events:
        return {}

    msg = sock.recv_json()
    while True:
        try:
            msg = sock.recv_json(flags=zmq.NOBLOCK)
        except zmq.Again:
            break
    return msg


def recv_latest(sock, timeout_ms: int = 0):
    msg = recv_latest_dict(sock, timeout_ms=timeout_ms)
    if not msg:
        return (-1, float("nan"), float("nan"), float("nan"), float("nan"), float("nan"), float("nan"), float("nan"))

    return (
        int(msg.get("frame_id", -1)),
        _float_or_nan(msg.get("capture_time_unix_s")),
        _float_or_nan(msg.get("publish_time_unix_s")),
        _float_or_nan(msg.get("center_x")),
        _float_or_nan(msg.get("center_y")),
        _float_or_nan(msg.get("diameter_px")),
        _float_or_nan(msg.get("confidence_mean")),
        _float_or_nan(msg.get("latency_ms")),
    )
