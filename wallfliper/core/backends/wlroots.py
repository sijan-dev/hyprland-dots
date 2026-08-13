"""Wallpaper backend for wlr-layer-shell compositors.

Images  -> swww (needs swww-daemon; we start it on demand if absent).
Video   -> mpvpaper, launched detached with -s -a MAX (auto-stop when the
           wallpaper is hidden, i.e. covered by a fullscreen/maximized window).
           On Hyprland a detached event-driven watcher (core/hyprfreeze.py)
           additionally SIGSTOPs the video whenever any window is open on the
           active workspace, so a tiled desktop costs no CPU.

Applying an image stops any running mpvpaper: there is only ever one wallpaper
at a time.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from ..firstframe import first_frame
from ..state import cache_dir
from .base import (
    BackendError,
    ImageTransition,
    MissingDependencyError,
    WallpaperBackend,
)


_SWWW_CANDIDATES = ("swww", "awww")

# swww's animated transitions minus 'fade'. We resolve 'random' from this pool
# ourselves rather than passing swww's own 'random', which can land on fade.
# Fade finishes visually well before the transition duration, so the seamless
# video lead-in (which keeps mpvpaper paused for the full duration) would sit on
# a frozen frame after the animation is already done. The instant 'none'/'simple'
# switches are excluded too — these are the actual animations.
_RANDOM_TRANSITIONS = (
    "wipe",
    "wave",
    "grow",
    "center",
    "outer",
    "left",
    "right",
    "top",
    "bottom",
)


def _resolve_random(transition: ImageTransition) -> ImageTransition:
    """Resolve a 'random' transition to a concrete type (fade excluded); others pass through.

    Centralizes the pick so the swww `--transition-*` flags and the seamless
    lead-in's timing read the *same* concrete type. Resolving 'random'
    independently in each place could desync them — e.g. an instant type chosen
    for the flags while the driver still waits the full duration to unpause,
    leaving mpv frozen on frame 0 after the (instant) switch already finished.
    """
    if transition.type == "random":
        return replace(transition, type=random.choice(_RANDOM_TRANSITIONS))
    return transition


# mpv options passed through to mpvpaper via -o. Tuned for robust, quiet, looping
# playback. no-config isolates from the user's ~/.config/mpv: a custom mpv.conf
# (broken hwdec/vo, scripts) is a common cause of a wallpaper that never plays.
# no-osd hides mpv's corner messages over the wallpaper. Hardware decode with
# bilinear scaling keeps the GPU cost low while the wallpaper is visible. The
# initial pause state is appended per-launch (see _mpvpaper_cmd): a hard cut
# starts playing at once, the seamless lead-in starts paused on frame 0 and is
# unpaused over IPC.
#
# video-sync stays on mpv's default decoupled (audio/system) clock rather than
# display-resample: a wallpaper outlives DPMS sleep and suspend, and slaving
# playback to the display's vsync clock makes mpv freeze on a stale, wrongly
# scaled buffer when the output is torn down and recreated on wake. For the same
# reason interpolation/tscale are omitted — they need continuous presentation
# feedback, are pure GPU cost on a looping background, and stall across reconfig.
_MPV_OPTIONS = " ".join(
    [
        "loop",
        "--no-audio",
        "no-config",
        "no-osd",
        "--hwdec=auto",
        "--video-sync=audio",
        "--scale=bilinear",
        "--dscale=bilinear",
    ]
)

_ALL_OUTPUTS = "*"
_DAEMON_TIMEOUT_S = 3.0

# Env-gated diagnostic log (WALLFLIPER_DEBUG=1 → /tmp/wallfliper-debug.log).
# Records every mpvpaper/freezer/driver lifecycle event so a stacked or leaked
# wallpaper can be traced to the apply that caused it.
_DEBUG_LOG = Path("/tmp/wallfliper-debug.log")


def _debug(msg: str) -> None:
    """Append a timestamped lifecycle event when WALLFLIPER_DEBUG=1."""
    if os.environ.get("WALLFLIPER_DEBUG") != "1":
        return
    try:
        with _DEBUG_LOG.open("a") as fh:
            fh.write(f"{time.monotonic():.3f} pid={os.getpid()} {msg}\n")
    except OSError:
        pass


# How long the outgoing mpvpaper keeps covering the screen after a new one is
# launched, before we retire it. Must exceed mpvpaper's surface-map time so the
# new video is up before the old goes away — otherwise swww's background would
# flash through the gap. ~0.8s is comfortably past typical mpv startup.
_VIDEO_SWAP_DELAY_S = 0.8
# Seamless lead-in: how far before the transition ends mpvpaper is launched, so
# its cold-start overlaps the animation instead of stacking after it. Roughly
# mpv's startup cost — too small leaves a residual delay before motion, too
# large maps mpv (frozen on frame 0) over the transition's last frames. The
# detached driver gates the unpause on the full duration regardless, so motion
# never begins before the animation visually ends.
_MPV_PREWARM_S = 0.6
_SEAMLESS_DRIVER = Path(__file__).resolve().parent.parent / "seamless.py"
_HYPRFREEZE = Path(__file__).resolve().parent.parent / "hyprfreeze.py"


class WlrootsBackend(WallpaperBackend):
    """Drives swww/mpvpaper on a wlr-layer-shell compositor."""

    def __init__(self) -> None:
        # The most recent seamless driver (core/seamless.py) that may still be
        # pending, and the IPC socket it was handed. It brings its video up ~1s in
        # the future, so a superseding apply has to cancel it (see
        # _cancel_pending_transition) or the stale video maps on top of the newer
        # wallpaper; the socket is unlinked there since a killed driver can't.
        self._pending_driver: subprocess.Popen | None = None
        self._pending_sock: str | None = None

    def is_available(self) -> bool:
        return os.environ.get("WAYLAND_DISPLAY") is not None

    # --- public API -----------------------------------------------------

    def set_image(self, path: Path, transition: ImageTransition | None = None) -> None:
        _debug(f"set_image {path.name}")
        self._cancel_pending_transition()  # a pending video must not map over the image
        self._stop_video()
        tool = self._resolve(_SWWW_CANDIDATES)
        self._ensure_daemon(tool)
        self._run([tool, "img", *self._transition_args(transition), str(path)])

    @staticmethod
    def _transition_args(transition: ImageTransition | None) -> list[str]:
        """Translate a transition choice into swww `--transition-*` flags."""
        if transition is None:
            return []
        # Resolve 'random' here (excluding fade) instead of letting swww pick.
        ttype = _resolve_random(transition).type
        args = ["--transition-type", ttype, "--transition-fps", str(transition.fps)]
        # swww ignores duration for the instant 'none'/'simple' switch.
        if ttype not in ("none", "simple"):
            args += ["--transition-duration", str(transition.duration)]
        return args

    def set_video(self, path: Path, transition: ImageTransition | None = None) -> None:
        mpvpaper = self._require("mpvpaper")
        # Supersede any in-flight seamless lead-in *before* sampling the running
        # state, so old_pids includes a (paused) video the cancelled driver had
        # already mapped — it gets retired below instead of lingering frozen.
        had_pending = self._pending_driver is not None
        self._cancel_pending_transition()
        old_pids = self._mpvpaper_pids()
        _debug(f"set_video {path.name} had_pending={had_pending} old_pids={old_pids}")
        # Already rendering this exact file → no-op, avoid stacking a 2nd GPU
        # decoder. Skipped when a driver was just cancelled: that mpvpaper is
        # paused on frame 0 and its un-pauser is now dead, so it must be redone.
        if (
            not had_pending
            and len(old_pids) == 1
            and self._video_path_of(old_pids[0]) == str(path)
        ):
            return
        if transition is not None and self._transition_into_video(
            path, transition, old_pids, mpvpaper
        ):
            _debug(f"set_video {path.name} seamless path")
            self._kill_freezers()  # the new video's watcher is spawned by its driver
            return
        # Hard cut (restore on login, or no ffmpeg/swww to fake a transition).
        # On Hyprland a detached watcher SIGSTOPs the video while any window is
        # open on the active workspace (see _spawn_freezer).
        self._kill_freezers()  # supersede the previous video's watcher
        new = self._spawn_detached(self._mpvpaper_cmd(mpvpaper, path))
        _debug(f"set_video {path.name} hard cut -> mpvpaper pid={new.pid}")
        self._spawn_freezer(new.pid)
        if old_pids:
            # Video -> video: killing the old mpvpaper first would briefly uncover
            # swww's stale background during the new one's startup. Instead we let
            # the old video keep covering the screen and retire it a beat later,
            # once the new surface has mapped — a seamless swap. Detached so it
            # outlives our GUI, which exits immediately after Enter.
            self._retire_pids(old_pids)

    def _transition_into_video(
        self,
        path: Path,
        transition: ImageTransition,
        old_pids: list[int],
        mpvpaper: str,
    ) -> bool:
        """Fake a video transition by animating to its first frame via swww.

        swww has no concept of video; mpvpaper has no transitions. So animate the
        switch on a still of the video's opening frame, then bring the live video
        up on top of that identical frame — the cut is invisible. Returns False
        (caller falls back to a hard cut) when the pieces aren't available: no
        swww, or the first-frame still isn't cached yet (extraction is warmed
        off-thread on selection; the apply path never blocks the GUI on ffmpeg).

        Any covering mpvpaper is dropped *now* so the swww animation is visible
        underneath it; a detached driver (core/seamless.py) then brings the video
        up and unpauses it in sync with the animation, so this works even though
        the GUI exits right after apply.
        """
        swww = self._resolve_optional(_SWWW_CANDIDATES)
        if swww is None:
            return False
        # cached_only: don't run ffmpeg on the GUI thread at apply. A not-yet-warmed
        # clip degrades to a hard cut instead of freezing the overlay.
        frame = first_frame(path, cached_only=True)
        if frame is None:
            return False
        try:
            self._ensure_daemon(swww)
        except BackendError:
            return False  # daemon won't start → fall back to a plain hard cut
        # Resolve 'random' once so the swww flags below and the driver's unpause
        # timing agree on the same concrete transition (see _resolve_random).
        transition = _resolve_random(transition)
        # Dispatch the transition *before* retiring the old video. swww img returns
        # as soon as the daemon accepts the frame (it animates asynchronously), so
        # killing mpvpaper right after reveals a wipe that is already painting — no
        # blank-background flash on a video->video switch (swww's surface is stale
        # there). If swww itself fails (daemon/compositor hiccup), bail so the
        # caller falls back to a hard cut instead of dropping the current wallpaper
        # onto a frame that never rendered.
        if self._run(
            [swww, "img", *self._transition_args(transition), str(frame)],
            check=False,
        ).returncode != 0:
            return False
        if old_pids:
            self._kill_pids(old_pids)  # reveal swww so its transition shows
            _debug(f"seamless killed old mpvpapers {old_pids}")
        instant = transition.type in ("none", "simple")
        duration = 0.0 if instant else transition.duration
        sock = self._ipc_socket_path()
        cfg = json.dumps(
            {
                "cmd": self._mpvpaper_cmd(mpvpaper, path, ipc_socket=sock),
                # Hard-cut command the driver falls back to if the IPC unpause
                # never lands, so a failed handoff plays instead of freezing.
                "fallback": self._mpvpaper_cmd(mpvpaper, path),
                "sock": sock,
                "duration": duration,
                "prewarm": _MPV_PREWARM_S,
            }
        )
        # The driver runs in its own process: it launches mpvpaper paused on the
        # first frame partway through the transition (overlapping cold-start) and
        # unpauses it over IPC the instant the duration elapses — so motion begins
        # exactly when the animation ends, not a cold-start later. Tracked so a
        # quick follow-up apply can cancel it before it maps a now-stale video.
        self._pending_driver = self._spawn_detached(
            [sys.executable, str(_SEAMLESS_DRIVER), cfg]
        )
        _debug(
            f"seamless driver spawned pid={self._pending_driver.pid} sock={sock} "
            f"duration={duration}"
        )
        self._pending_sock = sock
        return True

    def _cancel_pending_transition(self) -> None:
        """Kill a still-pending seamless driver so a newer apply wins.

        The driver brings its video up ~1s after apply (it overlaps mpv's
        cold-start with the swww animation, then unpauses over IPC). Without
        this, a quick second apply races that timer and the stale video maps on
        top of the newer wallpaper — switching video->image fast would leave the
        video showing, and fast video->video would land on the wrong clip.

        Killing the driver's process group stops it before it launches or
        unpauses mpv. Any mpvpaper it already spawned escaped into its own
        session (start_new_session), so killpg here doesn't touch it; the caller
        reaps it separately via old_pids / _stop_video.
        """
        driver = self._pending_driver
        sock = self._pending_sock
        self._pending_driver = None
        self._pending_sock = None
        if driver is None:
            return
        _debug(f"cancel pending driver pid={driver.pid} sock={sock}")
        try:
            os.killpg(driver.pid, signal.SIGKILL)  # driver is its own session leader
        except OSError:
            pass  # already exited
        try:
            driver.wait(timeout=1.0)  # reap it so cancelled drivers don't pile up as zombies
        except subprocess.TimeoutExpired:
            pass  # SIGKILL is near-instant; never block apply on a stuck reap
        if sock is not None:
            # The driver was killed before its own socket cleanup, so do it here —
            # otherwise every superseded transition leaks an IPC socket. Safe even
            # if mpv came up: it keeps its listening fd, only the pathname goes.
            Path(sock).unlink(missing_ok=True)

    @staticmethod
    def _ipc_socket_path() -> str:
        """A fresh mpv IPC socket path (unique per launch, never stale)."""
        runtime = os.environ.get("XDG_RUNTIME_DIR")
        base = Path(runtime) if runtime else cache_dir()
        if runtime is None:
            # XDG_RUNTIME_DIR is normally always set on a live Wayland session;
            # the cache-dir fallback may not exist yet, and mpv won't create the
            # socket's parent — without it the IPC handoff fails and the seamless
            # transition silently degrades to a hard cut. Best-effort create.
            try:
                base.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        return str(base / f"wallfliper-mpv-{time.monotonic_ns()}.sock")

    @staticmethod
    def _mpvpaper_cmd(mpvpaper: str, path: Path, ipc_socket: str | None = None) -> list[str]:
        """argv for a detached, auto-stopping mpvpaper covering every output.

        -s -a MAX stop the video whenever any window is fullscreen or maximized
        (mpvpaper keeps a static last frame and resumes where it left off once
        the desktop is visible again), so a covered wallpaper costs no CPU/RAM.

        Without `ipc_socket` it is a hard cut: start playing immediately. With
        one it starts paused on frame 0 with an IPC server, for the seamless
        driver to unpause once the transition has finished.
        """
        opts = _MPV_OPTIONS
        if ipc_socket is None:
            opts += " pause=no"
        else:
            opts += f" pause=yes --input-ipc-server={ipc_socket}"
        return [mpvpaper, "-s", "-a", "MAX", "-o", opts, _ALL_OUTPUTS, str(path)]

    # --- helpers --------------------------------------------------------

    def _ensure_daemon(self, tool: str) -> None:
        """Start the wallpaper daemon if it is not already responding."""
        if self._run([tool, "query"], check=False).returncode == 0:
            return
        daemon = self._require(f"{Path(tool).name}-daemon")
        self._spawn_detached([daemon])
        deadline = time.monotonic() + _DAEMON_TIMEOUT_S
        while time.monotonic() < deadline:
            if self._run([tool, "query"], check=False).returncode == 0:
                return
            time.sleep(0.1)
        raise BackendError(f"{Path(daemon).name} did not become ready in time.")

    @staticmethod
    def _resolve_optional(candidates: tuple[str, ...]) -> str | None:
        """Path to the first available tool, or None if none are installed."""
        for name in candidates:
            found = shutil.which(name)
            if found:
                return found
        return None

    @classmethod
    def _resolve(cls, candidates: tuple[str, ...]) -> str:
        """Return the path to the first available tool, or raise."""
        found = cls._resolve_optional(candidates)
        if found is None:
            raise MissingDependencyError(
                "no wallpaper tool found; install one of: " + ", ".join(candidates)
            )
        return found

    def _stop_video(self) -> None:
        """Terminate any running mpvpaper instance (best effort).

        The freeze watchers must go first (their SIGTERM handler resumes a
        frozen video), and mpvpaper must be CONT'd before it is killed: SIGSTOP
        queues a TERM instead of delivering it. KILL, not TERM, because
        mpvpaper's --auto-stop hook catches SIGTERM and merely pauses instead
        of exiting — a TERM'd mpvpaper would survive as a ghost and stack.
        """
        _debug("stop_video (pkill all mpvpaper)")
        self._kill_freezers()
        subprocess.run(
            ["pkill", "-CONT", "-x", "mpvpaper"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["pkill", "-KILL", "-x", "mpvpaper"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @staticmethod
    def _mpvpaper_pids() -> list[int]:
        """PIDs of currently running mpvpaper processes (empty if none)."""
        result = subprocess.run(
            ["pgrep", "-x", "mpvpaper"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return [int(pid) for pid in result.stdout.split()]

    @staticmethod
    def _video_path_of(pid: int) -> str | None:
        """The media file an mpvpaper PID is playing (its last argv entry), or None.

        Read from /proc/<pid>/cmdline (NUL-separated argv). mpvpaper's media path
        is the final argument, after the options and the `*` output selector — the
        same way we launch it in set_video. Used to detect an already-correct
        wallpaper so a redundant restore can no-op instead of stacking a duplicate.
        """
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as fh:
                argv = [field for field in fh.read().split(b"\x00") if field]
        except OSError:
            return None
        return argv[-1].decode("utf-8", "replace") if argv else None

    @staticmethod
    def _kill_pids(pids: list[int]) -> None:
        """Terminate the given PIDs immediately (best effort).

        CONT first: a frozen (SIGSTOPped) mpvpaper would otherwise queue a TERM
        and survive. KILL, not TERM: mpvpaper's --auto-stop hook catches
        SIGTERM and pauses instead of exiting, so a TERM'd process would linger
        as a stacked ghost. Self-contained here, so the seamless supersede path
        does not depend on the watchers being killed elsewhere.
        """
        targets = " ".join(str(pid) for pid in pids)
        _debug(f"kill_pids {pids}")
        subprocess.run(
            ["sh", "-c", f"kill -CONT {targets} 2>/dev/null; kill -KILL {targets} 2>/dev/null"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @staticmethod
    def _retire_pids(pids: list[int]) -> None:
        """Kill the given mpvpaper PIDs after the swap delay, detached.

        The delay lets the freshly launched mpvpaper map its surface before we
        remove the old one, so swww's background never shows through the seam.
        CONT first: a frozen (SIGSTOPped) process would otherwise queue the
        TERM. KILL, not TERM: mpvpaper's --auto-stop hook catches SIGTERM and
        merely pauses, so the old video would never actually retire. Runs in
        its own session so it survives our GUI exiting right after apply.
        """
        targets = " ".join(str(pid) for pid in pids)
        _debug(f"retire_pids {pids} (kill after {_VIDEO_SWAP_DELAY_S}s)")
        subprocess.Popen(
            [
                "sh",
                "-c",
                f"kill -CONT {targets} 2>/dev/null; sleep {_VIDEO_SWAP_DELAY_S}; kill -KILL {targets} 2>/dev/null",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise BackendError(
                f"command failed ({result.returncode}): {' '.join(cmd)}\n"
                f"{result.stderr.strip()}"
            )
        return result

    @staticmethod
    def _spawn_detached(cmd: list[str]) -> subprocess.Popen:
        """Launch a fully detached process (survives GUI exit); return its handle."""
        return subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    @staticmethod
    def _hyprland_present() -> bool:
        """True in a Hyprland session (where the freeze watcher can run)."""
        return (
            os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") is not None
            and shutil.which("hyprctl") is not None
        )

    def _spawn_freezer(self, pid: int) -> None:
        """Start the window-freeze watcher for a freshly launched mpvpaper.

        Hyprland only: a detached watcher (core/hyprfreeze.py) SIGSTOPs the
        given mpvpaper whenever any window is open on the active workspace and
        resumes it when the desktop is empty. Elsewhere the video keeps the
        -s -a MAX fullscreen/maximized auto-stop instead.
        """
        if not self._hyprland_present():
            return
        _debug(f"spawn freezer for mpvpaper pid={pid}")
        self._spawn_detached([sys.executable, str(_HYPRFREEZE), str(pid)])

    @staticmethod
    def _kill_freezers() -> None:
        """Terminate any running freeze watcher (best effort).

        SIGTERM lets the watcher's handler resume a frozen video before exit.
        The pattern matches only hyprfreeze.py command lines, never wallfliper.
        """
        _debug("kill all freezers")
        subprocess.run(
            ["pkill", "-f", "hyprfreeze.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
