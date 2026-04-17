#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def _read_string_node(node_map: Any, name: str) -> str:
    import PySpin

    node = PySpin.CStringPtr(node_map.GetNode(name))
    if not PySpin.IsAvailable(node) or not PySpin.IsReadable(node):
        return ""
    return str(node.GetValue())


def check_pyspin_camera() -> list[dict[str, str]]:
    """Return FLIR/Point Grey cameras visible to PySpin and print a short summary."""
    import PySpin

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    cameras: list[dict[str, str]] = []

    try:
        print(f"Detected cameras: {cam_list.GetSize()}")
        for idx in range(cam_list.GetSize()):
            cam = cam_list.GetByIndex(idx)
            try:
                tl_node_map = cam.GetTLDeviceNodeMap()
                model = _read_string_node(tl_node_map, "DeviceModelName")
                serial = _read_string_node(tl_node_map, "DeviceSerialNumber")
                cameras.append({
                    "index": str(idx),
                    "model": model,
                    "serial": serial,
                })
                print(f"{idx}: {model} serial={serial}")
            finally:
                del cam
    finally:
        cam_list.Clear()
        system.ReleaseInstance()

    return cameras


if __name__ == "__main__":
    check_pyspin_camera()
