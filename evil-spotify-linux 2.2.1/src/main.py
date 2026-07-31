from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from resonance.config import ConfigStore
from resonance.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Evil Spotify")
    app.setApplicationDisplayName("Evil Spotify")
    app.setApplicationVersion("2.2.0")
    app.setDesktopFileName("evil-spotify")
    app.setOrganizationName("Local")
    root = Path(__file__).resolve().parent.parent
    icon_path = root / "assets" / "evil-spotify.png"
    app.setWindowIcon(QIcon(str(icon_path)))
    store = ConfigStore()
    window = MainWindow(store, str(icon_path))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
