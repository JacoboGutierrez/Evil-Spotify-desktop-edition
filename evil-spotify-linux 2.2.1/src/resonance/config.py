from __future__ import annotations

import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_ID = "evil-spotify"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_ID
SETTINGS_FILE = CONFIG_DIR / "settings.json"
PLAYLISTS_FILE = CONFIG_DIR / "playlists.json"
LEGACY_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "resonance-player"

FREQUENCIES = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
FAVORITES_PLAYLIST = "Favoritos"

THEMES: dict[str, dict[str, str]] = {
    "Evil Red": {
        "background": "#090909",
        "panel": "#101010",
        "panel_alt": "#1B1B1B",
        "accent": "#F5000F",
        "text": "#F7F7F7",
        "muted": "#A8A8A8",
    },
    "Crimson": {
        "background": "#100407",
        "panel": "#1a090d",
        "panel_alt": "#2a1016",
        "accent": "#e1062c",
        "text": "#fff4f5",
        "muted": "#c69ba2",
    },
    "Graphite": {
        "background": "#111111",
        "panel": "#191919",
        "panel_alt": "#282828",
        "accent": "#ff3347",
        "text": "#f5f5f5",
        "muted": "#a7a7a7",
    },
    "Light": {
        "background": "#eeeeee",
        "panel": "#ffffff",
        "panel_alt": "#dedede",
        "accent": "#d90429",
        "text": "#151515",
        "muted": "#666666",
    },
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "es",
    "theme_name": "Evil Red",
    "theme": deepcopy(THEMES["Evil Red"]),
    "frequency_mode": "original",
    "volume": 75,
    "last_playlist": "Mi música",
    "shuffle": False,
    "repeat_mode": "off",
    "eq_gains": [0] * len(FREQUENCIES),
    "eq_selected_preset": "Plano",
    "eq_presets": {
        "Plano": [0] * len(FREQUENCIES),
        "Graves": [5, 4, 3, 1, 0, 0, -1, -1, 0, 1],
        "Vocal": [-2, -1, 0, 2, 4, 4, 3, 1, 0, -1],
        "Brillante": [-1, -1, 0, 0, 1, 2, 3, 4, 5, 5],
    },
}

DEFAULT_PLAYLISTS = {FAVORITES_PLAYLIST: [], "Mi música": []}


def _deep_merge(default: dict[str, Any], loaded: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(default)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


class ConfigStore:
    def __init__(self) -> None:
        self._migrate_legacy_data()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.settings = self._load_settings()
        self.playlists = self._load_playlists()
        self._repair_state()

    @staticmethod
    def _migrate_legacy_data() -> None:
        """Import the previous Resonance Player data once, when available."""
        if CONFIG_DIR.exists() or not LEGACY_CONFIG_DIR.exists():
            return
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            for name in ("settings.json", "playlists.json"):
                source = LEGACY_CONFIG_DIR / name
                destination = CONFIG_DIR / name
                if source.exists() and not destination.exists():
                    shutil.copy2(source, destination)
        except OSError:
            # Migration is optional. The application can continue with defaults.
            pass

    def _load_settings(self) -> dict[str, Any]:
        try:
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("settings root must be an object")
            return _deep_merge(DEFAULT_SETTINGS, loaded)
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            return deepcopy(DEFAULT_SETTINGS)

    def _load_playlists(self) -> dict[str, list[str]]:
        try:
            loaded = json.loads(PLAYLISTS_FILE.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("playlist root must be an object")
            cleaned: dict[str, list[str]] = {}
            for name, tracks in loaded.items():
                if isinstance(name, str) and name.strip() and isinstance(tracks, list):
                    cleaned[name] = [str(path) for path in tracks if isinstance(path, str)]
            return cleaned or deepcopy(DEFAULT_PLAYLISTS)
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            return deepcopy(DEFAULT_PLAYLISTS)

    def _repair_state(self) -> None:
        if not self.playlists:
            self.playlists = deepcopy(DEFAULT_PLAYLISTS)

        # Favoritos is a permanent system playlist. Keep it first in the
        # sidebar while preserving all existing user playlists and their order.
        favorites = self.playlists.get(FAVORITES_PLAYLIST, [])
        if not isinstance(favorites, list):
            favorites = []
        ordered_playlists: dict[str, list[str]] = {FAVORITES_PLAYLIST: favorites}
        for name, tracks in self.playlists.items():
            if name != FAVORITES_PLAYLIST:
                ordered_playlists[name] = tracks
        self.playlists = ordered_playlists

        last = self.settings.get("last_playlist")
        if last not in self.playlists:
            self.settings["last_playlist"] = "Mi música" if "Mi música" in self.playlists else next(iter(self.playlists))

        gains = self.settings.get("eq_gains", [])
        if not isinstance(gains, list) or len(gains) != len(FREQUENCIES):
            self.settings["eq_gains"] = [0] * len(FREQUENCIES)
        else:
            self.settings["eq_gains"] = [max(-12, min(12, int(value))) for value in gains]

        presets = self.settings.get("eq_presets")
        if not isinstance(presets, dict):
            self.settings["eq_presets"] = deepcopy(DEFAULT_SETTINGS["eq_presets"])

        theme = self.settings.get("theme", {})
        if not isinstance(theme, dict):
            self.settings["theme"] = deepcopy(THEMES["Evil Red"])
        else:
            self.settings["theme"] = _deep_merge(THEMES["Evil Red"], theme)

        if self.settings.get("frequency_mode") not in {"original", "432"}:
            self.settings["frequency_mode"] = "original"

        self.settings["shuffle"] = bool(self.settings.get("shuffle", False))
        if self.settings.get("repeat_mode") not in {"off", "playlist", "one"}:
            self.settings["repeat_mode"] = "off"

        # Named presets always use their current palette. This upgrades users
        # of the previous Evil Red default without overwriting Custom themes.
        theme_name = self.settings.get("theme_name")
        if theme_name in {"Midnight", "Aurora"}:
            theme_name = "Evil Red"
            self.settings["theme_name"] = theme_name
        if theme_name in THEMES:
            self.settings["theme"] = deepcopy(THEMES[theme_name])
        elif theme_name != "Custom":
            self.settings["theme_name"] = "Custom"

        self.save_all()

    def save_settings(self) -> None:
        _atomic_write(SETTINGS_FILE, self.settings)

    def save_playlists(self) -> None:
        _atomic_write(PLAYLISTS_FILE, self.playlists)

    def save_all(self) -> None:
        self.save_settings()
        self.save_playlists()
