#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PYTHON="$VENV/bin/python"

print_venv_help() {
  cat >&2 <<'HELP'

Could not create a Python virtual environment with pip.
No se pudo crear un entorno virtual de Python con pip.

Install the required package for your Linux distribution, then run this script again:
Instala el paquete necesario para tu distribución y vuelve a ejecutar este script:

  Debian / Ubuntu / Linux Mint:
    sudo apt update && sudo apt install python3-venv python3-pip

  Fedora:
    sudo dnf install python3-pip

  Arch Linux / Manjaro:
    sudo pacman -S python-pip

  openSUSE:
    sudo zypper install python3-pip python3-virtualenv
HELP
}

create_clean_venv() {
  echo "Preparing Python environment / Preparando el entorno de Python..."
  rm -rf "$VENV"

  if ! python3 -m venv "$VENV"; then
    rm -rf "$VENV"
    print_venv_help
    exit 1
  fi

  # Some distributions can leave a partially-created venv without pip.
  if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    "$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
  fi

  if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    rm -rf "$VENV"
    print_venv_help
    exit 1
  fi
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required / Se requiere Python 3." >&2
  exit 1
fi

if ! command -v mpv >/dev/null 2>&1; then
  echo "mpv is required / Se requiere mpv." >&2
  echo "Debian/Ubuntu: sudo apt install mpv librubberband2" >&2
  exit 1
fi

# Rebuild missing, broken, copied, or incomplete virtual environments.
if [[ ! -x "$PYTHON" ]] || ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
  create_clean_venv
fi

if ! "$PYTHON" -c 'import PySide6, mutagen' >/dev/null 2>&1; then
  echo "Installing Python dependencies / Instalando dependencias de Python..."
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r "$ROOT/requirements.txt"
fi

exec "$PYTHON" "$ROOT/src/main.py" "$@"
