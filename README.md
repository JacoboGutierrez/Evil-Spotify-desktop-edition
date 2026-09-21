<p align="center">
  <img
    src="https://github.com/JacoboGutierrez/JacoboGutierrez/blob/main/evil-spoty01.png?raw=true"
    alt="Evil Spotify Demonstration"
  />
</p>

# Evil Spotify for Linux

**Version 2.2.12**

Local music player for Linux built with **Python, PySide6, and mpv**. It uses a dark interface inspired by modern players, featuring red as the default accent color and a fully customizable theme.

## Features

- Playback with original tuning or optional conversion to **432 Hz** without modifying speed.
- Song table with **title, artist, album, and duration** extracted from file metadata.
- Full-body vertical scrolling: header, cover art, controls, and songs move together.
- Thin line-shaped scrollbar that adopts the theme's accent color.
- 10-band equalizer, from -12 dB to +12 dB.
- Creation, saving, and deletion of equalization presets.
- Permanent **Favorites** playlist, automatically created.
- Interactive heart between the track number and song title: the outline appears on hover, and the red heart stays visible when the song is favorited.
- Tagged songs automatically sync with the Favorites playlist from any playlist.
- Persistent playlists: create, double-click to rename, and delete.
- Drag and drop songs or folders from the file manager into the current playlist.
- Reorder songs by dragging them within the list.
- Shuffle playback without repeating songs within the same cycle.
- Repeat the entire playlist.
- Single repeat for the current song.
- Preset themes and fully customizable colors.
- Default Evil Red palette: background `#090909`, panel `#101010`, secondary panel `#1B1B1B`, accent `#F5000F`, text `#F7F7F7`, and muted text `#A8A8A8`.
- Theme, Language, and Preset dropdowns with Panel background and Secondary Panel highlight.
- Spanish and English interface.
- Automatic saving in `~/.config/evil-spotify/`.
- Automatic import of previous data from `~/.config/resonance-player/` when applicable.

## Recommended Installation

Open a terminal in this folder and run:

```bash
chmod +x install.sh
./install.sh
```

The installer supports Debian/Ubuntu, Fedora, Arch, and openSUSE. Afterward, you can open **Evil Spotify** from your applications menu or from the shortcut created in `Desktop`/`Escritorio`.

To update a previous installation, run `./install.sh` again. Your playlists, themes, and presets will be preserved.

## Run Without Installing

```bash
chmod +x run.sh
./run.sh
```

`run.sh` automatically creates a virtual environment and installs PySide6 and Mutagen. If it finds an incomplete `.venv` environment or one without `pip`, it deletes and rebuilds it.

## System Dependencies

- Python 3.10 or higher.
- Support for `venv` and `pip`.
- `mpv` compiled with Rubber Band/FFmpeg support.
- Rubber Band.

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip mpv librubberband2
```

On Fedora:

```bash
sudo dnf install python3 python3-pip mpv rubberband
```

On Arch Linux:

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

Current versions detect and repair this case automatically.

## How 432 Hz Works

When the switch is enabled, the program uses the pitch factor:

```text
432 / 440 = 0.981818...
```

The Rubber Band filter modifies the pitch while keeping the song's original duration and speed.

## Shortcuts

- `Space`: Play or pause.
- `Ctrl+O`: Add songs.
- `Delete`: Remove selected songs from the playlist.

## Uninstallation

```bash
./uninstall.sh
```

Uninstallation preserves your playlists and preferences. To delete them as well:

```bash
rm -rf ~/.config/evil-spotify
```
- Automatic update of application and icon caches.
- Creation of an executable shortcut in the user's desktop folder.

---

# Evil Spotify para Linux

**Versión 2.2.12**

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

In Arch Linux:

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
- Actualización automática de las cachés de aplicaciones e iconos.
- Creación de un acceso directo ejecutable en la carpeta de escritorio del usuario.
