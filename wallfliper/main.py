#!/usr/bin/env python3
"""Wallfliper entry point.

  wallfliper                  launch the selector GUI
  wallfliper --check          report whether all dependencies are installed
  wallfliper --restore        re-apply the last wallpaper (for login autostart)
  wallfliper --install-autostart   write the autostart entry that runs --restore
  wallfliper --random         apply a random image wallpaper and exit
  wallfliper --next           apply the next image wallpaper in sort order
  wallfliper --prev           apply the previous image wallpaper in sort order
"""

from __future__ import annotations

import argparse
import random
import signal
import sys
from pathlib import Path

from core.backends import BackendError, get_backend
from core.backends.base import ImageTransition
from core.deps import all_required_ok, check, format_report, missing, pyside6_present
from core.integrations import notify_color_tools, sync_lock_background
from core.single_instance import SingleInstance
from core.state import State, config_dir, load_config, load_state, save_state


_RANDOM_EXTS = (".jpg", ".jpeg", ".png", ".gif")


def _sorted_images(wallpaper_dir: Path) -> list[Path]:
    """Every image file in the directory, sorted (consistent ordering)."""
    try:
        return sorted(
            p
            for p in wallpaper_dir.iterdir()
            if p.is_file() and p.suffix.lower() in _RANDOM_EXTS
        )
    except OSError:
        return []


def _random_image(wallpaper_dir: Path) -> Path | None:
    """Pick one random image file from the directory (non-recursive)."""
    try:
        candidates = sorted(
            p
            for p in wallpaper_dir.iterdir()
            if p.is_file() and p.suffix.lower() in _RANDOM_EXTS
        )
    except OSError:
        return None
    return random.choice(candidates) if candidates else None


def _restore() -> int:
    """Re-apply the last wallpaper. No Qt: keeps login-time cost minimal."""
    state = load_state()
    if not state.path or not state.kind:
        return 0
    path = Path(state.path)
    if not path.exists():
        print(f"wallfliper: saved wallpaper missing: {path}", file=sys.stderr)
        return 1
    return _apply(path, state)


def _apply(
    path: Path, state: State, transition: ImageTransition | None = None
) -> int:
    """Apply a wallpaper, then notify/sync theme and save state."""
    backend = get_backend()
    try:
        if state.kind == "video":
            backend.set_video(path)
        else:
            backend.set_image(path, transition)
    except BackendError as exc:
        print(f"wallfliper: apply failed: {exc}", file=sys.stderr)
        return 1
    config = load_config()
    notify_color_tools(path, state.kind, config.color_hook)
    sync_lock_background(path, config.lock_background)
    save_state(path, state.kind)
    return 0


def _random() -> int:
    """Pick a random image from the wallpaper dir and apply it."""
    config = load_config()
    wdir = config.wallpaper_path
    if wdir is None:
        print("wallfliper: no wallpaper directory configured", file=sys.stderr)
        return 1
    path = _random_image(wdir)
    if path is None:
        print(
            f"wallfliper: no images (jpg/jpeg/png/gif) in {wdir}",
            file=sys.stderr,
        )
        return 1
    return _apply(path, State(str(path), "image"), ImageTransition(duration=2))


def _cycle(direction: int) -> int:
    """Move to the next/prev image (relative to current, else first/last)."""
    config = load_config()
    wdir = config.wallpaper_path
    if wdir is None:
        print("wallfliper: no wallpaper directory configured", file=sys.stderr)
        return 1
    images = _sorted_images(wdir)
    if not images:
        print(
            f"wallfliper: no images (jpg/jpeg/png/gif) in {wdir}",
            file=sys.stderr,
        )
        return 1

    current = Path(load_state().path or "")
    index = next((i for i, p in enumerate(images) if p.resolve() == current.resolve()), -1)
    if index < 0:
        index = 0 if direction > 0 else len(images) - 1
    else:
        index = (index + direction) % len(images)
    transition = ImageTransition(
        type="right" if direction > 0 else "left",
        duration=0.5,
    )
    return _apply(images[index], State(str(images[index]), "image"), transition)


def _check() -> int:
    """Print a dependency report. Exit non-zero if a required dep is missing."""
    results = check()
    print("wallfliper: dependency check")
    print(format_report(results))
    ok = all_required_ok(results)
    if not ok:
        print("\nwallfliper: missing required dependencies (see above).", file=sys.stderr)
    return 0 if ok else 1


def _install_autostart() -> int:
    """Write ~/.config/autostart/wallfliper-restore.desktop."""
    python = sys.executable
    script = Path(__file__).resolve()
    autostart = Path.home() / ".config" / "autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    desktop = autostart / "wallfliper-restore.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Wallfliper (restore wallpaper)\n"
        f"Exec={python} {script} --restore\n"
        "X-GNOME-Autostart-enabled=true\n"
        "NoDisplay=true\n"
    )
    print(f"wallfliper: autostart installed at {desktop}")
    return 0


_SYSTEM_QT_QML = "/usr/lib/qt6/qml"
_SYSTEM_QT_PLUGINS = "/usr/lib/qt6/plugins"


def _prepend_system_qt_paths() -> None:
    """Make the system layer-shell QML module + wayland plugin discoverable.

    pip's PySide6 bundles its own Qt and looks only in its own dirs, so it
    won't find the system `org.kde.layershell` module or the layer-shell
    wayland-shell-integration plugin. Prepending the system paths fixes that
    (works because system Qt matches PySide6's bundled Qt version). With a
    distro `pyside6` package these are already the defaults.
    """
    import os

    for var, path in (
        ("QT_PLUGIN_PATH", _SYSTEM_QT_PLUGINS),
        ("QML_IMPORT_PATH", _SYSTEM_QT_QML),
        ("QML2_IMPORT_PATH", _SYSTEM_QT_QML),
    ):
        if os.path.isdir(path):
            existing = os.environ.get(var, "")
            os.environ[var] = path + (os.pathsep + existing if existing else "")


def _install_signal_quit(app) -> tuple:
    """Quit the Qt loop on SIGTERM/SIGINT, event-driven (the self-pipe trick).

    A second launch toggles us off by sending SIGTERM (see SingleInstance). Qt's
    C++ event loop doesn't yield to Python between iterations, so a plain Python
    signal handler wouldn't run until the loop happened to wake. We route signals
    through a socketpair watched by a QSocketNotifier: the signal writes a byte,
    the notifier fires inside the Qt loop and quits cleanly (releasing the lock).
    No polling timer. The returned objects must stay referenced for the app's life.
    """
    import socket

    from PySide6.QtCore import QSocketNotifier

    reader, writer = socket.socketpair()
    reader.setblocking(False)
    writer.setblocking(False)
    signal.set_wakeup_fd(writer.fileno())

    notifier = QSocketNotifier(reader.fileno(), QSocketNotifier.Type.Read)

    def _drain_and_quit() -> None:
        try:
            reader.recv(64)  # drain the wakeup byte(s)
        except OSError:
            pass
        app.quit()

    notifier.activated.connect(_drain_and_quit)
    # Replace the default terminate action with a no-op so the wakeup byte — not
    # an abrupt kill — is what drives the graceful quit above.
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: None)
    return reader, writer, notifier


def _run_gui() -> int:
    _prepend_system_qt_paths()

    # One live GUI only. If another instance is already up, acquire() signals it
    # to close (hotkey toggle) and returns False; we just exit without loading Qt.
    instance = SingleInstance()
    if not instance.acquire():
        return 0

    # Friendly heads-up before Qt loads: surface any missing tool as a hint so a
    # first-run failure isn't a bare traceback. Non-fatal — detection can miss on
    # non-Arch layouts, so we still attempt to launch.
    for dep in missing():
        kind = "required" if dep.required else "optional"
        print(f"wallfliper: {kind} dependency missing — {dep.hint}", file=sys.stderr)

    # Without PySide6 the imports below would be a bare ImportError. The loop
    # above already printed the install hint, so exit cleanly (and free the lock).
    if not pyside6_present():
        instance.release()
        return 1

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from ui.bridge import Controller

    app = QGuiApplication(sys.argv)
    app.setApplicationName("wallfliper")
    app.setDesktopFileName("wallfliper")  # Wayland app_id

    signal_guard = _install_signal_quit(app)  # keep referenced until exec returns

    controller = Controller()
    engine = QQmlApplicationEngine()
    engine.addImportPath(_SYSTEM_QT_QML)
    engine.rootContext().setContextProperty("controller", controller)

    qml_main = Path(__file__).resolve().parent / "ui" / "qml" / "Main.qml"
    engine.load(str(qml_main))
    if not engine.rootObjects():
        print("wallfliper: failed to load QML UI", file=sys.stderr)
        instance.release()
        return 1
    try:
        return app.exec()
    finally:
        del signal_guard
        instance.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wallfliper", description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="report whether all dependencies are installed and exit",
    )
    group.add_argument(
        "--restore", action="store_true", help="re-apply the last wallpaper and exit"
    )
    group.add_argument(
        "--install-autostart",
        action="store_true",
        help="install the login autostart entry for --restore",
    )
    group.add_argument(
        "--random",
        action="store_true",
        help="apply a random image wallpaper from the configured directory and exit",
    )
    group.add_argument(
        "--next",
        action="store_true",
        help="apply the next image wallpaper in the directory and exit",
    )
    group.add_argument(
        "--prev",
        action="store_true",
        help="apply the previous image wallpaper in the directory and exit",
    )
    args = parser.parse_args(argv)

    if args.check:
        return _check()

    config_dir().mkdir(parents=True, exist_ok=True)

    if args.restore:
        return _restore()
    if args.random:
        return _random()
    if args.next:
        return _cycle(1)
    if args.prev:
        return _cycle(-1)
    if args.install_autostart:
        return _install_autostart()
    return _run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
