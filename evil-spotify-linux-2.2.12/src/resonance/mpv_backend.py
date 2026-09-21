from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from itertools import count
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from .config import FREQUENCIES


class MpvEventThread(QThread):
    event_received = Signal(dict)

    def __init__(self, socket_path: str) -> None:
        super().__init__()
        self.socket_path = socket_path
        self._stop_event = threading.Event()
        self._socket: socket.socket | None = None

    def stop(self) -> None:
        self._stop_event.set()
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._socket.close()
            except OSError:
                pass

    def run(self) -> None:
        while not self._stop_event.is_set():
            sock: socket.socket | None = None
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                sock.connect(self.socket_path)
                self._socket = sock

                observed = ["time-pos", "duration", "pause", "media-title", "path"]
                for observer_id, prop in enumerate(observed, start=100):
                    packet = {"command": ["observe_property", observer_id, prop]}
                    sock.sendall((json.dumps(packet) + "\n").encode("utf-8"))

                buffer = b""
                while not self._stop_event.is_set():
                    try:
                        data = sock.recv(65536)
                    except socket.timeout:
                        continue
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        if not line.strip():
                            continue
                        try:
                            message = json.loads(line.decode("utf-8", errors="replace"))
                        except json.JSONDecodeError:
                            continue
                        if isinstance(message, dict) and "event" in message:
                            self.event_received.emit(message)
            except OSError:
                time.sleep(0.15)
            finally:
                self._socket = None
                if sock is not None:
                    try:
                        sock.close()
                    except OSError:
                        pass


class MpvBackend(QObject):
    event_received = Signal(dict)
    backend_error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.process: subprocess.Popen[bytes] | None = None
        self.socket_path = str(Path(tempfile.gettempdir()) / f"evil-spotify-{os.getpid()}.sock")
        self._request_ids = count(1)
        self._event_thread: MpvEventThread | None = None
        self.available = shutil.which("mpv") is not None
        self.last_start_error = ""
        self.last_pitch_method = "original"

    def start(self) -> bool:
        if not self.available:
            self.last_start_error = "mpv executable was not found in PATH."
            return False

        try:
            Path(self.socket_path).unlink(missing_ok=True)
            # Keep startup options deliberately conservative so older distro
            # builds of mpv can start too. Pitch correction is managed by our
            # explicit filter chain instead of mpv's hidden automatic filter.
            args = [
                "mpv",
                "--idle=yes",
                "--no-video",
                "--audio-display=no",
                "--no-terminal",
                "--really-quiet",
                "--no-config",
                # Manage pitch correction explicitly. This prevents mpv from
                # inserting/removing an automatic scaletempo2 filter behind
                # our explicit EQ/pitch chain, which made 432 Hz unreliable
                # on some distro builds.
                "--audio-pitch-correction=no",
                "--keep-open=no",
                f"--input-ipc-server={self.socket_path}",
            ]
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            self.last_start_error = str(exc)
            self.backend_error.emit(str(exc))
            return False

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if Path(self.socket_path).exists():
                break
            if self.process.poll() is not None:
                self.last_start_error = f"mpv exited during startup with code {self.process.returncode}."
                return False
            time.sleep(0.05)
        else:
            self.last_start_error = "mpv did not create its IPC socket within 3 seconds."
            return False

        self.last_start_error = ""
        self._event_thread = MpvEventThread(self.socket_path)
        self._event_thread.event_received.connect(self.event_received)
        self._event_thread.start()
        return True

    def command(self, command: list[Any], timeout: float = 0.6) -> dict[str, Any] | None:
        if not Path(self.socket_path).exists():
            return None
        request_id = next(self._request_ids)
        payload = {"command": command, "request_id": request_id}
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect(self.socket_path)
            sock.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            buffer = b""
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                data = sock.recv(65536)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        message = json.loads(line.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        continue
                    if message.get("request_id") == request_id:
                        return message
        except (OSError, socket.timeout) as exc:
            self.backend_error.emit(str(exc))
        finally:
            sock.close()
        return None

    def load(self, path: str) -> bool:
        response = self.command(["loadfile", path, "replace"])
        return bool(response and response.get("error") == "success")

    def set_pause(self, paused: bool) -> None:
        self.command(["set_property", "pause", paused])

    def toggle_pause(self) -> None:
        self.command(["cycle", "pause"])

    def stop_playback(self) -> None:
        self.command(["stop"])

    def seek(self, seconds: float) -> None:
        self.command(["seek", max(0.0, seconds), "absolute", "exact"])

    def set_volume(self, volume: int) -> None:
        self.command(["set_property", "volume", max(0, min(100, int(volume)))])

    def _eq_filter(self, gains: list[int]) -> str | None:
        safe_gains = list(gains[: len(FREQUENCIES)])
        safe_gains.extend([0] * (len(FREQUENCIES) - len(safe_gains)))
        if not any(int(value) != 0 for value in safe_gains):
            return None

        graph = ",".join(
            f"equalizer=f={freq}:t=q:w=1:g={max(-12, min(12, int(gain)))}"
            for freq, gain in zip(FREQUENCIES, safe_gains)
        )
        return f"@resonance_eq:lavfi=[{graph}]"

    def _set_filter_chain(self, filters: list[str]) -> bool:
        # `af set` replaces only our explicit chain. Automatic pitch correction
        # is disabled at mpv startup, so there is no hidden filter for this
        # command to accidentally erase.
        chain = ",".join(filters)
        response = self.command(["af", "set", chain])
        return bool(response and response.get("error") == "success")

    def _get_numeric_property(self, name: str) -> float | None:
        response = self.command(["get_property", name])
        if not response or response.get("error") != "success":
            return None
        value = response.get("data")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def apply_filters(self, frequency_mode: str, gains: list[int]) -> bool:
        """Apply 432 Hz pitch shifting and the user EQ deterministically.

        v2.2.3-v2.2.5 relied on mpv's automatic `pitch` implementation. On
        some distro builds the IPC property reported success while the auto
        correction filter was not left in the effective chain, so the switch
        could visually say 432 Hz while playback remained at the original
        pitch.

        This version does not rely on that hidden filter. For 432 Hz it first
        tries Rubber Band R3 (`engine=finer`) explicitly. R3 is much cleaner
        than the R2/default path that caused the earlier robotic sound. If R3
        is not available, it falls back to mpv's long-supported `scaletempo`
        pitch mode and uses the speed property only as the pitch control; the
        filter keeps the audible tempo unchanged.
        """
        pitch_scale = 432.0 / 440.0
        eq_filter = self._eq_filter(gains)

        # Always reset the speed control first. This is important when moving
        # from the compatibility path back to original tuning or to R3.
        speed_reset = self.command(["set_property", "speed", 1.0])
        if not speed_reset or speed_reset.get("error") != "success":
            self.last_pitch_method = "error"
            return False

        if frequency_mode != "432":
            filters = [eq_filter] if eq_filter else []
            ok = self._set_filter_chain(filters)
            if ok:
                self.last_pitch_method = "original"
            return ok

        # Preferred path: explicit Rubber Band R3. By forcing `engine=finer`
        # we avoid the older R2 engine that can sound metallic/robotic.
        r3_pitch = (
            "@resonance_pitch:rubberband="
            f"pitch-scale={pitch_scale:.12f}:engine=finer"
        )
        r3_filters = [r3_pitch]
        if eq_filter:
            r3_filters.append(eq_filter)
        if self._set_filter_chain(r3_filters):
            self.last_pitch_method = "rubberband-r3"
            return True

        # Compatibility path: scaletempo's speed=pitch mode is available on
        # older mpv builds. In this mode changing `speed` changes pitch while
        # the filter compensates the tempo, so duration/playback tempo stays
        # effectively normal. This makes the 432/440 ratio explicit instead
        # of depending on mpv's automatic pitch filter.
        compat_pitch = (
            "@resonance_pitch:scaletempo="
            "speed=pitch:stride=60:overlap=0.20:search=14"
        )
        compat_filters = [compat_pitch]
        if eq_filter:
            compat_filters.append(eq_filter)

        if not self._set_filter_chain(compat_filters):
            self.command(["set_property", "speed", 1.0])
            self.last_pitch_method = "error"
            return False

        speed_response = self.command(["set_property", "speed", pitch_scale])
        if not speed_response or speed_response.get("error") != "success":
            self.command(["set_property", "speed", 1.0])
            self.last_pitch_method = "error"
            return False

        # Verify that mpv actually retained the ratio. This catches the exact
        # failure mode seen in the previous releases instead of reporting a
        # false success to the UI.
        effective_speed = self._get_numeric_property("speed")
        if effective_speed is None or abs(effective_speed - pitch_scale) > 0.0005:
            self.command(["set_property", "speed", 1.0])
            self.last_pitch_method = "error"
            return False

        self.last_pitch_method = "scaletempo-compat"
        return True

    def shutdown(self) -> None:
        if self._event_thread is not None:
            self._event_thread.stop()
            self._event_thread.wait(1000)
            self._event_thread = None

        if self.process is not None and self.process.poll() is None:
            self.command(["quit"], timeout=0.2)
            try:
                self.process.wait(timeout=0.8)
            except subprocess.TimeoutExpired:
                self.process.terminate()
        self.process = None
        Path(self.socket_path).unlink(missing_ok=True)
