#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_HOME/evil-spotify"
BIN_DIR="$HOME/.local/bin"
DESKTOP_APPS_DIR="$DATA_HOME/applications"
ICON_THEME_ROOT="$DATA_HOME/icons/hicolor"
ICON_DIR="$ICON_THEME_ROOT/256x256/apps"
PIXMAP_DIR="$DATA_HOME/pixmaps"
DESKTOP_FILE="$DESKTOP_APPS_DIR/evil-spotify.desktop"

python_venv_is_usable() {
  command -v python3 >/dev/null 2>&1 || return 1

  local check_dir
  check_dir="$(mktemp -d)"
  if ! python3 -m venv "$check_dir/venv" >/dev/null 2>&1; then
    rm -rf "$check_dir"
    return 1
  fi

  if ! "$check_dir/venv/bin/python" -m pip --version >/dev/null 2>&1; then
    rm -rf "$check_dir"
    return 1
  fi

  rm -rf "$check_dir"
  return 0
}

install_system_dependencies() {
  if command -v mpv >/dev/null 2>&1 && python_venv_is_usable; then
    return
  fi

  echo "Installing system dependencies / Instalando dependencias del sistema..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip mpv librubberband2
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip mpv rubberband
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed python python-pip mpv rubberband
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y python3 python3-pip python3-virtualenv mpv rubberband
  else
    echo "Install Python 3, pip, venv, mpv and Rubber Band with your package manager." >&2
    echo "Instala Python 3, pip, venv, mpv y Rubber Band con el gestor de paquetes de tu distribución." >&2
    exit 1
  fi

  if ! python_venv_is_usable; then
    echo "Python venv is still unavailable / El entorno virtual de Python sigue sin estar disponible." >&2
    exit 1
  fi
}

resolve_desktop_dir() {
  local candidate=""

  if command -v xdg-user-dir >/dev/null 2>&1; then
    candidate="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  fi

  # Some minimal desktops return HOME or nothing when XDG folders are not set.
  if [[ -z "$candidate" || "$candidate" == "$HOME" ]]; then
    if [[ -d "$HOME/Escritorio" ]]; then
      candidate="$HOME/Escritorio"
    else
      candidate="$HOME/Desktop"
    fi
  fi

  printf '%s\n' "$candidate"
}

refresh_desktop_caches() {
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_APPS_DIR" >/dev/null 2>&1 || true
  fi

  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICON_THEME_ROOT" >/dev/null 2>&1 || true
  fi
}

install_system_dependencies
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_APPS_DIR" "$ICON_DIR" "$PIXMAP_DIR"

if [[ "$ROOT" != "$APP_DIR" ]]; then
  rm -rf "$APP_DIR"
  mkdir -p "$APP_DIR"
  cp -a "$ROOT/." "$APP_DIR/"
fi

# Never copy or reuse a venv created in another path or with missing pip.
rm -rf "$APP_DIR/.venv"
find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +

cat > "$BIN_DIR/evil-spotify" <<LAUNCHER
#!/usr/bin/env bash
exec "$APP_DIR/run.sh" "\$@"
LAUNCHER
chmod +x "$BIN_DIR/evil-spotify" "$APP_DIR/run.sh" "$APP_DIR/uninstall.sh"

# Install the icon both in the freedesktop hicolor theme and in pixmaps.
# The desktop entry also uses the absolute installed path as a reliable fallback.
cp -f "$APP_DIR/assets/evil-spotify.png" "$ICON_DIR/evil-spotify.png"
cp -f "$APP_DIR/assets/evil-spotify.png" "$PIXMAP_DIR/evil-spotify.png"
chmod 644 "$ICON_DIR/evil-spotify.png" "$PIXMAP_DIR/evil-spotify.png"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Evil Spotify
GenericName=Music Player
GenericName[es]=Reproductor de música
Comment=Local music player with optional 432 Hz tuning
Comment[es]=Reproductor de música local con afinación opcional a 432 Hz
Exec=$BIN_DIR/evil-spotify %U
TryExec=$BIN_DIR/evil-spotify
Icon=$ICON_DIR/evil-spotify.png
Terminal=false
Categories=AudioVideo;Audio;Player;
MimeType=audio/mpeg;audio/flac;audio/x-wav;audio/ogg;audio/aac;audio/mp4;
StartupNotify=true
StartupWMClass=evil-spotify
Keywords=music;audio;player;playlist;432hz;
Keywords[es]=música;audio;reproductor;playlist;432hz;
DESKTOP
chmod 755 "$DESKTOP_FILE"

# Create an actual desktop shortcut in the localized XDG Desktop folder.
USER_DESKTOP_DIR="$(resolve_desktop_dir)"
mkdir -p "$USER_DESKTOP_DIR"
DESKTOP_SHORTCUT="$USER_DESKTOP_DIR/Evil Spotify.desktop"
cp -f "$DESKTOP_FILE" "$DESKTOP_SHORTCUT"
chmod +x "$DESKTOP_SHORTCUT"

# GNOME and some other desktops need the launcher to be marked as trusted.
if command -v gio >/dev/null 2>&1; then
  gio set "$DESKTOP_SHORTCUT" metadata::trusted true >/dev/null 2>&1 || true
fi

refresh_desktop_caches

echo
printf 'Installed successfully. Launch "Evil Spotify" from your app menu or desktop shortcut.\n'
printf 'Instalado correctamente. Abre "Evil Spotify" desde el menú o el acceso directo del escritorio.\n'
printf 'Desktop shortcut / Acceso directo: %s\n' "$DESKTOP_SHORTCUT"
