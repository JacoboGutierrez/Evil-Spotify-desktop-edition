# Evil Spotify for Linux

**Version 2.2.0**

A local music player for Linux built with **Python, PySide6, and mpv**. It features a modern dark interface with red as the default accent color, while allowing the entire theme to be customized.

## Features

- Original tuning playback or optional conversion to **432 Hz** without changing playback speed.
- Song table displaying **title, artist, album, and duration** from the file metadata.
- Full-body vertical scrolling: the header, artwork, controls, and song list move together.
- A thin line-style scrollbar that automatically uses the selected theme accent color.
- 10-band equalizer ranging from -12 dB to +12 dB.
- Create, save, and delete equalizer presets.
- Permanent **Favorites** playlist created automatically.
- Interactive heart button between the track number and title: an outline appears on hover, while favorited songs always display a filled red heart.
- Songs marked as favorites are automatically synchronized with the Favorites playlist from any playlist.
- Persistent playlists with support for creating, deleting, and renaming them by double-clicking.
- Drag songs or entire folders from the file manager into the current playlist.
- Reorder songs by dragging them within the track list.
- Shuffle playback without repeating songs during the same cycle.
- Repeat the entire playlist.
- Repeat the current song.
- Built-in themes and fully customizable colors.
- Default Evil Red palette:
  - Background: `#090909`
  - Panel: `#101010`
  - Secondary panel: `#1B1B1B`
  - Accent: `#F5000F`
  - Text: `#F7F7F7`
  - Muted text: `#A8A8A8`
- Theme, Language, and Preset dropdowns use the Panel color as their background and the Secondary Panel color for hovered or selected options.
- English and Spanish interface languages.
- Automatic settings storage in `~/.config/evil-spotify/`.
- Automatic import of compatible data from `~/.config/resonance-player/` when available.

## Recommended Installation

Open a terminal in this folder and run:

```bash
chmod +x install.sh
./install.sh
```

The installer supports Debian/Ubuntu, Fedora, Arch Linux, and openSUSE. After installation, you can launch **Evil Spotify** from the applications menu or from the shortcut created in your `Desktop` folder.

To update an existing installation, run `./install.sh` again. Your playlists, themes, presets, and preferences will be preserved.

## Run Without Installing

```bash
chmod +x run.sh
./run.sh
```

`run.sh` automatically creates a Python virtual environment and installs PySide6 and Mutagen. If it finds an incomplete `.venv` environment or one without `pip`, it removes and rebuilds it automatically.

## System Dependencies

- Python 3.10 or newer.
- Python `venv` and `pip` support.
- `mpv` with Rubber Band/FFmpeg filter support.
- Rubber Band.

### Debian/Ubuntu

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip mpv librubberband2
```

### Fedora

```bash
sudo dnf install python3 python3-pip mpv rubberband
```

### Arch Linux

```bash
sudo pacman -S python python-pip mpv rubberband
```

## Repair an Incomplete Virtual Environment

```bash
rm -rf .venv
sudo apt update
sudo apt install python3-venv python3-pip
./run.sh
```

Current versions detect and repair this situation automatically.

## How 432 Hz Mode Works

When the 432 Hz switch is enabled, the player uses this pitch factor:

```text
432 / 440 = 0.981818...
```

The Rubber Band filter changes the pitch while preserving the original song duration and playback speed.

## Keyboard Shortcuts

- `Space`: Play or pause.
- `Ctrl+O`: Add songs.
- `Delete`: Remove the selected songs from the current playlist.

## Uninstallation

```bash
./uninstall.sh
```

Uninstalling the application preserves your playlists and preferences. To remove them as well:

```bash
rm -rf ~/.config/evil-spotify
```

## Version 2.2.0 Changes

- Added the new default Evil Red color palette.
- Theme, Language, and Preset dropdowns now correctly follow the dark theme, including on Linux desktop environments that render popup menus in separate windows.
- Added the permanent `Favorites` playlist.
- Added a per-song heart button between the track number and title, without an extra column label.
- The empty heart appears only when hovering over a song that is not yet a favorite.
- The filled heart remains permanently visible in red for favorited songs.
- Marking or unmarking a song immediately updates the Favorites playlist and its sidebar counter.
- The Favorites playlist cannot be accidentally renamed or deleted.

## Version 2.1.1 Fixes

- Fixed `Could not parse stylesheet of object ColorButton` warnings.
- Added automatic validation of stored colors before applying them.
- Added icon installation to the `hicolor` theme and `pixmaps` directory.
- Added automatic refresh of application and icon caches.
- Added creation of an executable desktop shortcut in the user's Desktop folder.

<hr>

# Español: #

# Evil Spotify para Linux

**Versión 2.2.0**

Reproductor de música local para Linux construido con **Python, PySide6 y mpv**. Utiliza una interfaz oscura inspirada en reproductores modernos, con rojo como color de acento predeterminado y el tema completamente personalizable.

## Funciones

- Reproducción con afinación original o conversión opcional a **432 Hz** sin modificar la velocidad.
- Tabla de canciones con **título, artista, álbum y duración** obtenidos de los metadatos del archivo.
- Desplazamiento vertical del cuerpo completo: cabecera, portada, controles y canciones se mueven juntos.
- Barra de desplazamiento fina en forma de línea que adopta el color de acento del tema.
- Ecualizador de 10 bandas, de -12 dB a +12 dB.
- Creación, guardado y eliminación de presets de ecualización.
- Playlist permanente **Favoritos**, creada automáticamente.
- Corazón interactivo entre el número y el título de cada canción: el contorno aparece al pasar el mouse y el corazón rojo queda visible cuando la canción es favorita.
- Las canciones marcadas se sincronizan automáticamente con la playlist Favoritos desde cualquier playlist.
- Playlists persistentes: crear, renombrar con doble clic y eliminar.
- Arrastrar canciones o carpetas desde el explorador de archivos a la playlist actual.
- Reordenar canciones arrastrándolas dentro de la lista.
- Reproducción aleatoria sin repetir canciones dentro del mismo ciclo.
- Repetición de la playlist completa.
- Repetición individual de la canción actual.
- Temas predefinidos y colores completamente personalizables.
- Paleta Evil Red predeterminada: fondo `#090909`, panel `#101010`, panel secundario `#1B1B1B`, acento `#F5000F`, texto `#F7F7F7` y texto tenue `#A8A8A8`.
- Desplegables de Tema, Idioma y Preset con fondo del Panel y resaltado del Panel secundario.
- Interfaz en español e inglés.
- Guardado automático en `~/.config/evil-spotify/`.
- Importación automática de datos anteriores desde `~/.config/resonance-player/` cuando corresponde.

## Instalación recomendada

Abre una terminal en esta carpeta y ejecuta:

```bash
chmod +x install.sh
./install.sh
```

El instalador admite Debian/Ubuntu, Fedora, Arch y openSUSE. Después podrás abrir **Evil Spotify** desde el menú de aplicaciones o desde el acceso directo creado en `Escritorio`/`Desktop`.

Para actualizar una instalación anterior, ejecuta nuevamente `./install.sh`. Tus playlists, temas y presets se conservan.

## Ejecutar sin instalar

```bash
chmod +x run.sh
./run.sh
```

`run.sh` crea automáticamente un entorno virtual e instala PySide6 y Mutagen. Si encuentra un entorno `.venv` incompleto o sin `pip`, lo elimina y lo reconstruye.

## Dependencias del sistema

- Python 3.10 o superior.
- Soporte para `venv` y `pip`.
- `mpv` compilado con soporte para Rubber Band/FFmpeg.
- Rubber Band.

En Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip mpv librubberband2
```

En Fedora:

```bash
sudo dnf install python3 python3-pip mpv rubberband
```

En Arch Linux:

```bash
sudo pacman -S python python-pip mpv rubberband
```

## Reparar un entorno virtual incompleto

```bash
rm -rf .venv
sudo apt update
sudo apt install python3-venv python3-pip
./run.sh
```

Las versiones actuales detectan y reparan este caso automáticamente.

## Cómo funciona 432 Hz

Cuando el switch está activado, el programa utiliza el factor de tono:

```text
432 / 440 = 0.981818...
```

El filtro Rubber Band modifica el tono manteniendo la duración y la velocidad original de la canción.

## Atajos

- `Espacio`: reproducir o pausar.
- `Ctrl+O`: agregar canciones.
- `Supr`: quitar canciones seleccionadas de la playlist.

## Desinstalación

```bash
./uninstall.sh
```

La desinstalación conserva tus playlists y preferencias. Para borrarlas también:

```bash
rm -rf ~/.config/evil-spotify
```


## Cambios de la versión 2.2.0

- Nueva paleta Evil Red predeterminada solicitada.
- Los desplegables de Tema, Idioma y Preset respetan el tema oscuro, incluso en escritorios Linux que renderizan el popup en una ventana separada.
- Se agrega automáticamente la playlist permanente `Favoritos`.
- Corazón por canción ubicado entre el número y el título, sin encabezado adicional.
- El corazón vacío aparece solamente al hacer hover sobre una canción no favorita.
- El corazón lleno permanece visible en rojo para todas las canciones favoritas.
- Marcar o desmarcar una canción actualiza inmediatamente la playlist Favoritos y el contador lateral.
- Favoritos no puede renombrarse ni eliminarse accidentalmente.


## Correcciones de la versión 2.1.1

- Corregidos los avisos `Could not parse stylesheet of object ColorButton`.
- Validación automática de los colores guardados antes de aplicarlos.
- Instalación del icono en el tema `hicolor` y en `pixmaps`.
- Actualización automática de las cachés de aplicaciones e iconos.
- Creación de un acceso directo ejecutable en la carpeta de escritorio del usuario.
