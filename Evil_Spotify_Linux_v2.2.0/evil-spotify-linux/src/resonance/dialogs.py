from __future__ import annotations

from copy import deepcopy
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .config import FREQUENCIES, THEMES
from .i18n import tr


class ColorButton(QPushButton):
    def __init__(self, color: str, changed: Callable[[str], None]) -> None:
        super().__init__()
        self.color = color
        self.changed = changed
        self.setFixedWidth(100)
        self.clicked.connect(self.pick_color)
        self.refresh()

    def refresh(self) -> None:
        # Only feed validated, normalized colors to Qt's stylesheet parser.
        # The previous version ended this rule with two closing braces, which
        # caused a warning every time a color button was refreshed.
        parsed = QColor(str(self.color))
        if not parsed.isValid():
            parsed = QColor("#F5000F")
        self.color = parsed.name(QColor.NameFormat.HexRgb)
        foreground = "#111111" if parsed.lightness() > 150 else "#ffffff"

        self.setText(self.color.upper())
        self.setStyleSheet(
            "QPushButton {"
            f" background-color: {self.color};"
            f" color: {foreground};"
            " border: 1px solid #7f7f7f;"
            " border-radius: 8px;"
            " padding: 7px;"
            "}"
            "QPushButton:hover { border: 1px solid #ffffff; }"
            "QPushButton:pressed { padding-top: 8px; padding-bottom: 6px; }"
        )

    def set_color(self, color: str) -> None:
        self.color = color
        self.refresh()

    def pick_color(self) -> None:
        selected = QColorDialog.getColor(QColor(self.color), self)
        if selected.isValid():
            self.color = selected.name()
            self.refresh()
            self.changed(self.color)


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: dict,
        preview_theme: Callable[[dict], None],
        preview_eq: Callable[[list[int]], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.original = deepcopy(settings)
        self.working = deepcopy(settings)
        self.preview_theme = preview_theme
        self.preview_eq = preview_eq
        self.language = self.working.get("language", "es")
        self.color_buttons: dict[str, ColorButton] = {}
        self.eq_sliders: list[QSlider] = []
        self.eq_value_labels: list[QLabel] = []

        self.setWindowTitle(tr(self.language, "settings"))
        self.resize(780, 560)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)
        self._build_theme_tab()
        self._build_language_tab()
        self._build_equalizer_tab()
        self._apply_combo_popup_theme()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr(self.language, "save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr(self.language, "cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_theme_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES) + ["Custom"])
        theme_name = self.working.get("theme_name", "Evil Red")
        self.theme_combo.setCurrentText(theme_name if theme_name in THEMES else "Custom")
        self.theme_combo.currentTextChanged.connect(self._theme_preset_changed)
        form.addRow(tr(self.language, "theme_preset"), self.theme_combo)

        colors = QWidget()
        colors_layout = QFormLayout(colors)
        labels = {
            "background": "background",
            "panel": "panel",
            "panel_alt": "panel_alt",
            "accent": "accent",
            "text": "text",
            "muted": "muted",
        }
        for key, label_key in labels.items():
            button = ColorButton(
                self.working["theme"].get(key, THEMES["Evil Red"][key]),
                lambda color, item=key: self._custom_color_changed(item, color),
            )
            self.color_buttons[key] = button
            colors_layout.addRow(tr(self.language, label_key), button)
        form.addRow(tr(self.language, "custom_colors"), colors)
        layout.addLayout(form)

        reset = QPushButton(tr(self.language, "reset_theme"))
        reset.clicked.connect(lambda: self.theme_combo.setCurrentText("Evil Red"))
        layout.addWidget(reset, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        self.tabs.addTab(tab, tr(self.language, "theme"))

    def _build_language_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)
        self.language_combo = QComboBox()
        self.language_combo.addItem(tr(self.language, "spanish"), "es")
        self.language_combo.addItem(tr(self.language, "english"), "en")
        index = self.language_combo.findData(self.working.get("language", "es"))
        self.language_combo.setCurrentIndex(max(0, index))
        layout.addRow(tr(self.language, "language"), self.language_combo)
        self.tabs.addTab(tab, tr(self.language, "language"))

    def _build_equalizer_tab(self) -> None:
        tab = QWidget()
        root = QVBoxLayout(tab)

        help_label = QLabel(tr(self.language, "eq_help"))
        help_label.setWordWrap(True)
        root.addWidget(help_label)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(tr(self.language, "preset")))
        self.preset_combo = QComboBox()
        self._reload_preset_combo()
        self.preset_combo.currentTextChanged.connect(self._load_preset)
        preset_row.addWidget(self.preset_combo, 1)
        save_preset = QPushButton(tr(self.language, "save_preset"))
        save_preset.clicked.connect(self._save_preset)
        preset_row.addWidget(save_preset)
        delete_preset = QPushButton(tr(self.language, "delete_preset"))
        delete_preset.clicked.connect(self._delete_preset)
        preset_row.addWidget(delete_preset)
        root.addLayout(preset_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        frame = QFrame()
        bands = QHBoxLayout(frame)
        gains = self.working.get("eq_gains", [0] * len(FREQUENCIES))
        for idx, frequency in enumerate(FREQUENCIES):
            column = QVBoxLayout()
            value = QLabel(f"{int(gains[idx]):+d} dB")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(int(gains[idx]))
            slider.setTickInterval(3)
            slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
            slider.valueChanged.connect(lambda amount, i=idx: self._eq_value_changed(i, amount))
            freq_label = QLabel(self._format_frequency(frequency))
            freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(value)
            column.addWidget(slider, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(freq_label)
            bands.addLayout(column, 1)
            self.eq_sliders.append(slider)
            self.eq_value_labels.append(value)
        scroll.setWidget(frame)
        root.addWidget(scroll, 1)
        self.tabs.addTab(tab, tr(self.language, "equalizer"))

    def _apply_combo_popup_theme(self) -> None:
        """Keep combo popup lists readable under every custom theme.

        Qt renders combo popups in a separate container on some Linux desktop
        environments, so relying only on the parent window stylesheet can leave
        them with a white system background. Styling each popup view directly
        makes Theme, Language and Preset follow the configured panel colors.
        """
        theme = self.working.get("theme", THEMES["Evil Red"])
        panel = theme.get("panel", "#101010")
        panel_alt = theme.get("panel_alt", "#1B1B1B")
        text = theme.get("text", "#F7F7F7")
        popup_style = f"""
            QListView {{
                background-color: {panel};
                color: {text};
                border: 1px solid {panel_alt};
                outline: 0;
                selection-background-color: {panel_alt};
                selection-color: {text};
            }}
            QListView::item {{
                background-color: {panel};
                color: {text};
                min-height: 30px;
                padding: 5px 9px;
            }}
            QListView::item:hover,
            QListView::item:selected {{
                background-color: {panel_alt};
                color: {text};
            }}
        """
        for attribute in ("theme_combo", "language_combo", "preset_combo"):
            combo = getattr(self, attribute, None)
            if combo is not None:
                combo.view().setStyleSheet(popup_style)

    @staticmethod
    def _format_frequency(frequency: int) -> str:
        return f"{frequency // 1000}k" if frequency >= 1000 else str(frequency)

    def _theme_preset_changed(self, name: str) -> None:
        if name not in THEMES:
            return
        self.working["theme_name"] = name
        self.working["theme"] = deepcopy(THEMES[name])
        for key, button in self.color_buttons.items():
            button.set_color(self.working["theme"][key])
        self.preview_theme(self.working["theme"])
        self._apply_combo_popup_theme()

    def _custom_color_changed(self, key: str, color: str) -> None:
        self.working["theme_name"] = "Custom"
        self.working["theme"][key] = color
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText("Custom")
        self.theme_combo.blockSignals(False)
        self.preview_theme(self.working["theme"])
        self._apply_combo_popup_theme()

    def _reload_preset_combo(self, select: str | None = None) -> None:
        current = select or self.working.get("eq_selected_preset", "Plano")
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(self.working.get("eq_presets", {}).keys()))
        if self.preset_combo.findText(current) >= 0:
            self.preset_combo.setCurrentText(current)
        self.preset_combo.blockSignals(False)

    def _load_preset(self, name: str) -> None:
        gains = self.working.get("eq_presets", {}).get(name)
        if not isinstance(gains, list) or len(gains) != len(FREQUENCIES):
            return
        self.working["eq_selected_preset"] = name
        for slider, gain in zip(self.eq_sliders, gains):
            slider.blockSignals(True)
            slider.setValue(int(gain))
            slider.blockSignals(False)
        self.working["eq_gains"] = [int(value) for value in gains]
        self._refresh_eq_labels()
        self.preview_eq(self.working["eq_gains"])

    def _eq_value_changed(self, index: int, value: int) -> None:
        self.working["eq_gains"][index] = int(value)
        self.eq_value_labels[index].setText(f"{value:+d} dB")
        self.working["eq_selected_preset"] = ""
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(-1)
        self.preset_combo.blockSignals(False)
        self.preview_eq(self.working["eq_gains"])

    def _refresh_eq_labels(self) -> None:
        for label, slider in zip(self.eq_value_labels, self.eq_sliders):
            label.setText(f"{slider.value():+d} dB")

    def _save_preset(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(tr(self.language, "save_preset"))
        layout = QVBoxLayout(dialog)
        edit = QLineEdit()
        edit.setPlaceholderText(tr(self.language, "preset_name"))
        layout.addWidget(edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr(self.language, "save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr(self.language, "cancel"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name = edit.text().strip()
        if not name:
            return
        self.working.setdefault("eq_presets", {})[name] = [slider.value() for slider in self.eq_sliders]
        self.working["eq_selected_preset"] = name
        self._reload_preset_combo(name)

    def _delete_preset(self) -> None:
        name = self.preset_combo.currentText()
        if not name:
            return
        if name == "Plano":
            QMessageBox.information(self, tr(self.language, "equalizer"), tr(self.language, "cannot_delete_flat"))
            return
        answer = QMessageBox.question(
            self,
            tr(self.language, "delete_preset"),
            tr(self.language, "confirm_delete_preset", name=name),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.working.get("eq_presets", {}).pop(name, None)
        self._reload_preset_combo("Plano")
        self._load_preset("Plano")

    def accept(self) -> None:
        self.working["language"] = self.language_combo.currentData()
        self.working["eq_gains"] = [slider.value() for slider in self.eq_sliders]
        super().accept()

    def reject(self) -> None:
        self.preview_theme(self.original["theme"])
        self.preview_eq(self.original["eq_gains"])
        super().reject()
