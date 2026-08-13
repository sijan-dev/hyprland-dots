"""Tests for the mpvpaper launch command built by the wlroots backend."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from core.backends.wlroots import WlrootsBackend, _MPV_OPTIONS


class MpvOptionsTest(unittest.TestCase):
    def test_auto_stop_and_auto_mode_max(self) -> None:
        cmd = WlrootsBackend._mpvpaper_cmd("/usr/bin/mpvpaper", Path("/tmp/x.mp4"))
        self.assertEqual(cmd[1:4], ["-s", "-a", "MAX"])

    def test_all_outputs(self) -> None:
        cmd = WlrootsBackend._mpvpaper_cmd("/usr/bin/mpvpaper", Path("/tmp/x.mp4"))
        self.assertEqual(cmd[-2], "*")
        self.assertEqual(cmd[-1], "/tmp/x.mp4")

    def test_no_heavy_profile(self) -> None:
        self.assertNotIn("high-quality", _MPV_OPTIONS)
        self.assertIn("--scale=bilinear", _MPV_OPTIONS)
        self.assertIn("--dscale=bilinear", _MPV_OPTIONS)

    def test_hard_cut_starts_playing(self) -> None:
        cmd = WlrootsBackend._mpvpaper_cmd("/usr/bin/mpvpaper", Path("/tmp/x.mp4"))
        opts = cmd[cmd.index("-o") + 1]
        self.assertIn("pause=no", opts)
        self.assertNotIn("pause=yes", opts)

    def test_ipc_socket_starts_paused(self) -> None:
        cmd = WlrootsBackend._mpvpaper_cmd(
            "/usr/bin/mpvpaper", Path("/tmp/x.mp4"), ipc_socket="/tmp/wf.sock"
        )
        opts = cmd[cmd.index("-o") + 1]
        self.assertIn("pause=yes", opts)
        self.assertIn("--input-ipc-server=/tmp/wf.sock", opts)


class FreezerTest(unittest.TestCase):
    def test_hyprland_present_requires_env_and_binary(self) -> None:
        with mock.patch.dict(os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "sig"}, clear=True), mock.patch(
            "core.backends.wlroots.shutil.which", return_value="/usr/bin/hyprctl"
        ):
            self.assertTrue(WlrootsBackend._hyprland_present())

    def test_not_hyprland_without_env(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "core.backends.wlroots.shutil.which", return_value="/usr/bin/hyprctl"
        ):
            self.assertFalse(WlrootsBackend._hyprland_present())

    def test_spawn_freezer_only_on_hyprland(self) -> None:
        spawned: list[list[str]] = []
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            WlrootsBackend, "_spawn_detached", side_effect=lambda cmd: spawned.append(cmd)
        ):
            WlrootsBackend()._spawn_freezer(42)
        self.assertEqual(spawned, [])

        with mock.patch.dict(os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "sig"}, clear=True), mock.patch(
            "core.backends.wlroots.shutil.which", return_value="/usr/bin/hyprctl"
        ), mock.patch.object(
            WlrootsBackend, "_spawn_detached", side_effect=lambda cmd: spawned.append(cmd)
        ):
            WlrootsBackend()._spawn_freezer(42)
        self.assertEqual(len(spawned), 1)
        self.assertEqual(spawned[0][-1], "42")
        self.assertTrue(spawned[0][-2].endswith("hyprfreeze.py"))

    def test_stop_video_cont_before_kill(self) -> None:
        calls: list[list[str]] = []
        backend = WlrootsBackend()
        with mock.patch.object(backend, "_kill_freezers"), mock.patch(
            "core.backends.wlroots.subprocess.run", side_effect=lambda cmd, **_: calls.append(cmd)
        ):
            backend._stop_video()
        mpvpaper_calls = [c for c in calls if "mpvpaper" in c]
        self.assertEqual(mpvpaper_calls[0], ["pkill", "-CONT", "-x", "mpvpaper"])
        # KILL, not TERM: mpvpaper's --auto-stop hook catches SIGTERM and merely
        # pauses, so a TERM'd mpvpaper would survive as a stacked ghost.
        self.assertEqual(mpvpaper_calls[1], ["pkill", "-KILL", "-x", "mpvpaper"])

    def test_retire_pids_cont_before_kill(self) -> None:
        with mock.patch("core.backends.wlroots.subprocess.Popen") as popen:
            WlrootsBackend._retire_pids([77])
        script = popen.call_args.args[0][-1]
        self.assertLess(script.index("kill -CONT 77"), script.index("kill -KILL 77"))

    def test_kill_pids_cont_before_kill(self) -> None:
        calls: list[list[str]] = []
        with mock.patch(
            "core.backends.wlroots.subprocess.run", side_effect=lambda cmd, **_: calls.append(cmd)
        ):
            WlrootsBackend._kill_pids([77])
        self.assertEqual(len(calls), 1)
        script = calls[0][-1]
        self.assertLess(script.index("kill -CONT 77"), script.index("kill -KILL 77"))

    def test_hard_cut_spawns_freezer(self) -> None:
        backend = WlrootsBackend()
        spawned: list[list[str]] = []

        class FakePopen:
            pid = 4242

        def fake_spawn(cmd: list[str]) -> FakePopen:
            spawned.append(cmd)
            return FakePopen()

        with (
            mock.patch.object(backend, "_require", return_value="/usr/bin/mpvpaper"),
            mock.patch.object(backend, "_cancel_pending_transition"),
            mock.patch.object(backend, "_mpvpaper_pids", return_value=[]),
            mock.patch.object(backend, "_spawn_detached", side_effect=fake_spawn),
            mock.patch.object(backend, "_kill_freezers"),
            mock.patch.object(backend, "_spawn_freezer"),
            mock.patch.object(backend, "_retire_pids"),
        ):
            backend.set_video(Path("/tmp/x.mp4"))
            backend._spawn_freezer.assert_called_once_with(4242)
            self.assertFalse(backend._retire_pids.called)


if __name__ == "__main__":
    unittest.main()
