#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  TARGET_USER="$SUDO_USER"
  TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
else
  TARGET_USER="$(id -un)"
  TARGET_HOME="$HOME"
fi

DATA_HOME="$TARGET_HOME/.local/share"
ICON_THEME_ROOT="$DATA_HOME/icons/hicolor"

run_as_target_user() {
  if [[ "$(id -un)" == "$TARGET_USER" ]]; then
    HOME="$TARGET_HOME" "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -u "$TARGET_USER" env HOME="$TARGET_HOME" "$@"
  else
    "$@"
  fi
}

resolve_desktop_dir() {
  local candidate=""
  if command -v xdg-user-dir >/dev/null 2>&1; then
    candidate="$(run_as_target_user xdg-user-dir DESKTOP 2>/dev/null || true)"
  fi
  if [[ -z "$candidate" || "$candidate" == "$TARGET_HOME" ]]; then
    if [[ -d "$TARGET_HOME/Escritorio" ]]; then
      candidate="$TARGET_HOME/Escritorio"
    else
      candidate="$TARGET_HOME/Desktop"
    fi
  fi
  printf '%s\n' "$candidate"
}

rm -rf "$DATA_HOME/evil-spotify"
rm -f "$TARGET_HOME/.local/bin/evil-spotify"
rm -f "$DATA_HOME/applications/evil-spotify.desktop"
rm -f "$ICON_THEME_ROOT/256x256/apps/evil-spotify.png"
rm -f "$DATA_HOME/pixmaps/evil-spotify.png"
rm -f "$(resolve_desktop_dir)/Evil Spotify.desktop"
rm -f "$TARGET_HOME/Desktop/Evil Spotify.desktop" "$TARGET_HOME/Escritorio/Evil Spotify.desktop"

# Remove any other per-user .desktop entry that explicitly identifies itself
# as Evil Spotify. This cleans launchers left by pre-2.2.8 releases.
for dir in "$DATA_HOME/applications" "$TARGET_HOME/Desktop" "$TARGET_HOME/Escritorio"; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r -d '' file; do
    if grep -qiE '^(Name=Evil Spotify|Exec=.*evil[- ]spotify|X-EvilSpotify-Version=)' "$file" 2>/dev/null; then
      rm -f "$file"
    fi
  done < <(find "$dir" -maxdepth 1 -type f -name '*.desktop' -print0 2>/dev/null)
done

# Clean accidental root-level files left by v2.2.3 and older when uninstall.sh
# was run with sudo.
if [[ "${EUID:-$(id -u)}" -eq 0 && -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
  rm -rf /root/.local/share/evil-spotify
  rm -f /root/.local/bin/evil-spotify
  rm -f /root/.local/share/applications/evil-spotify.desktop
  rm -f /root/.local/share/icons/hicolor/256x256/apps/evil-spotify.png
  rm -f /root/.local/share/pixmaps/evil-spotify.png
  rm -f "/root/Desktop/Evil Spotify.desktop" "/root/Escritorio/Evil Spotify.desktop"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  run_as_target_user update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  run_as_target_user gtk-update-icon-cache -f -t "$ICON_THEME_ROOT" >/dev/null 2>&1 || true
fi

echo "Evil Spotify removed for $TARGET_USER. User settings remain in $TARGET_HOME/.config/evil-spotify"
echo "Evil Spotify eliminado para $TARGET_USER. Los ajustes permanecen en $TARGET_HOME/.config/evil-spotify"
