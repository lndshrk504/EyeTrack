#!/usr/bin/env python3
from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> int:
    replacement = Path(__file__).with_name("smoke_dlc_flir_inference.py")
    print(
        "Spin2DLC.py is kept as a compatibility wrapper. "
        "Use smoke_dlc_flir_inference.py for the maintained timing smoke test.",
        file=sys.stderr,
    )
    runpy.run_path(str(replacement), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
