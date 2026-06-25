from __future__ import annotations

from mouse_gesture_studio.config import ConfigManager
from mouse_gesture_studio.gesture.matcher import GestureMatcher


def main() -> int:
    manager = ConfigManager()
    settings = manager.settings
    assert settings.gestures, "默认手势未加载"

    matcher = GestureMatcher()
    sample = settings.gestures[0]
    result = matcher.match(sample.points, settings.gestures)
    assert result.template is not None, "识别器未返回模板"
    assert result.template.id == sample.id, "识别器没有匹配到自身模板"
    assert result.confidence >= settings.match_threshold, "识别置信度低于阈值"

    print("SMOKE_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
