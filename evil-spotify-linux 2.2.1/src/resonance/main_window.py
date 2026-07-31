from __future__ import annotations

import random
from copy import deepcopy
from pathlib import Path

from mutagen import File as MutagenFile
from PySide6.QtCore import QItemSelectionModel, QSize, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .config import ConfigStore, FAVORITES_PLAYLIST, FREQUENCIES
from .dialogs import SettingsDialog
from .i18n import tr
from .mpv_backend import MpvBackend
from .widgets import AUDIO_EXTENSIONS, ToggleSwitch, TrackListWidget, TrackRowWidget


class MainWindow(QMainWindow):
    def __init__(self, store: ConfigStore, icon_path: str) -> None:
        super().__init__()
        self.store = store
        self.settings = store.settings
        self.playlists = store.playlists
        self.language = self.settings.get("language", "es")
        self.current_playlist = self.settings.get("last_playlist", next(iter(self.playlists)))
        self.current_index = -1
        self.current_path = ""
        self.duration = 0.0
        self.dragging_seek = False
        self._last_filter_error_shown = False
        self.shuffle_remaining: list[int] = []
        self.shuffle_history: list[int] = []
        self.icon_path = icon_path
        self.icon_pixmap = QPixmap(icon_path)
        self._metadata_cache: dict[str, tuple[str, str, str, str]] = {}

        self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1020, 650)
        self.resize(1320, 820)

        self.backend = MpvBackend()
        self.backend.event_received.connect(self._handle_mpv_event)
        self.backend.backend_error.connect(self._backend_error)

        self._build_ui()
        self._create_shortcuts()
        self.apply_theme(self.settings["theme"])
        self.retranslate_ui()
        self._refresh_playlist_sidebar()
        self._select_playlist(self.current_playlist)
        self._sync_playback_mode_buttons()

        if not self.backend.start():
            QTimer.singleShot(0, self._show_mpv_missing)
        else:
            self.backend.set_volume(int(self.settings.get("volume", 75)))
            self._apply_audio_filters()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralRoot")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.setObjectName("bodySplitter")
        body.setChildrenCollapsible(False)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(245)
        sidebar.setMaximumWidth(330)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 14, 14)
        sidebar_layout.setSpacing(12)

        brand_row = QHBoxLayout()
        self.brand_icon = QLabel()
        self.brand_icon.setObjectName("brandIcon")
        self.brand_icon.setFixedSize(42, 42)
        self.brand_icon.setPixmap(
            self.icon_pixmap.scaled(
                42,
                42,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        brand_row.addWidget(self.brand_icon)
        self.title_label = QLabel()
        self.title_label.setObjectName("brandTitle")
        brand_row.addWidget(self.title_label, 1)
        sidebar_layout.addLayout(brand_row)

        self.library_label = QLabel()
        self.library_label.setObjectName("libraryTitle")
        sidebar_layout.addWidget(self.library_label)

        playlist_header = QHBoxLayout()
        self.playlists_heading = QLabel()
        self.playlists_heading.setObjectName("mutedCaps")
        playlist_header.addWidget(self.playlists_heading)
        playlist_header.addStretch(1)
        self.new_playlist_button = QToolButton()
        self.new_playlist_button.setObjectName("smallRoundButton")
        self.new_playlist_button.setText("+")
        self.new_playlist_button.clicked.connect(self._new_playlist)
        playlist_header.addWidget(self.new_playlist_button)
        self.delete_playlist_button = QToolButton()
        self.delete_playlist_button.setObjectName("smallRoundButton")
        self.delete_playlist_button.setText("−")
        self.delete_playlist_button.clicked.connect(self._delete_playlist)
        playlist_header.addWidget(self.delete_playlist_button)
        sidebar_layout.addLayout(playlist_header)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("playlistList")
        self.playlist_list.itemClicked.connect(
            lambda item: self._select_playlist(item.data(Qt.ItemDataRole.UserRole))
        )
        self.playlist_list.itemDoubleClicked.connect(self._rename_playlist)
        sidebar_layout.addWidget(self.playlist_list, 1)

        self.create_playlist_button = QPushButton()
        self.create_playlist_button.setObjectName("createPlaylistButton")
        self.create_playlist_button.clicked.connect(self._new_playlist)
        sidebar_layout.addWidget(self.create_playlist_button)

        self.about_label = QLabel()
        self.about_label.setWordWrap(True)
        self.about_label.setObjectName("mutedSmall")
        sidebar_layout.addWidget(self.about_label)
        body.addWidget(sidebar)

        self.main_scroll = QScrollArea()
        self.main_scroll.setObjectName("mainBodyScroll")
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.main_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        main_panel = QFrame()
        main_panel.setObjectName("mainPanel")
        main_layout = QVBoxLayout(main_panel)
        main_layout.setContentsMargins(22, 16, 22, 24)
        main_layout.setSpacing(14)
        main_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        topbar = QHBoxLayout()
        topbar.addStretch(1)
        self.frequency_text = QLabel("432 Hz")
        self.frequency_text.setObjectName("frequencyText")
        topbar.addWidget(self.frequency_text)
        self.frequency_switch = ToggleSwitch()
        self.frequency_switch.toggled.connect(self._toggle_frequency)
        topbar.addWidget(self.frequency_switch)

        self.eq_button = QToolButton()
        self.eq_button.setObjectName("topIconButton")
        self.eq_button.setText("▥")
        self.eq_button.clicked.connect(lambda: self._open_settings(2))
        topbar.addWidget(self.eq_button)

        self.settings_button = QToolButton()
        self.settings_button.setObjectName("topIconButton")
        self.settings_button.setText("⚙")
        self.settings_button.clicked.connect(lambda: self._open_settings(0))
        topbar.addWidget(self.settings_button)
        main_layout.addLayout(topbar)

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(24)

        self.hero_icon = QLabel()
        self.hero_icon.setObjectName("heroIcon")
        self.hero_icon.setFixedSize(138, 138)
        self.hero_icon.setPixmap(
            self.icon_pixmap.scaled(
                138,
                138,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        hero_layout.addWidget(self.hero_icon)

        hero_text = QVBoxLayout()
        hero_text.addStretch(1)
        self.hero_kicker = QLabel("PLAYLIST")
        self.hero_kicker.setObjectName("heroKicker")
        hero_text.addWidget(self.hero_kicker)
        self.current_playlist_label = QLabel()
        self.current_playlist_label.setObjectName("heroTitle")
        self.current_playlist_label.setWordWrap(True)
        hero_text.addWidget(self.current_playlist_label)
        self.playlist_count_label = QLabel()
        self.playlist_count_label.setObjectName("heroSubtitle")
        hero_text.addWidget(self.playlist_count_label)
        hero_buttons = QHBoxLayout()
        self.play_playlist_button = QPushButton()
        self.play_playlist_button.setObjectName("primaryButton")
        self.play_playlist_button.clicked.connect(self._play_current_playlist)
        hero_buttons.addWidget(self.play_playlist_button)
        hero_buttons.addStretch(1)
        hero_text.addLayout(hero_buttons)
        hero_text.addStretch(1)
        hero_layout.addLayout(hero_text, 1)
        main_layout.addWidget(hero)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        self.add_files_button = QPushButton()
        self.add_files_button.clicked.connect(self._add_files_dialog)
        toolbar.addWidget(self.add_files_button)
        self.remove_tracks_button = QPushButton()
        self.remove_tracks_button.clicked.connect(self._remove_selected_tracks)
        toolbar.addWidget(self.remove_tracks_button)
        main_layout.addLayout(toolbar)

        self.drop_hint_label = QLabel()
        self.drop_hint_label.setObjectName("dropHint")
        self.drop_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.drop_hint_label)

        track_header = QFrame()
        track_header.setObjectName("trackHeader")
        track_header_layout = QHBoxLayout(track_header)
        track_header_layout.setContentsMargins(12, 6, 12, 8)
        track_header_layout.setSpacing(12)

        self.number_column_label = QLabel("#")
        self.number_column_label.setObjectName("trackHeaderCell")
        self.number_column_label.setFixedWidth(42)
        track_header_layout.addWidget(self.number_column_label)

        # Intentionally blank: hearts sit here without adding another column title.
        self.favorite_column_spacer = QLabel()
        self.favorite_column_spacer.setFixedWidth(30)
        track_header_layout.addWidget(self.favorite_column_spacer)

        self.title_column_label = QLabel()
        self.title_column_label.setObjectName("trackHeaderCell")
        track_header_layout.addWidget(self.title_column_label, 3)

        self.artist_column_label = QLabel()
        self.artist_column_label.setObjectName("trackHeaderCell")
        track_header_layout.addWidget(self.artist_column_label, 2)

        self.album_column_label = QLabel()
        self.album_column_label.setObjectName("trackHeaderCell")
        track_header_layout.addWidget(self.album_column_label, 2)

        self.duration_column_label = QLabel()
        self.duration_column_label.setObjectName("trackHeaderCell")
        self.duration_column_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.duration_column_label.setFixedWidth(72)
        track_header_layout.addWidget(self.duration_column_label)
        main_layout.addWidget(track_header)

        self.track_list = TrackListWidget()
        self.track_list.setObjectName("trackList")
        self.track_list.files_dropped.connect(self._add_paths)
        self.track_list.order_changed.connect(self._save_track_order)
        self.track_list.itemDoubleClicked.connect(
            lambda item: self._play_index(self.track_list.row(item))
        )
        self.track_list.itemSelectionChanged.connect(self._update_remove_button)
        main_layout.addWidget(self.track_list)

        self.main_scroll.setWidget(main_panel)
        body.addWidget(self.main_scroll)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setSizes([280, 1040])
        root.addWidget(body, 1)

        player = QFrame()
        player.setObjectName("playerBar")
        player_layout = QHBoxLayout(player)
        player_layout.setContentsMargins(18, 10, 18, 10)
        player_layout.setSpacing(18)

        now_box = QHBoxLayout()
        self.player_icon = QLabel()
        self.player_icon.setFixedSize(54, 54)
        self.player_icon.setPixmap(
            self.icon_pixmap.scaled(
                54,
                54,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        now_box.addWidget(self.player_icon)
        now_text = QVBoxLayout()
        self.now_playing_label = QLabel()
        self.now_playing_label.setObjectName("nowPlaying")
        self.now_playing_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        now_text.addStretch(1)
        now_text.addWidget(self.now_playing_label)
        self.now_artist_label = QLabel()
        self.now_artist_label.setObjectName("mutedSmall")
        now_text.addWidget(self.now_artist_label)
        now_text.addStretch(1)
        now_box.addLayout(now_text, 1)
        player_layout.addLayout(now_box, 1)

        center_player = QVBoxLayout()
        controls = QHBoxLayout()
        controls.addStretch(1)

        self.shuffle_button = QToolButton()
        self.shuffle_button.setObjectName("modeButton")
        self.shuffle_button.setText("⤨")
        self.shuffle_button.setCheckable(True)
        self.shuffle_button.toggled.connect(self._toggle_shuffle)
        controls.addWidget(self.shuffle_button)

        self.previous_button = QToolButton()
        self.previous_button.setObjectName("transportButton")
        self.previous_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward)
        )
        self.previous_button.clicked.connect(self._previous_track)
        controls.addWidget(self.previous_button)

        self.play_button = QToolButton()
        self.play_button.setObjectName("playButton")
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.clicked.connect(self._toggle_playback)
        controls.addWidget(self.play_button)

        self.next_button = QToolButton()
        self.next_button.setObjectName("transportButton")
        self.next_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward)
        )
        self.next_button.clicked.connect(self._next_track)
        controls.addWidget(self.next_button)

        self.repeat_playlist_button = QToolButton()
        self.repeat_playlist_button.setObjectName("modeButton")
        self.repeat_playlist_button.setText("↻")
        self.repeat_playlist_button.setCheckable(True)
        self.repeat_playlist_button.toggled.connect(self._toggle_repeat_playlist)
        controls.addWidget(self.repeat_playlist_button)

        self.repeat_one_button = QToolButton()
        self.repeat_one_button.setObjectName("modeButton")
        self.repeat_one_button.setText("↻¹")
        self.repeat_one_button.setCheckable(True)
        self.repeat_one_button.toggled.connect(self._toggle_repeat_one)
        controls.addWidget(self.repeat_one_button)

        controls.addStretch(1)
        center_player.addLayout(controls)

        seek_row = QHBoxLayout()
        self.elapsed_label = QLabel("00:00")
        self.elapsed_label.setObjectName("mutedSmall")
        seek_row.addWidget(self.elapsed_label)
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderPressed.connect(lambda: setattr(self, "dragging_seek", True))
        self.seek_slider.sliderMoved.connect(self._preview_seek)
        self.seek_slider.sliderReleased.connect(self._commit_seek)
        seek_row.addWidget(self.seek_slider, 1)
        self.total_label = QLabel("00:00")
        self.total_label.setObjectName("mutedSmall")
        seek_row.addWidget(self.total_label)
        center_player.addLayout(seek_row)
        player_layout.addLayout(center_player, 2)

        volume_box = QHBoxLayout()
        self.volume_icon_label = QLabel("🔊")
        volume_box.addWidget(self.volume_icon_label)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setFixedWidth(150)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.settings.get("volume", 75)))
        self.volume_slider.valueChanged.connect(self._volume_changed)
        volume_box.addWidget(self.volume_slider)
        player_layout.addLayout(volume_box, 1)
        root.addWidget(player)

    def _create_shortcuts(self) -> None:
        play = QAction(self)
        play.setShortcut(QKeySequence(Qt.Key.Key_Space))
        play.triggered.connect(self._toggle_playback)
        self.addAction(play)

        delete = QAction(self)
        delete.setShortcut(QKeySequence.StandardKey.Delete)
        delete.triggered.connect(self._remove_selected_tracks)
        self.addAction(delete)

        add = QAction(self)
        add.setShortcut(QKeySequence.StandardKey.Open)
        add.triggered.connect(self._add_files_dialog)
        self.addAction(add)

    def retranslate_ui(self) -> None:
        self.language = self.settings.get("language", "es")
        self.setWindowTitle(tr(self.language, "app_name"))
        self.title_label.setText(tr(self.language, "app_name"))
        self.library_label.setText(tr(self.language, "library"))
        self.playlists_heading.setText(tr(self.language, "playlists").upper())
        self.new_playlist_button.setToolTip(tr(self.language, "new_playlist"))
        self.delete_playlist_button.setToolTip(tr(self.language, "delete_playlist"))
        self.create_playlist_button.setText("＋  " + tr(self.language, "new_playlist"))
        self.add_files_button.setText(tr(self.language, "add_files"))
        self.remove_tracks_button.setText(tr(self.language, "remove_tracks"))
        self.play_playlist_button.setText("▶  " + tr(self.language, "play"))
        self.title_column_label.setText(tr(self.language, "title").upper())
        self.artist_column_label.setText(tr(self.language, "artist").upper())
        self.album_column_label.setText(tr(self.language, "album").upper())
        self.duration_column_label.setText(tr(self.language, "duration").upper())
        self.about_label.setText(tr(self.language, "about_line"))
        self.settings_button.setToolTip(tr(self.language, "settings"))
        self.eq_button.setToolTip(tr(self.language, "equalizer"))
        self.frequency_switch.setToolTip(tr(self.language, "frequency_help"))
        self.frequency_text.setToolTip(tr(self.language, "frequency_help"))
        self.previous_button.setToolTip(tr(self.language, "previous"))
        self.next_button.setToolTip(tr(self.language, "next"))
        self.play_button.setToolTip(tr(self.language, "play"))
        self.shuffle_button.setToolTip(tr(self.language, "shuffle"))
        self.repeat_playlist_button.setToolTip(tr(self.language, "repeat_playlist"))
        self.repeat_one_button.setToolTip(tr(self.language, "repeat_one"))
        self.volume_slider.setToolTip(tr(self.language, "volume"))
        if not self.current_path:
            self.now_playing_label.setText(tr(self.language, "now_playing"))
            self.now_artist_label.clear()
        self._update_frequency_switch()
        self._update_empty_state()
        self._update_playlist_summary()
        self._refresh_playlist_sidebar()
        self._refresh_favorite_widgets()

    def apply_theme(self, theme: dict) -> None:
        background = theme.get("background", "#090909")
        panel = theme.get("panel", "#101010")
        panel_alt = theme.get("panel_alt", "#1b1b1b")
        accent = theme.get("accent", "#F5000F")
        text = theme.get("text", "#f7f7f7")
        muted = theme.get("muted", "#a8a8a8")
        self.frequency_switch.set_theme_colors(accent, panel_alt, text)
        self.setStyleSheet(
            f"""
            QWidget {{
                color: {text};
                font-family: Inter, 'Noto Sans', 'DejaVu Sans', sans-serif;
                font-size: 14px;
            }}
            QMainWindow, QDialog, QWidget#centralRoot {{ background-color: {background}; }}
            QFrame#sidebar {{ background-color: {panel}; border-right: 1px solid {panel_alt}; }}
            QFrame#mainPanel {{ background-color: {background}; }}
            QFrame#hero {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {accent}, stop:0.38 #5b0a16, stop:1 {panel});
                border: 1px solid {panel_alt};
                border-radius: 14px;
            }}
            QFrame#playerBar {{
                background-color: {panel};
                border-top: 1px solid {panel_alt};
            }}
            QLabel#brandTitle {{ font-size: 21px; font-weight: 800; }}
            QLabel#libraryTitle {{ font-size: 16px; font-weight: 700; margin-top: 8px; }}
            QLabel#mutedCaps {{ color: {muted}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#mutedSmall {{ color: {muted}; font-size: 11px; }}
            QLabel#heroKicker {{ font-size: 11px; font-weight: 800; }}
            QLabel#heroTitle {{ font-size: 38px; font-weight: 900; }}
            QLabel#heroSubtitle {{ color: {text}; font-size: 13px; }}
            QLabel#nowPlaying {{ font-size: 14px; font-weight: 700; }}
            QLabel#frequencyText {{ font-weight: 750; }}
            QLabel#dropHint {{
                color: {muted};
                border: 1px dashed {panel_alt};
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton, QToolButton {{
                background-color: {panel_alt};
                color: {text};
                border: 1px solid transparent;
                border-radius: 18px;
                padding: 8px 14px;
                font-weight: 650;
            }}
            QPushButton:hover, QToolButton:hover {{ background-color: #333333; }}
            QPushButton:pressed, QToolButton:pressed {{ background-color: {accent}; }}
            QPushButton:disabled, QToolButton:disabled {{ color: {muted}; background-color: {panel}; }}
            QPushButton#primaryButton {{ background-color: {accent}; color: #ffffff; min-width: 115px; }}
            QPushButton#primaryButton:hover {{ border: 1px solid #ffffff; }}
            QPushButton#createPlaylistButton {{ text-align: left; border-radius: 8px; }}
            QToolButton#smallRoundButton {{ min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; padding: 0; border-radius: 14px; }}
            QToolButton#topIconButton {{ min-width: 38px; max-width: 38px; min-height: 38px; max-height: 38px; padding: 0; border-radius: 19px; font-size: 18px; }}
            QToolButton#transportButton, QToolButton#modeButton {{ background: transparent; min-width: 34px; min-height: 34px; padding: 0; border-radius: 17px; }}
            QToolButton#modeButton {{ color: {muted}; font-size: 20px; }}
            QToolButton#modeButton:checked {{ color: {accent}; background-color: transparent; }}
            QToolButton#playButton {{ min-width: 48px; max-width: 48px; min-height: 48px; max-height: 48px; padding: 0; border-radius: 24px; background-color: {accent}; }}
            QFrame#trackHeader {{
                background-color: transparent;
                border-bottom: 1px solid {panel_alt};
            }}
            QLabel#trackHeaderCell {{
                color: {muted};
                font-size: 11px;
                font-weight: 750;
                letter-spacing: 0.7px;
            }}
            QFrame#trackRow {{ background-color: transparent; border: none; }}
            QLabel#trackCellNumber {{ color: {muted}; font-size: 12px; }}
            QLabel#trackCellTitle {{ color: {text}; font-size: 13px; font-weight: 650; }}
            QLabel#trackCellMeta {{ color: {muted}; font-size: 12px; }}
            QLabel#trackCellDuration {{ color: {muted}; font-size: 12px; }}
            QToolButton#favoriteButton {{
                background-color: transparent;
                border: none;
                border-radius: 15px;
                color: {muted};
                font-size: 21px;
                font-weight: 500;
                padding: 0;
            }}
            QToolButton#favoriteButton:hover {{ background-color: transparent; color: #F5000F; }}
            QToolButton#favoriteButton:disabled {{ background-color: transparent; color: transparent; border: none; }}
            QToolButton#favoriteButton[favorite="true"] {{ color: #F5000F; }}
            QListWidget {{ background-color: transparent; border: none; outline: none; padding: 2px; }}
            QListWidget::item {{ background-color: transparent; border-radius: 7px; padding: 9px; margin: 1px; }}
            QListWidget::item:hover {{ background-color: {panel_alt}; }}
            QListWidget::item:selected {{ background-color: #3b0d14; color: {text}; border-left: 3px solid {accent}; }}
            QListWidget#trackList {{ padding: 0; }}
            QListWidget#trackList::item {{
                border-bottom: 1px solid {panel_alt};
                border-radius: 4px;
                padding: 0;
                margin: 0;
            }}
            QListWidget#trackList::item:hover {{ background-color: {panel_alt}; }}
            QListWidget#trackList::item:selected {{ background-color: #421019; border-left: 3px solid {accent}; }}
            QSlider::groove:horizontal {{ height: 4px; background: #4a4a4a; border-radius: 2px; }}
            QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {text}; width: 13px; margin: -5px 0; border-radius: 6px; }}
            QSlider::groove:vertical {{ width: 5px; background: {panel_alt}; border-radius: 2px; }}
            QSlider::sub-page:vertical {{ background: {panel_alt}; }}
            QSlider::add-page:vertical {{ background: {accent}; }}
            QSlider::handle:vertical {{ background: {text}; height: 15px; margin: 0 -5px; border-radius: 7px; }}
            QComboBox, QLineEdit {{
                background-color: {panel};
                color: {text};
                border: 1px solid {panel_alt};
                border-radius: 8px;
                padding: 7px;
            }}
            QComboBox:focus, QLineEdit:focus {{ border-color: {accent}; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox QAbstractItemView {{
                background-color: {panel};
                color: {text};
                border: 1px solid {panel_alt};
                outline: 0;
                selection-background-color: {panel_alt};
                selection-color: {text};
            }}
            QTabWidget::pane {{ border: 1px solid {panel_alt}; border-radius: 10px; top: -1px; }}
            QTabBar::tab {{ background: {panel}; color: {muted}; padding: 9px 16px; border-radius: 8px 8px 0 0; }}
            QTabBar::tab:selected {{ background: {panel_alt}; color: {text}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollArea#mainBodyScroll > QWidget > QWidget {{ background-color: {background}; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 5px;
                margin: 3px 0 3px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {accent};
                min-height: 34px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{ background: {accent}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QSplitter::handle {{ background: {background}; width: 2px; }}
            QStatusBar {{ background: {panel}; color: {muted}; }}
            QToolTip {{ background-color: {panel_alt}; color: {text}; border: 1px solid {accent}; }}
            """
        )

    def _refresh_playlist_sidebar(self) -> None:
        self.playlist_list.clear()
        for name, tracks in self.playlists.items():
            item = QListWidgetItem(f"{name}\n{tr(self.language, 'track_count', count=len(tracks))}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setSizeHint(QSize(0, 52))
            self.playlist_list.addItem(item)
        self._refresh_playlist_sidebar_selection()

    def _select_playlist(self, name: str) -> None:
        if name not in self.playlists:
            return
        self.current_playlist = name
        self.settings["last_playlist"] = name
        self.store.save_settings()
        self.track_list.clear()
        for path in self.playlists[name]:
            self._append_track_item(path)
        tracks = self.playlists[name]
        self.current_index = tracks.index(self.current_path) if self.current_path in tracks else -1
        self.shuffle_remaining.clear()
        self.shuffle_history.clear()
        if self.settings.get("shuffle"):
            self._prepare_shuffle_cycle()
        self._update_empty_state()
        self._update_playlist_summary()
        self._refresh_playlist_sidebar_selection()

    def _refresh_playlist_sidebar_selection(self) -> None:
        for row in range(self.playlist_list.count()):
            item = self.playlist_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_playlist:
                self.playlist_list.setCurrentItem(item)
                self.delete_playlist_button.setEnabled(
                    self.current_playlist != FAVORITES_PLAYLIST and len(self.playlists) > 1
                )
                return

    def _update_playlist_summary(self) -> None:
        if not hasattr(self, "current_playlist_label"):
            return
        self.current_playlist_label.setText(self.current_playlist)
        count = len(self.playlists.get(self.current_playlist, []))
        self.playlist_count_label.setText(
            f"Evil Spotify  •  {tr(self.language, 'track_count', count=count)}"
        )
        self.play_playlist_button.setEnabled(count > 0)

    def _append_track_item(self, path: str) -> None:
        title, artist, album, duration = self._track_metadata(path)
        row_number = self.track_list.count() + 1
        exists = Path(path).exists()

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setToolTip(path)
        item.setSizeHint(QSize(0, 56))
        self.track_list.addItem(item)

        row_widget = TrackRowWidget(
            number=f"{row_number:02d}",
            title=("⚠  " if not exists else "") + title,
            artist=artist,
            album=album,
            duration=duration,
            favorite=self._is_favorite(path),
            favorite_add_text=tr(self.language, "add_to_favorites"),
            favorite_remove_text=tr(self.language, "remove_from_favorites"),
        )
        row_widget.clicked.connect(
            lambda modifiers, track_item=item: self._select_track_item(track_item, modifiers)
        )
        row_widget.double_clicked.connect(
            lambda track_item=item: self._play_index(self.track_list.row(track_item))
        )
        row_widget.drag_requested.connect(
            lambda track_item=item: self._begin_track_drag(track_item)
        )
        row_widget.favorite_toggled.connect(
            lambda favorite, track_path=path: self._set_favorite(track_path, favorite)
        )

        self.track_list.setItemWidget(item, row_widget)
        self.track_list.sync_content_height()

    def _select_track_item(self, item: QListWidgetItem, modifiers: Qt.KeyboardModifier) -> None:
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            selected = item.isSelected()
            self.track_list.setCurrentItem(
                item,
                QItemSelectionModel.SelectionFlag.NoUpdate,
            )
            item.setSelected(not selected)
        else:
            self.track_list.clearSelection()
            self.track_list.setCurrentItem(item)
            item.setSelected(True)
        self._update_remove_button()

    def _begin_track_drag(self, item: QListWidgetItem) -> None:
        if not item.isSelected():
            self.track_list.clearSelection()
            self.track_list.setCurrentItem(item)
            item.setSelected(True)
        self.track_list.begin_internal_drag()

    def _is_favorite(self, path: str) -> bool:
        return path in self.playlists.get(FAVORITES_PLAYLIST, [])

    def _set_favorite(self, path: str, favorite: bool) -> None:
        favorites = self.playlists.setdefault(FAVORITES_PLAYLIST, [])
        changed = False
        if favorite and path not in favorites:
            favorites.append(path)
            changed = True
        elif not favorite and path in favorites:
            self.playlists[FAVORITES_PLAYLIST] = [
                favorite_path for favorite_path in favorites if favorite_path != path
            ]
            changed = True

        if not changed:
            return

        self.store.save_playlists()
        if self.current_playlist == FAVORITES_PLAYLIST:
            self._reload_track_list()
            self._update_empty_state()
            self._update_playlist_summary()
        else:
            self._refresh_favorite_widgets(path)
        self._refresh_playlist_sidebar()
        message_key = "added_to_favorites" if favorite else "removed_from_favorites"
        self.statusBar().showMessage(tr(self.language, message_key), 2200)

    def _refresh_favorite_widgets(self, only_path: str | None = None) -> None:
        for row in range(self.track_list.count()):
            item = self.track_list.item(row)
            path = item.data(Qt.ItemDataRole.UserRole)
            if only_path is not None and path != only_path:
                continue
            row_widget = self.track_list.itemWidget(item)
            if isinstance(row_widget, TrackRowWidget):
                row_widget.set_favorite_tooltips(
                    tr(self.language, "add_to_favorites"),
                    tr(self.language, "remove_from_favorites"),
                )
                row_widget.set_favorite(self._is_favorite(path))

    @staticmethod
    def _format_track_duration(seconds: float | int | None) -> str:
        if seconds is None or seconds < 0:
            return "--:--"
        total = int(round(float(seconds)))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _track_metadata(self, path: str) -> tuple[str, str, str, str]:
        cached = self._metadata_cache.get(path)
        if cached is not None:
            return cached

        title = Path(path).stem
        artist = ""
        album = ""
        duration = "--:--"
        try:
            audio = MutagenFile(path, easy=True)
            if audio:
                tags = getattr(audio, "tags", None)
                if tags:
                    title_values = tags.get("title", [])
                    artist_values = tags.get("artist", [])
                    album_values = tags.get("album", [])
                    if title_values:
                        title = str(title_values[0])
                    if artist_values:
                        artist = str(artist_values[0])
                    if album_values:
                        album = str(album_values[0])
                info = getattr(audio, "info", None)
                length = getattr(info, "length", None)
                if length is not None:
                    duration = self._format_track_duration(float(length))
        except (OSError, ValueError, TypeError, AttributeError):
            pass

        result = (title, artist, album, duration)
        self._metadata_cache[path] = result
        return result

    def _new_playlist(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            tr(self.language, "new_playlist"),
            tr(self.language, "playlist_name"),
        )
        name = name.strip()
        if not ok or not name:
            return
        if name in self.playlists:
            QMessageBox.information(
                self,
                tr(self.language, "playlists"),
                tr(self.language, "duplicate_playlist"),
            )
            return
        self.playlists[name] = []
        self.store.save_playlists()
        self._refresh_playlist_sidebar()
        self._select_playlist(name)

    def _rename_playlist(self, item: QListWidgetItem) -> None:
        old_name = item.data(Qt.ItemDataRole.UserRole)
        if old_name == FAVORITES_PLAYLIST:
            QMessageBox.information(
                self,
                tr(self.language, "favorites"),
                tr(self.language, "favorites_is_permanent"),
            )
            return
        new_name, ok = QInputDialog.getText(
            self,
            tr(self.language, "rename_playlist"),
            tr(self.language, "playlist_name"),
            text=old_name,
        )
        new_name = new_name.strip()
        if not ok or not new_name or new_name == old_name:
            return
        if new_name in self.playlists:
            QMessageBox.information(
                self,
                tr(self.language, "playlists"),
                tr(self.language, "duplicate_playlist"),
            )
            return
        rebuilt: dict[str, list[str]] = {}
        for name, tracks in self.playlists.items():
            rebuilt[new_name if name == old_name else name] = tracks
        self.playlists.clear()
        self.playlists.update(rebuilt)
        if self.current_playlist == old_name:
            self.current_playlist = new_name
            self.settings["last_playlist"] = new_name
        self.store.save_all()
        self._refresh_playlist_sidebar()
        self._select_playlist(self.current_playlist)

    def _delete_playlist(self) -> None:
        if len(self.playlists) <= 1:
            return
        name = self.current_playlist
        if name == FAVORITES_PLAYLIST:
            QMessageBox.information(
                self,
                tr(self.language, "favorites"),
                tr(self.language, "favorites_is_permanent"),
            )
            return
        answer = QMessageBox.question(
            self,
            tr(self.language, "delete_playlist"),
            tr(self.language, "confirm_delete_playlist", name=name),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.playlists.pop(name, None)
        self.current_playlist = next(iter(self.playlists))
        self.settings["last_playlist"] = self.current_playlist
        self.store.save_all()
        self._refresh_playlist_sidebar()
        self._select_playlist(self.current_playlist)

    def _add_files_dialog(self) -> None:
        pattern = " ".join(f"*{ext}" for ext in sorted(AUDIO_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self,
            tr(self.language, "add_files"),
            str(Path.home()),
            f"{tr(self.language, 'audio_files')} ({pattern});;{tr(self.language, 'all_files')} (*)",
        )
        self._add_paths(files)

    def _add_paths(self, paths: list[str]) -> None:
        clean: list[str] = []
        existing = set(self.playlists[self.current_playlist])
        for path in paths:
            resolved = str(Path(path).resolve())
            if (
                Path(resolved).is_file()
                and Path(resolved).suffix.lower() in AUDIO_EXTENSIONS
                and resolved not in existing
            ):
                clean.append(resolved)
                existing.add(resolved)
        if not clean:
            return
        self.playlists[self.current_playlist].extend(clean)
        for path in clean:
            self._append_track_item(path)
        self.store.save_playlists()
        self._update_empty_state()
        self._update_playlist_summary()
        self._refresh_playlist_sidebar()
        if self.settings.get("shuffle"):
            self._prepare_shuffle_cycle()
        self.statusBar().showMessage(
            tr(self.language, "tracks_added", count=len(clean)),
            3000,
        )

    def _remove_selected_tracks(self) -> None:
        rows = sorted(
            {self.track_list.row(item) for item in self.track_list.selectedItems()},
            reverse=True,
        )
        if not rows:
            return
        for row in rows:
            item = self.track_list.takeItem(row)
            removed_path = item.data(Qt.ItemDataRole.UserRole)
            if removed_path == self.current_path:
                self.backend.stop_playback()
                self.current_path = ""
                self.current_index = -1
                self.now_playing_label.setText(tr(self.language, "now_playing"))
                self.now_artist_label.clear()
                self.play_button.setIcon(
                    self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                )
            del self.playlists[self.current_playlist][row]
        self.store.save_playlists()
        self._reload_track_list()
        self._update_empty_state()
        self._update_playlist_summary()
        self._refresh_playlist_sidebar()
        self.shuffle_remaining.clear()
        self.shuffle_history.clear()
        if self.settings.get("shuffle"):
            self._prepare_shuffle_cycle()
        self._update_remove_button()

    def _reload_track_list(self) -> None:
        self.track_list.clear()
        for path in self.playlists.get(self.current_playlist, []):
            self._append_track_item(path)
        if self.current_path in self.playlists.get(self.current_playlist, []):
            self.current_index = self.playlists[self.current_playlist].index(self.current_path)
            self.track_list.setCurrentRow(self.current_index)
        else:
            self.current_index = -1

    def _save_track_order(self) -> None:
        ordered = [
            self.track_list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.track_list.count())
        ]
        self.playlists[self.current_playlist] = ordered
        self.store.save_playlists()
        if self.current_path in ordered:
            self.current_index = ordered.index(self.current_path)
        self.shuffle_remaining.clear()
        self.shuffle_history.clear()
        if self.settings.get("shuffle"):
            self._prepare_shuffle_cycle()
        self._reload_track_list()

    def _update_empty_state(self) -> None:
        if not hasattr(self, "drop_hint_label"):
            return
        empty = self.track_list.count() == 0
        base = tr(self.language, "drop_hint")
        if empty:
            text = f"{tr(self.language, 'empty_playlist')}  •  {base}"
        else:
            text = f"{base}  •  {tr(self.language, 'drag_reorder')}"
        self.drop_hint_label.setText(text)

    def _update_remove_button(self) -> None:
        self.remove_tracks_button.setEnabled(bool(self.track_list.selectedItems()))

    def _play_current_playlist(self) -> None:
        if self.track_list.count() == 0:
            return
        if self.settings.get("shuffle"):
            self._prepare_shuffle_cycle(include_current=True)
            index = self._take_next_shuffle_index()
            if index is not None:
                self._play_index(index)
            return
        selected = self.track_list.currentRow()
        self._play_index(selected if selected >= 0 else 0)

    def _play_index(self, index: int, record_shuffle_history: bool = True) -> None:
        if index < 0 or index >= self.track_list.count():
            return
        item = self.track_list.item(index)
        path = item.data(Qt.ItemDataRole.UserRole)
        if not Path(path).exists():
            QMessageBox.warning(
                self,
                tr(self.language, "playback_error"),
                tr(self.language, "file_missing", path=path),
            )
            return
        if not self.backend.available:
            self._show_mpv_missing()
            return
        if self.backend.load(path):
            if (
                record_shuffle_history
                and self.settings.get("shuffle")
                and self.current_index >= 0
                and self.current_index != index
            ):
                self.shuffle_history.append(self.current_index)
                self.shuffle_history = self.shuffle_history[-200:]
            if index in self.shuffle_remaining:
                self.shuffle_remaining.remove(index)
            self.current_index = index
            self.current_path = path
            self.duration = 0.0
            self.track_list.setCurrentRow(index)
            row_widget = self.track_list.itemWidget(item)
            if row_widget is not None:
                self.main_scroll.ensureWidgetVisible(row_widget, 0, 120)
            title, artist, _album, _duration = self._track_metadata(path)
            self.now_playing_label.setText(title)
            self.now_artist_label.setText(artist or Path(path).parent.name)
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            )
            self.play_button.setToolTip(tr(self.language, "pause"))
            QTimer.singleShot(180, self._apply_audio_filters)
        else:
            QMessageBox.warning(
                self,
                tr(self.language, "playback_error"),
                tr(self.language, "playback_error"),
            )

    def _toggle_playback(self) -> None:
        if not self.current_path:
            self._play_current_playlist()
            return
        self.backend.toggle_pause()

    def _prepare_shuffle_cycle(self, include_current: bool = False) -> None:
        count = self.track_list.count()
        indices = list(range(count))
        if not include_current and count > 1 and self.current_index in indices:
            indices.remove(self.current_index)
        random.shuffle(indices)
        self.shuffle_remaining = indices

    def _take_next_shuffle_index(self) -> int | None:
        if not self.shuffle_remaining:
            return None
        return self.shuffle_remaining.pop(0)

    def _next_track(self) -> None:
        count = self.track_list.count()
        if count == 0:
            return
        if self.settings.get("shuffle"):
            if not self.shuffle_remaining:
                self._prepare_shuffle_cycle()
            index = self._take_next_shuffle_index()
            if index is not None:
                self._play_index(index)
            return
        index = self.current_index + 1 if self.current_index >= 0 else 0
        self._play_index(index % count)

    def _previous_track(self) -> None:
        count = self.track_list.count()
        if count == 0:
            return
        if self.settings.get("shuffle") and self.shuffle_history:
            index = self.shuffle_history.pop()
            self._play_index(index, record_shuffle_history=False)
            return
        index = self.current_index - 1 if self.current_index >= 0 else count - 1
        self._play_index(index % count)

    def _stop_after_queue(self) -> None:
        self.current_path = ""
        self.current_index = -1
        self.play_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.play_button.setToolTip(tr(self.language, "play"))
        self.seek_slider.setValue(0)
        self.elapsed_label.setText("00:00")

    def _handle_track_finished(self) -> None:
        count = self.track_list.count()
        if count == 0:
            return
        repeat_mode = self.settings.get("repeat_mode", "off")
        if repeat_mode == "one" and self.current_index >= 0:
            self._play_index(self.current_index, record_shuffle_history=False)
            return
        if self.settings.get("shuffle"):
            index = self._take_next_shuffle_index()
            if index is not None:
                self._play_index(index)
                return
            if repeat_mode == "playlist":
                self._prepare_shuffle_cycle()
                index = self._take_next_shuffle_index()
                if index is not None:
                    self._play_index(index)
                    return
            self._stop_after_queue()
            return
        next_index = self.current_index + 1
        if next_index < count:
            self._play_index(next_index)
            return
        if repeat_mode == "playlist":
            self._play_index(0)
            return
        self._stop_after_queue()

    def _toggle_frequency(self, checked: bool) -> None:
        self.settings["frequency_mode"] = "432" if checked else "original"
        self.store.save_settings()
        self._apply_audio_filters()
        message_key = "frequency_on" if checked else "frequency_off"
        self.statusBar().showMessage(tr(self.language, message_key), 2500)

    def _update_frequency_switch(self) -> None:
        blocker = QSignalBlocker(self.frequency_switch)
        self.frequency_switch.setChecked(self.settings.get("frequency_mode") == "432")
        del blocker

    def _toggle_shuffle(self, checked: bool) -> None:
        self.settings["shuffle"] = bool(checked)
        self.shuffle_remaining.clear()
        self.shuffle_history.clear()
        if checked:
            self._prepare_shuffle_cycle()
        self.store.save_settings()
        message_key = "shuffle_on" if checked else "shuffle_off"
        self.statusBar().showMessage(tr(self.language, message_key), 2200)

    def _toggle_repeat_playlist(self, checked: bool) -> None:
        if checked:
            self.settings["repeat_mode"] = "playlist"
            blocker = QSignalBlocker(self.repeat_one_button)
            self.repeat_one_button.setChecked(False)
            del blocker
            message_key = "repeat_playlist_on"
        else:
            if self.settings.get("repeat_mode") == "playlist":
                self.settings["repeat_mode"] = "off"
            message_key = "repeat_off"
        self.store.save_settings()
        self.statusBar().showMessage(tr(self.language, message_key), 2200)

    def _toggle_repeat_one(self, checked: bool) -> None:
        if checked:
            self.settings["repeat_mode"] = "one"
            blocker = QSignalBlocker(self.repeat_playlist_button)
            self.repeat_playlist_button.setChecked(False)
            del blocker
            message_key = "repeat_one_on"
        else:
            if self.settings.get("repeat_mode") == "one":
                self.settings["repeat_mode"] = "off"
            message_key = "repeat_off"
        self.store.save_settings()
        self.statusBar().showMessage(tr(self.language, message_key), 2200)

    def _sync_playback_mode_buttons(self) -> None:
        shuffle_blocker = QSignalBlocker(self.shuffle_button)
        playlist_blocker = QSignalBlocker(self.repeat_playlist_button)
        one_blocker = QSignalBlocker(self.repeat_one_button)
        self.shuffle_button.setChecked(bool(self.settings.get("shuffle", False)))
        repeat_mode = self.settings.get("repeat_mode", "off")
        self.repeat_playlist_button.setChecked(repeat_mode == "playlist")
        self.repeat_one_button.setChecked(repeat_mode == "one")
        del shuffle_blocker, playlist_blocker, one_blocker

    def _apply_audio_filters(self) -> None:
        if not self.backend.available:
            return
        success = self.backend.apply_filters(
            self.settings.get("frequency_mode", "original"),
            self.settings.get("eq_gains", [0] * len(FREQUENCIES)),
        )
        if not success and self.current_path and not self._last_filter_error_shown:
            self._last_filter_error_shown = True
            self.statusBar().showMessage(
                tr(self.language, "mpv_filter_error"),
                7000,
            )

    def _open_settings(self, initial_tab: int = 0) -> None:
        dialog = SettingsDialog(
            self.settings,
            preview_theme=self.apply_theme,
            preview_eq=self._preview_equalizer,
            parent=self,
        )
        dialog.tabs.setCurrentIndex(max(0, min(initial_tab, dialog.tabs.count() - 1)))
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            return
        self.settings.clear()
        self.settings.update(deepcopy(dialog.working))
        self.store.save_settings()
        self.language = self.settings.get("language", "es")
        self.apply_theme(self.settings["theme"])
        self.retranslate_ui()
        self._sync_playback_mode_buttons()
        self._apply_audio_filters()

    def _preview_equalizer(self, gains: list[int]) -> None:
        if self.backend.available:
            self.backend.apply_filters(
                self.settings.get("frequency_mode", "original"),
                gains,
            )

    def _volume_changed(self, value: int) -> None:
        self.settings["volume"] = int(value)
        self.store.save_settings()
        if self.backend.available:
            self.backend.set_volume(value)

    def _handle_mpv_event(self, event: dict) -> None:
        event_name = event.get("event")
        if event_name == "property-change":
            name = event.get("name")
            data = event.get("data")
            if name == "time-pos" and isinstance(data, (int, float)):
                self._update_position(float(data))
            elif name == "duration" and isinstance(data, (int, float)):
                self.duration = max(0.0, float(data))
                self.total_label.setText(self._format_time(self.duration))
            elif name == "pause" and isinstance(data, bool):
                icon = (
                    QStyle.StandardPixmap.SP_MediaPlay
                    if data
                    else QStyle.StandardPixmap.SP_MediaPause
                )
                self.play_button.setIcon(self.style().standardIcon(icon))
                self.play_button.setToolTip(
                    tr(self.language, "play" if data else "pause")
                )
        elif event_name == "end-file" and event.get("reason") == "eof":
            QTimer.singleShot(80, self._handle_track_finished)

    def _update_position(self, position: float) -> None:
        if not self.dragging_seek and self.duration > 0:
            value = int((position / self.duration) * 1000)
            blocker = QSignalBlocker(self.seek_slider)
            self.seek_slider.setValue(max(0, min(1000, value)))
            del blocker
        self.elapsed_label.setText(self._format_time(position))
        self.total_label.setText(self._format_time(self.duration))

    def _preview_seek(self, value: int) -> None:
        if self.duration <= 0:
            return
        position = (value / 1000.0) * self.duration
        self.elapsed_label.setText(self._format_time(position))

    def _commit_seek(self) -> None:
        if self.duration > 0:
            self.backend.seek((self.seek_slider.value() / 1000.0) * self.duration)
        self.dragging_seek = False

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = max(0, int(seconds or 0))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return (
            f"{hours:d}:{minutes:02d}:{secs:02d}"
            if hours
            else f"{minutes:02d}:{secs:02d}"
        )

    def _backend_error(self, message: str) -> None:
        if message:
            self.statusBar().showMessage(message, 4000)

    def _show_mpv_missing(self) -> None:
        QMessageBox.critical(
            self,
            tr(self.language, "mpv_missing_title"),
            tr(self.language, "mpv_missing"),
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.store.save_all()
        self.backend.shutdown()
        event.accept()
