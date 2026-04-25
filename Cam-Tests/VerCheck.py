#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import os
import platform
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PackageCheck:
    import_name: str
    label: str
    required_for_runtime: bool = False
    distribution_name: str | None = None


PACKAGE_CHECKS = [
    PackageCheck("numpy", "NumPy", True),
    PackageCheck("cv2", "OpenCV", True, "opencv-python"),
    PackageCheck("zmq", "pyzmq", True, "pyzmq"),
    PackageCheck("PySpin", "PySpin", True),
    PackageCheck("dlclive", "DLCLive", True),
    PackageCheck("tensorflow", "TensorFlow", True),
    PackageCheck("deeplabcut", "DeepLabCut", False),
    PackageCheck("dlclivegui", "DLCLiveGUI", False),
]


def package_version(module, check: PackageCheck) -> str:
    for attr in ("__version__", "VERSION"):
        value = getattr(module, attr, None)
        if value:
            return str(value)
    distribution = check.distribution_name or check.import_name
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def check_packages() -> list[str]:
    missing_required: list[str] = []
    print("Python executable:", sys.executable)
    print("Python version:", sys.version.replace("\n", " "))
    print("Platform:", platform.platform())
    print("CONDA_DEFAULT_ENV:", os.environ.get("CONDA_DEFAULT_ENV", ""))
    print("CONDA_PREFIX:", os.environ.get("CONDA_PREFIX", ""))
    print("CUDA_VISIBLE_DEVICES:", os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    print()

    for check in PACKAGE_CHECKS:
        try:
            module = importlib.import_module(check.import_name)
            version = package_version(module, check)
            print(f"{check.label:16s} OK      {version}")
        except Exception as exc:
            status = "MISSING" if isinstance(exc, ModuleNotFoundError) else "ERROR"
            print(f"{check.label:16s} {status:7s} {exc}")
            if check.required_for_runtime:
                missing_required.append(check.label)

    print()
    report_tensorflow()
    return missing_required


def report_tensorflow() -> None:
    try:
        import tensorflow as tf
    except Exception:
        return

    try:
        from tensorflow.python.platform import build_info
        info = build_info.build_info
    except Exception:
        info = {}

    print("TensorFlow build CUDA:", info.get("cuda_version", "unknown"))
    print("TensorFlow build cuDNN:", info.get("cudnn_version", "unknown"))
    print("TensorFlow build TensorRT:", info.get("tensorrt_version", "unknown"))
    try:
        gpus = tf.config.list_physical_devices("GPU")
        print("TensorFlow visible GPUs:", [gpu.name for gpu in gpus])
    except Exception as exc:
        print("TensorFlow visible GPUs: ERROR", exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report Python package versions for DLC eye-tracking environments."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if any runtime-required package is missing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    missing_required = check_packages()
    if args.strict and missing_required:
        print()
        print("Missing runtime-required packages:", ", ".join(missing_required))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
