#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from urllib.parse import urlparse

from behavior_eye_receiver import serve_receiver


def _default_address() -> str:
    return os.environ.get("BB_EYETRACK_ZMQ_ADDRESS", "tcp://127.0.0.1:5555")


def _default_receiver_url() -> str:
    return os.environ.get("BB_EYETRACK_RECEIVER_URL", "http://127.0.0.1:8765")


def _default_api_host_port() -> tuple[str, int]:
    parsed = urlparse(_default_receiver_url())
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8765
    return host, port


def parse_args() -> argparse.Namespace:
    default_api_host, default_api_port = _default_api_host_port()
    parser = argparse.ArgumentParser(
        description="Run the deferred BehaviorBox eye receiver service."
    )
    parser.add_argument(
        "--address",
        default=_default_address(),
        help="ZeroMQ PUB address that the eye streamer is publishing on.",
    )
    parser.add_argument(
        "--api-host",
        default=default_api_host,
        help="Host interface for the localhost control API.",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=default_api_port,
        help="Port for the localhost control API.",
    )
    parser.add_argument(
        "--rcv-hwm",
        type=int,
        default=10000,
        help="ZeroMQ receive high-water mark for the subscriber socket.",
    )
    parser.add_argument(
        "--poll-timeout-ms",
        type=int,
        default=50,
        help="ZeroMQ poll timeout in milliseconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    serve_receiver(
        address=args.address,
        api_host=args.api_host,
        api_port=args.api_port,
        rcv_high_water_mark=args.rcv_hwm,
        poll_timeout_ms=args.poll_timeout_ms,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
