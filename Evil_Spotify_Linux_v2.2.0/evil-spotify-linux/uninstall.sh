#!/usr/bin/env bash
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
ICON_THEME_ROOT="$DATA_HOME/icons/hicolor"

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

rm -rf "$DATA_HOME/evil-spotify"
rm -f "$HOME/.local/bin/evil-spotify"
rm -f "$DATA_HOME/applications/evil-spotify.desktop"
rm -f "$ICON_THEME_ROOT/256x256/apps/evil-spotify.png"
rm -f "$DATA_HOME/pixmaps/evil-spotify.png"
rm -f "$(resolve_desktop_dir)/Evil Spotify.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$ICON_THEME_ROOT" >/dev/null 2>&1 || true
fi

echo "Evil Spotify removed. User settings remain in ~/.config/evil-spotify"
echo "Evil Spotify eliminado. Los ajustes permanecen en ~/.config/evil-spotify"
