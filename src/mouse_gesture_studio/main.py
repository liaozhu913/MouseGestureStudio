from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_path() -> None:
    current = Path(__file__).resolve()
    src_root = current.parents[1]
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


_ensure_src_path()

from mouse_gesture_studio.app import run


if __name__ == "__main__":
    raise SystemExit(run())
