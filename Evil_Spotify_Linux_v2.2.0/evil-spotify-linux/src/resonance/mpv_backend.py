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

    def start(self) -> bool:
        if not self.available:
            return False

        try:
            Path(self.socket_path).unlink(missing_ok=True)
            args = [
                "mpv",
                "--idle=yes",
                "--no-video",
                "--audio-display=no",
                "--no-terminal",
                "--really-quiet",
                "--no-config",
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
            self.backend_error.emit(str(exc))
            return False

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if Path(self.socket_path).exists():
                break
            if self.process.poll() is not None:
                return False
            time.sleep(0.05)
        else:
            return False

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

    def apply_filters(self, frequency_mode: str, gains: list[int]) -> bool:
        filters: list[str] = []
        pitch_scale = 432.0 / 440.0 if frequency_mode == "432" else 1.0

        if abs(pitch_scale - 1.0) > 0.000001:
            filters.append(f"@resonance_pitch:rubberband=pitch-scale={pitch_scale:.9f}")

        safe_gains = list(gains[: len(FREQUENCIES)])
        safe_gains.extend([0] * (len(FREQUENCIES) - len(safe_gains)))
        if any(int(value) != 0 for value in safe_gains):
            graph = ",".join(
                f"equalizer=f={freq}:t=q:w=1:g={max(-12, min(12, int(gain)))}"
                for freq, gain in zip(FREQUENCIES, safe_gains)
            )
            filters.append(f"@resonance_eq:lavfi=[{graph}]")

        if filters:
            response = self.command(["af", "set", ",".join(filters)])
        else:
            response = self.command(["af", "clr", ""])
        return bool(response and response.get("error") == "success")

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
