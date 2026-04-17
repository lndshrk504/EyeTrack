#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _matlab_string(value: str | Path) -> str:
    text = str(value)
    return "'" + text.replace("'", "''") + "'"


def _default_python_executable() -> Path:
    env_value = os.environ.get("BB_EYETRACK_PYTHON")
    if env_value:
        return Path(env_value)

    home = Path.home()
    candidates = [
        home / "miniforge3" / "envs" / "dlclivegui" / "bin" / "python",
        home / "mambaforge" / "envs" / "dlclivegui" / "bin" / "python",
        home / "miniconda3" / "envs" / "dlclivegui" / "bin" / "python",
        home / "anaconda3" / "envs" / "dlclivegui" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return Path(sys.executable)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MATLAB-side eye-stream receive test from the command line."
    )
    parser.add_argument(
        "--address",
        default="tcp://127.0.0.1:5555",
        help="ZMQ address published by dlc_eye_streamer.py.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Seconds to receive samples in MATLAB.",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum MATLAB sample count required for the test to pass.",
    )
    parser.add_argument(
        "--output-mat",
        default="",
        help="Where to save the MATLAB receive record. Default: timestamped /tmp file.",
    )
    parser.add_argument(
        "--matlab-bin",
        default=os.environ.get("MATLAB_BIN", "matlab"),
        help="MATLAB executable to call.",
    )
    parser.add_argument(
        "--python-exe",
        default="",
        help="Python executable MATLAB should use for pyzmq. Default: dlclivegui env if found.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    here = Path(__file__).resolve().parent
    output_mat = args.output_mat
    if not output_mat:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_mat = f"/tmp/eye_stream_matlab_receive_{stamp}.mat"

    python_exe = Path(args.python_exe) if args.python_exe else _default_python_executable()

    env = os.environ.copy()
    env["BB_EYETRACK_PYTHON"] = str(python_exe)

    matlab_code = (
        f"addpath({_matlab_string(here)}); "
        "run_eye_stream_receive_test("
        f"'Address', {_matlab_string(args.address)}, "
        f"'DurationSeconds', {args.duration:.6g}, "
        f"'MinSamples', {int(args.min_samples)}, "
        f"'OutputMat', {_matlab_string(output_mat)}, "
        f"'PythonExecutable', {_matlab_string(python_exe)}"
        ");"
    )

    command = [args.matlab_bin, "-batch", matlab_code]
    print("Running MATLAB eye-stream receive test", flush=True)
    print(f"Address: {args.address}", flush=True)
    print(f"Duration: {args.duration:.1f} seconds", flush=True)
    print(f"Output MAT: {output_mat}", flush=True)
    print(f"MATLAB executable: {args.matlab_bin}", flush=True)
    print(f"Python for MATLAB bridge: {python_exe}", flush=True)
    return subprocess.run(command, cwd=here, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
