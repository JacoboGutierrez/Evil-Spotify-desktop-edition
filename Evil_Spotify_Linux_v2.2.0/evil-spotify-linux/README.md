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
