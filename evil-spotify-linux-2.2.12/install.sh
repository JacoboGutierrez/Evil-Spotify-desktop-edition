#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# This installer intentionally follows the simple per-user installation flow
# used by Evil Spotify 2.2.1, which is known to launch correctly on Ubuntu.
# If the script was started with sudo, immediately return to the real desktop
# user so HOME, XDG paths and GNOME launcher metadata are not created as root.
if [[ "${EUID:-$(id -u)}" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  TARGET_USER="$SUDO_USER"
  TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
  TARGET_UID="$(id -u "$TARGET_USER")"
  TARGET_RUNTIME_DIR="/run/user/$TARGET_UID"
  TARGET_DBUS="unix:path=$TARGET_RUNTIME_DIR/bus"

  exec sudo -u "$TARGET_USER" env \
    HOME="$TARGET_HOME" \
    USER="$TARGET_USER" \
    LOGNAME="$TARGET_USER" \
    XDG_RUNTIME_DIR="$TARGET_RUNTIME_DIR" \
    DBUS_SESSION_BUS_ADDRESS="$TARGET_DBUS" \
    bash "$0" "$@"
fi

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
    sudo apt-get install -y python3 python3-venv python3-pip mpv
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip mpv
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed python python-pip mpv
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y python3 python3-pip python3-virtualenv mpv
  else
    echo "Install Python 3, pip, venv and mpv with your package manager." >&2
    echo "Instala Python 3, pip, venv y mpv con el gestor de paquetes de tu distribución." >&2
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

remove_old_user_launchers() {
  # Remove only Evil Spotify launchers. Do not touch ~/.config/evil-spotify.
  rm -f "$HOME/.local/share/applications/evil-spotify.desktop" \
        "$HOME/.local/share/applications/evil_spotify.desktop" \
        "$HOME/.local/bin/evil_spotify"

  for desktop_dir in "$HOME/Desktop" "$HOME/Escritorio"; do
    [[ -d "$desktop_dir" ]] || continue
    find "$desktop_dir" -maxdepth 1 -type f \( -iname '*evil*spotify*.desktop' -o -iname 'evil-spotify.desktop' \) -delete 2>/dev/null || true
  done
}

install_system_dependencies
remove_old_user_launchers
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_APPS_DIR" "$ICON_DIR" "$PIXMAP_DIR"

# Replace only the installed application. User playlists/settings live in
# ~/.config/evil-spotify and are deliberately left untouched.
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -a "$ROOT/." "$APP_DIR/"

# Match the working 2.2.1 behavior: do not copy/reuse a virtual environment
# from the extracted package. run.sh creates it in the installed location.
rm -rf "$APP_DIR/.venv"
find "$APP_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +

# Direct launcher, exactly like the reliable 2.2.1 chain:
# .desktop -> ~/.local/bin/evil-spotify -> installed run.sh
cat > "$BIN_DIR/evil-spotify" <<LAUNCHER
#!/usr/bin/env bash
exec "$APP_DIR/run.sh" "\$@"
LAUNCHER
chmod +x "$BIN_DIR/evil-spotify" "$APP_DIR/run.sh" "$APP_DIR/uninstall.sh"

cp -f "$APP_DIR/assets/evil-spotify.png" "$ICON_DIR/evil-spotify.png"
cp -f "$APP_DIR/assets/evil-spotify.png" "$PIXMAP_DIR/evil-spotify.png"
chmod 644 "$ICON_DIR/evil-spotify.png" "$PIXMAP_DIR/evil-spotify.png"

# Use the same desktop-entry pattern that worked in 2.2.1: direct Exec and
# TryExec to the Evil Spotify launcher, plus an absolute icon path.
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
X-EvilSpotify-Version=2.2.12
Terminal=false
Categories=AudioVideo;Audio;Player;
MimeType=audio/mpeg;audio/flac;audio/x-wav;audio/ogg;audio/aac;audio/mp4;
StartupNotify=true
StartupWMClass=evil-spotify
Keywords=music;audio;player;playlist;432hz;
Keywords[es]=música;audio;reproductor;playlist;432hz;
DESKTOP
chmod 755 "$DESKTOP_FILE"

USER_DESKTOP_DIR="$(resolve_desktop_dir)"
mkdir -p "$USER_DESKTOP_DIR"
DESKTOP_SHORTCUT="$USER_DESKTOP_DIR/Evil Spotify.desktop"
cp -f "$DESKTOP_FILE" "$DESKTOP_SHORTCUT"
chmod +x "$DESKTOP_SHORTCUT"

# Same trust mechanism used by 2.2.1. Ubuntu may still ask once for
# "Allow Launching" depending on the desktop-icons extension/settings.
if command -v gio >/dev/null 2>&1; then
  gio set "$DESKTOP_SHORTCUT" metadata::trusted true >/dev/null 2>&1 || true
fi

refresh_desktop_caches

echo
printf 'Installed Evil Spotify v2.2.12 successfully.\n'
printf 'Evil Spotify v2.2.12 instalado correctamente.\n'
printf 'Application / Aplicación: %s\n' "$APP_DIR"
printf 'Launcher: %s\n' "$BIN_DIR/evil-spotify"
printf 'Desktop shortcut / Acceso directo: %s\n' "$DESKTOP_SHORTCUT"
printf 'Your playlists remain in / Tus playlists permanecen en: %s\n' "$HOME/.config/evil-spotify"
