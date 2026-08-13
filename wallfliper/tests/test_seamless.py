"""Tests for the seamless driver's Hyprland freezer spawn."""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from core import seamless


class FreezerSpawnTest(unittest.TestCase):
    def test_freezer_script_points_next_to_driver(self) -> None:
        self.assertTrue(seamless._freezer_script().endswith("hyprfreeze.py"))

    def test_spawns_watcher_with_mpvpaper_pid(self) -> None:
        with mock.patch("core.seamless.subprocess.Popen") as popen:
            seamless._spawn_freezer("/x/hyprfreeze.py", 4242)
        self.assertEqual(
            popen.call_args.args[0], [sys.executable, "/x/hyprfreeze.py", "4242"]
        )


if __name__ == "__main__":
    unittest.main()
