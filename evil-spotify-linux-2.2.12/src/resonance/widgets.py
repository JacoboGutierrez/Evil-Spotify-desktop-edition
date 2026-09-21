from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, Signal, QTimer
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QToolButton,
)

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".ogg", ".oga", ".opus", ".m4a", ".aac",
    ".wma", ".aiff", ".aif", ".ape", ".wv", ".mpc", ".alac", ".mka",
}


class ToggleSwitch(QAbstractButton):
    """Small painted on/off switch that follows the active application theme."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(48, 26)
        self._accent = QColor("#F5000F")
        self._off = QColor("#4a4a4a")
        self._knob = QColor("#ffffff")

    def set_theme_colors(self, accent: str, off: str, knob: str = "#ffffff") -> None:
        self._accent = QColor(accent)
        self._off = QColor(off)
        self._knob = QColor(knob)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_rect = QRectF(1.0, 3.0, self.width() - 2.0, self.height() - 6.0)
        radius = track_rect.height() / 2.0
        track = QPainterPath()
        track.addRoundedRect(track_rect, radius, radius)
        painter.fillPath(track, self._accent if self.isChecked() else self._off)

        diameter = self.height() - 8.0
        x = self.width() - diameter - 4.0 if self.isChecked() else 4.0
        knob_rect = QRectF(x, 4.0, diameter, diameter)
        painter.setPen(QPen(QColor(0, 0, 0, 45), 1.0))
        painter.setBrush(self._knob)
        painter.drawEllipse(knob_rect)
        painter.end()


class TrackRowWidget(QFrame):
    """Interactive track row with a Spotify-style favorite control.

    The outline heart is revealed only while hovering a non-favorite row. A
    favorite track always shows a filled heart. The remaining row area keeps
    selection, double-click playback and drag-to-reorder behavior.
    """

    clicked = Signal(object)
    double_clicked = Signal()
    drag_requested = Signal()
    favorite_toggled = Signal(bool)

    def __init__(
        self,
        number: str,
        title: str,
        artist: str,
        album: str,
        duration: str,
        favorite: bool,
        favorite_add_text: str = "Agregar a Favoritos",
        favorite_remove_text: str = "Quitar de Favoritos",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("trackRow")
        self.setMinimumHeight(56)
        self.setMouseTracking(True)
        self._favorite = bool(favorite)
        self._favorite_add_text = favorite_add_text
        self._favorite_remove_text = favorite_remove_text
        self._row_hovered = False
        self._press_position: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)

        self.number_label = QLabel(number)
        self.number_label.setObjectName("trackCellNumber")
        self.number_label.setFixedWidth(42)
        self.number_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.number_label)

        self.favorite_button = QToolButton()
        self.favorite_button.setObjectName("favoriteButton")
        self.favorite_button.setFixedSize(30, 30)
        self.favorite_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favorite_button.clicked.connect(self._favorite_clicked)
        layout.addWidget(self.favorite_button)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("trackCellTitle")
        self.title_label.setToolTip(title)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title_label, 3)

        self.artist_label = QLabel(artist or "—")
        self.artist_label.setObjectName("trackCellMeta")
        self.artist_label.setToolTip(artist or "—")
        self.artist_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.artist_label, 2)

        self.album_label = QLabel(album or "—")
        self.album_label.setObjectName("trackCellMeta")
        self.album_label.setToolTip(album or "—")
        self.album_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.album_label, 2)

        self.duration_label = QLabel(duration)
        self.duration_label.setObjectName("trackCellDuration")
        self.duration_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.duration_label.setFixedWidth(72)
        self.duration_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.duration_label)

        self.set_favorite(self._favorite)

    def set_favorite(self, favorite: bool) -> None:
        self._favorite = bool(favorite)
        self.favorite_button.setProperty("favorite", "true" if self._favorite else "false")
        self.favorite_button.setToolTip(
            self._favorite_remove_text if self._favorite else self._favorite_add_text
        )
        self._refresh_heart_visual()
        self.favorite_button.style().unpolish(self.favorite_button)
        self.favorite_button.style().polish(self.favorite_button)
        self.favorite_button.update()

    def _refresh_heart_visual(self) -> None:
        if self._favorite:
            self.favorite_button.setText("♥")
            self.favorite_button.setEnabled(True)
        elif self._row_hovered:
            self.favorite_button.setText("♡")
            self.favorite_button.setEnabled(True)
        else:
            # Keep the fixed-width slot in the layout while hiding the control.
            self.favorite_button.setText("")
            self.favorite_button.setEnabled(False)

    def set_favorite_tooltips(self, add_text: str, remove_text: str) -> None:
        self._favorite_add_text = add_text
        self._favorite_remove_text = remove_text
        self.set_favorite(self._favorite)

    def is_favorite(self) -> bool:
        return self._favorite

    def _favorite_clicked(self) -> None:
        self.favorite_toggled.emit(not self._favorite)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._row_hovered = True
        self._refresh_heart_visual()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._row_hovered = False
        self._refresh_heart_visual()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_position = event.position().toPoint()
            self.clicked.emit(event.modifiers())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if (
            self._press_position is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and (event.position().toPoint() - self._press_position).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._press_position = None
            self.drag_requested.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._press_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class TrackListWidget(QListWidget):
    """Drag-and-drop track list whose height follows all its rows.

    The list deliberately has no internal scrollbar. Wheel events are passed to
    the enclosing body scroll area, so the hero, controls, table header and
    tracks all move together as one page.
    """

    files_dropped = Signal(list)
    order_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(False)
        self.setSpacing(0)
        self.setUniformItemSizes(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sync_content_height()

    def begin_internal_drag(self) -> None:
        """Start an internal move using the currently selected track rows."""
        self.startDrag(Qt.DropAction.MoveAction)

    def sync_content_height(self) -> None:
        # 58 px per track plus a small viewport allowance. Keep an empty drop
        # target visible when a playlist contains no songs.
        self.setFixedHeight(max(92, self.count() * 58 + 4))
        self.updateGeometry()

    def addItem(self, item: QListWidgetItem | str) -> None:  # type: ignore[override]
        super().addItem(item)
        self.sync_content_height()

    def takeItem(self, row: int) -> QListWidgetItem | None:  # type: ignore[override]
        item = super().takeItem(row)
        self.sync_content_height()
        return item

    def clear(self) -> None:  # type: ignore[override]
        super().clear()
        self.sync_content_height()

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Forward wheel/trackpad movement to the outer body scroll area. This
        # keeps scrolling natural even when the pointer is directly over a row.
        parent = self.parentWidget()
        while parent is not None and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if isinstance(parent, QScrollArea):
            bar = parent.verticalScrollBar()
            pixel_delta = event.pixelDelta().y()
            if pixel_delta:
                delta = pixel_delta
            else:
                steps = event.angleDelta().y() / 120.0
                delta = int(steps * max(36, bar.singleStep() * 3))
            bar.setValue(bar.value() - delta)
            event.accept()
            return
        event.ignore()

    @staticmethod
    def _paths_from_event(event: QDropEvent | QDragEnterEvent) -> list[str]:
        if not event.mimeData().hasUrls():
            return []
        result: list[str] = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                result.append(str(path.resolve()))
            elif path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_file() and child.suffix.lower() in AUDIO_EXTENSIONS:
                        result.append(str(child.resolve()))
        return result

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._paths_from_event(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = self._paths_from_event(event)
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)
        QTimer.singleShot(0, self.sync_content_height)
        self.order_changed.emit()
