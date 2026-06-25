from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .constants import build_default_settings
from .models import AppSettings


APP_DIR_NAME = "MouseGestureStudio"
CONFIG_FILE_NAME = "settings.json"
CURRENT_SCHEMA_VERSION = 3


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if base:
        root = Path(base) / APP_DIR_NAME
    else:
        root = Path.home() / f".{APP_DIR_NAME}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def config_path() -> Path:
    return data_dir() / CONFIG_FILE_NAME


def resource_path(*parts: str) -> Path:
    root = runtime_root()
    direct = root.joinpath(*parts)
    if direct.exists():
        return direct
    bundled = root / "_internal"
    return bundled.joinpath(*parts)


class ConfigManager:
    def __init__(self) -> None:
        self._path = config_path()
        self._settings = self.load()

    def load(self) -> AppSettings:
        if not self._path.exists():
            migrated = self._load_latest_legacy_settings()
            settings = migrated or build_default_settings()
            settings.schema_version = CURRENT_SCHEMA_VERSION
            self.save(settings)
            return settings

        with self._path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if int(payload.get("schema_version", 1)) < CURRENT_SCHEMA_VERSION:
            self._backup_legacy_config()
            settings = AppSettings.from_dict(payload)
            settings.schema_version = CURRENT_SCHEMA_VERSION
            self.save(settings)
            return settings
        settings = AppSettings.from_dict(payload)
        if not settings.gestures:
            settings = build_default_settings()
            self.save(settings)
            return settings
        if self._append_missing_default_gestures(settings):
            self.save(settings)
        return settings

    def save(self, settings: AppSettings | None = None) -> None:
        if settings is not None:
            self._settings = settings
        payload = self._settings.to_dict()
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def _backup_legacy_config(self) -> None:
        backup_dir = self._path.parent / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_dir / f"settings-legacy-{stamp}.json"
        shutil.copy2(self._path, backup_path)

    def _load_latest_legacy_settings(self) -> AppSettings | None:
        candidates = [
            runtime_root() / "data" / CONFIG_FILE_NAME,
            Path.cwd() / "data" / CONFIG_FILE_NAME,
            Path.cwd() / "dist" / APP_DIR_NAME / "data" / CONFIG_FILE_NAME,
        ]
        source_root = Path(__file__).resolve().parents[2]
        candidates.append(source_root / "data" / CONFIG_FILE_NAME)
        candidates.append(source_root / "dist" / APP_DIR_NAME / "data" / CONFIG_FILE_NAME)

        existing: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved == self._path.resolve() or resolved in seen or not resolved.exists():
                continue
            seen.add(resolved)
            existing.append(resolved)
        if not existing:
            return None

        latest = max(existing, key=lambda item: item.stat().st_mtime)
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
            settings = AppSettings.from_dict(payload)
        except (OSError, ValueError, json.JSONDecodeError, KeyError):
            return None

        backup_dir = self._path.parent / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(latest, backup_dir / f"settings-migrated-from-{latest.parent.name}-{stamp}.json")
        return settings

    def _append_missing_default_gestures(self, settings: AppSettings) -> bool:
        default_settings = build_default_settings()
        existing_ids = {gesture.id for gesture in settings.gestures}
        appended = False
        for default_gesture in default_settings.gestures:
            if default_gesture.id in existing_ids:
                continue
            settings.gestures.append(default_gesture)
            appended = True
        return appended
