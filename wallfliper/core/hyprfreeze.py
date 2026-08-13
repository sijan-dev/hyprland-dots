"""Freeze the live wallpaper while any window is open (Hyprland).

A detached, event-driven companion to mpvpaper: it subscribes to Hyprland's
event socket and SIGSTOPs/SIGCONTs the target mpvpaper PID whenever the active
workspace gains or loses its last window. SIGSTOP frees the whole process
(0% CPU) and freezes mpv's frame cleanly; resume continues from the same
position because wallfliper runs mpv --no-audio (free-run timing, nothing to
catch up to).

A timeout-gated read re-syncs on a timer even when no event arrives, and an
unreadable window count resumes the wallpaper rather than leaving it frozen —
a missed event can never strand the video stuck. On failure the wallpaper is
always resumed, never left frozen.

Runs as a plain script: `python core/hyprfreeze.py <mpvpaper_pid>`.
Hyprland only — exits immediately elsewhere. Stdlib only.
"""

from __future__ import annotations

import json
import os
import select
import shutil
import signal
import socket
import subprocess
import sys
import time

# Re-sync even when no layout event arrives, so a single missed or mishandled
# event can never strand the wallpaper frozen: at most this many seconds of
# stale freeze state can persist.
_RESYNC_INTERVAL_S = 5.0
# Transient hyprctl failures (compositor busy, IPC hiccup) are retried before
# the count is treated as unknown.
_WINDOW_COUNT_RETRIES = 3
_WINDOW_COUNT_RETRY_DELAY_S = 0.05

# Events that can change the active workspace's window count. Hyprland emits
# `v2`-suffixed variants of several of these; _is_layout_event strips the
# suffix before matching.
_LAYOUT_EVENTS = (
    "openwindow",
    "closewindow",
    "fullscreen",
    "workspace",
    "movewindow",
    "changefloatingmode",
    "activewindow",
    "focusedmon",
)


def _is_layout_event(line: str) -> bool:
    """True when an event line can change the active workspace's window count."""
    name = line.split(">>", 1)[0].strip()
    return name in _LAYOUT_EVENTS or name.removesuffix("v2") in _LAYOUT_EVENTS


def _parse_active_workspace_windows(text: str) -> int:
    """The `windows` field of `hyprctl activeworkspace -j` output."""
    return int(json.loads(text)["windows"])


def _freeze_action(window_count: int, frozen: bool) -> str | None:
    """What to send the target: 'STOP', 'CONT', or None (already aligned)."""
    if window_count > 0 and not frozen:
        return "STOP"
    if window_count == 0 and frozen:
        return "CONT"
    return None


def _event_socket_path() -> str:
    """Path to Hyprland's event socket (`.socket2.sock` in the instance dir)."""
    sig = os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return os.path.join(runtime, "hypr", sig, ".socket2.sock")


class _Watcher:
    """Keeps a specific mpvpaper frozen exactly while the desktop is occupied."""

    def __init__(self, pid: int, hyprctl: str) -> None:
        self._pid = pid
        self._hyprctl = hyprctl
        self._frozen = False

    def _target_alive(self) -> bool:
        try:
            os.kill(self._pid, 0)
            return True
        except OSError:
            return False

    def _signal(self, sig: int) -> None:
        try:
            os.kill(self._pid, sig)
        except OSError:
            pass  # target already gone; _target_alive handles exit on the next sync

    def _window_count(self) -> int | None:
        """The active workspace's window count, or None if it can't be read.

        Retries a few times: hyprctl can transiently fail (compositor busy or
        mid-reconfigure) right when a layout event fires — the exact moment a
        missed read would strand the freeze state.
        """
        for _ in range(_WINDOW_COUNT_RETRIES):
            result = subprocess.run(
                [self._hyprctl, "activeworkspace", "-j"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                try:
                    return _parse_active_workspace_windows(result.stdout)
                except (ValueError, KeyError):
                    pass
            time.sleep(_WINDOW_COUNT_RETRY_DELAY_S)
        return None

    def sync(self) -> None:
        """Align the freeze state with the active workspace's window count."""
        if not self._target_alive():
            return
        count = self._window_count()
        if count is None:
            # Unknown state: never leave the wallpaper frozen on uncertainty.
            # A playing wallpaper while windows are open costs a little CPU; a
            # stuck-freeze needs a manual CONT, which is far worse.
            if self._frozen:
                self._signal(signal.SIGCONT)
                self._frozen = False
            return
        action = _freeze_action(count, self._frozen)
        if action is None:
            return
        self._signal(signal.SIGSTOP if action == "STOP" else signal.SIGCONT)
        self._frozen = action == "STOP"

    def _resume_and_exit(self, _signum: int, _frame: object) -> None:
        self._signal(signal.SIGCONT)
        sys.exit(0)

    def run(self) -> int:
        """Subscribe to Hyprland events and re-sync on layout changes."""
        signal.signal(signal.SIGTERM, self._resume_and_exit)
        signal.signal(signal.SIGINT, self._resume_and_exit)
        self.sync()  # state may already be wrong before we subscribed
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(_event_socket_path())
                sock.sendall(b"subscribeAll\n")
                with sock.makefile("r") as lines:
                    while True:
                        if not self._target_alive():
                            break  # superseded; the backend owns respawning us
                        # Timeout-gated read: layout events trigger an
                        # immediate sync, and a quiet socket re-syncs on a
                        # timer so a missed event can't strand the freeze state.
                        readable, _, _ = select.select([sock], [], [], _RESYNC_INTERVAL_S)
                        if not readable:
                            self.sync()
                            continue
                        line = lines.readline()
                        if not line:
                            break  # EOF: compositor restart or teardown
                        if _is_layout_event(line):
                            self.sync()
        except OSError:
            # Socket vanished (compositor restart/teardown). Never leave the
            # wallpaper frozen.
            self._signal(signal.SIGCONT)
            return 0
        # Socket EOF/error: compositor restart or session teardown. Never leave
        # the wallpaper frozen.
        self._signal(signal.SIGCONT)
        return 0


def main(argv: list[str]) -> int:
    if not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return 1
    hyprctl = shutil.which("hyprctl")
    if hyprctl is None:
        return 1
    return _Watcher(int(argv[0]), hyprctl).run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
