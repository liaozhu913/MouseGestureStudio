from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Point = tuple[float, float]


@dataclass
class ActionConfig:
    kind: str = "builtin"
    builtin_name: str = "copy"
    shortcut: str = ""
    text: str = ""
    target: str = ""
    arguments: str = ""
    workflow: str = ""
    delay_ms: int = 0
    show_hint: bool = True

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionConfig":
        return cls(
            kind=payload.get("kind", "builtin"),
            builtin_name=payload.get("builtin_name", "copy"),
            shortcut=payload.get("shortcut", ""),
            text=payload.get("text", ""),
            target=payload.get("target", ""),
            arguments=payload.get("arguments", ""),
            workflow=payload.get("workflow", ""),
            delay_ms=max(0, int(float(payload.get("delay_ms", 0) or 0))),
            show_hint=payload.get("show_hint", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "builtin_name": self.builtin_name,
            "shortcut": self.shortcut,
            "text": self.text,
            "target": self.target,
            "arguments": self.arguments,
            "workflow": self.workflow,
            "delay_ms": self.delay_ms,
            "show_hint": self.show_hint,
        }


@dataclass
class GestureTemplate:
    id: str
    name: str
    points: list[Point]
    action: ActionConfig
    hint: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GestureTemplate":
        raw_points = payload.get("points", [])
        points = [(float(x), float(y)) for x, y in raw_points]
        return cls(
            id=payload["id"],
            name=payload.get("name", payload["id"]),
            points=points,
            action=ActionConfig.from_dict(payload.get("action", {})),
            hint=payload.get("hint", ""),
            enabled=payload.get("enabled", True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "points": [[round(x, 4), round(y, 4)] for x, y in self.points],
            "action": self.action.to_dict(),
            "hint": self.hint,
            "enabled": self.enabled,
        }


@dataclass
class AppSettings:
    schema_version: int = 2
    gestures_enabled: bool = True
    start_on_boot: bool = False
    trigger_button: str = "right"
    minimum_path_length: float = 36.0
    match_threshold: float = 0.62
    gestures: list[GestureTemplate] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppSettings":
        return cls(
            schema_version=int(payload.get("schema_version", 1)),
            gestures_enabled=payload.get("gestures_enabled", True),
            start_on_boot=payload.get("start_on_boot", False),
            trigger_button=payload.get("trigger_button", "right"),
            minimum_path_length=float(payload.get("minimum_path_length", 36.0)),
            match_threshold=float(payload.get("match_threshold", 0.62)),
            gestures=[
                GestureTemplate.from_dict(item)
                for item in payload.get("gestures", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "gestures_enabled": self.gestures_enabled,
            "start_on_boot": self.start_on_boot,
            "trigger_button": self.trigger_button,
            "minimum_path_length": self.minimum_path_length,
            "match_threshold": self.match_threshold,
            "gestures": [gesture.to_dict() for gesture in self.gestures],
        }
