"""Post-apply theming integration.

Wallpaper *painting* (swww/mpvpaper) is decoupled from *theming*: tools like
noctalia-shell, matugen, wallust or pywal derive a color scheme from the
wallpaper image. Since they don't watch swww, wallfliper notifies them after
applying. Best-effort and non-blocking: a failure here never affects the
wallpaper that was just set, and never blocks the UI.

Color tools only understand still images. For video wallpapers we first extract
a representative frame with ffmpeg and theme from that, so the scheme still
adapts to a video. The extraction is chained into the same detached shell
command (`ffmpeg ... && <notify>`), so it stays off the UI thread and silently
does nothing if ffmpeg is missing.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .state import WallpaperKind, cache_dir

# noctalia v5+ ships a native binary with its own IPC CLI; v4 and earlier is a
# quickshell config reached through `qs`. Detected by binary, newest first.
_NOCTALIA_V5 = "noctalia msg wallpaper-set {path}"
_NOCTALIA_V4 = 'qs -c noctalia-shell ipc call wallpaper set {path} ""'


def notify_color_tools(path: Path, kind: WallpaperKind, hook: str = "") -> None:
    """Tell external theming tools the wallpaper changed.

    If `hook` is set, run it as a shell command with `{path}` substituted (lets
    users wire up matugen/wallust/pywal/etc). Otherwise auto-detect
    noctalia-shell and have it regenerate its scheme. For video, `{path}` /
    the noctalia path is a still frame extracted from the clip.
    """
    color_source, prefix = _color_source(path, kind)
    if color_source is None:
        return  # video but no ffmpeg -> nothing we can theme from

    quoted = shlex.quote(str(color_source))
    if hook:
        _spawn(prefix + hook.replace("{path}", quoted))
        return
    # noctalia regenerates colors even when its own wallpaper rendering is
    # disabled; if it isn't running the call fails fast and is swallowed.
    if shutil.which("noctalia"):
        _spawn(prefix + _NOCTALIA_V5.format(path=quoted))
    elif shutil.which("qs"):
        _spawn(prefix + _NOCTALIA_V4.format(path=quoted))


def _color_source(path: Path, kind: WallpaperKind) -> tuple[Path | None, str]:
    """Return (image to theme from, shell prefix that produces it).

    Images theme directly (no prefix). Video themes from a still frame: the
    prefix is an `ffmpeg ... &&` that writes the frame just before the notify
    command runs. Returns (None, "") when video can't be themed (no ffmpeg).
    """
    if kind != "video":
        return path, ""
    if not shutil.which("ffmpeg"):
        return None, ""
    frame = _next_frame_path()
    frame.parent.mkdir(parents=True, exist_ok=True)
    # -ss 1: skip a possible black/fade-in opening frame. scale: color tools
    # only need the dominant/secondary colors, so 320px wide is ample and keeps
    # the extraction near-instant and the file tiny. -update 1: write a single
    # still without image-sequence warnings.
    prefix = (
        f"ffmpeg -y -ss 1 -i {shlex.quote(str(path))} -frames:v 1 "
        f"-vf scale=320:-2 -update 1 {shlex.quote(str(frame))} >/dev/null 2>&1 && "
    )
    return frame, prefix


def _next_frame_path() -> Path:
    """Pick a frame file whose path differs from the previously used one.

    noctalia (and similar tools) skip regenerating when handed the same
    wallpaper path twice — which broke video->video switches when every frame
    reused one filename. Alternating between two files guarantees the path
    changes each time, while staying strictly bounded to 2 cached frames.
    """
    cache = cache_dir()
    a, b = cache / "colorframe-a.png", cache / "colorframe-b.png"
    if not a.exists():
        return a
    if not b.exists():
        return b
    # Both exist: the most-recently-written one is what the tool currently has,
    # so write to (and return) the other.
    return b if a.stat().st_mtime >= b.stat().st_mtime else a


def _spawn(command: str) -> None:
    """Fire-and-forget a shell command: detached, output and errors discarded."""
    try:
        subprocess.Popen(
            ["sh", "-c", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


_DEFAULT_HYPRLOCK_CONF = Path("hypr") / "hyprlock.conf"


def sync_lock_background(path: Path, enabled: bool, conf: Path | None = None) -> None:
    """Point hyprlock's background path at the current wallpaper.

    Rewrites the `path =` line inside the first `background { }` block of the
    hyprlock config so the lock screen shows the current wallpaper (animated
    for video, static for image). hyprlock re-reads its config on every lock,
    so no reload is needed. Best-effort: a missing config, a config without a
    background block, or any I/O error leaves the file untouched.
    """
    if not enabled:
        return
    target = conf if conf is not None else _default_hyprlock_conf()
    try:
        text = target.read_text()
    except (FileNotFoundError, OSError):
        return
    new_text = _rewrite_background_path(text, str(path))
    if new_text is None or new_text == text:
        return
    try:
        mode = target.stat().st_mode
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".", text=True)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(new_text)
            os.chmod(tmp_name, mode)
            os.replace(tmp_name, target)
        except OSError:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
    except OSError:
        return


def _default_hyprlock_conf() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / _DEFAULT_HYPRLOCK_CONF


def _rewrite_background_path(text: str, new_path: str) -> str | None:
    """Return `text` with the background `path =` value replaced, or None if no
    `background {` block with a `path =` line exists.

    Line-based on purpose: a `background {` in a comment must be ignored, and a
    `}` inside a path value must not close the block. Paths containing `#` are
    not supported (hyprlang would treat it as a comment start).
    """
    lines = text.splitlines(keepends=True)
    start = None
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("background {"):
            start = idx
            break
    if start is None:
        return None
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].lstrip().startswith("}"):
            end = idx + 1
            break
    for idx in range(start, end):
        stripped = lines[idx].lstrip()
        if stripped.startswith("path ="):
            prefix = lines[idx][: len(lines[idx]) - len(stripped)]
            lines[idx] = f"{prefix}path = {new_path}\n"
            return "".join(lines)
    return None
