"""Tests for post-apply integrations (color tools, hyprlock background)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import integrations
from core.state import Config, load_config, save_config


def _write(tmp: str, text: str) -> Path:
    p = Path(tmp) / "hyprlock.conf"
    p.write_text(text)
    return p


class LockBackgroundSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _conf(self) -> Path:
        return Path(self._tmp.name) / "hyprlock.conf"

    def test_disabled_leaves_conf_untouched(self) -> None:
        conf = self._conf()
        original = "path = /orig.png\n"
        conf.write_text("background {\n" + original + "}\n")
        integrations.sync_lock_background(Path("/new.mp4"), enabled=False, conf=conf)
        self.assertEqual(conf.read_text(), "background {\n" + original + "}\n")

    def test_missing_conf_is_a_noop(self) -> None:
        integrations.sync_lock_background(
            Path("/new.mp4"), enabled=True, conf=self._conf()
        )

    def test_missing_parent_dir_is_a_noop(self) -> None:
        conf = Path(self._tmp.name) / "nope" / "hyprlock.conf"
        integrations.sync_lock_background(Path("/new.mp4"), enabled=True, conf=conf)

    def test_no_background_block_is_a_noop(self) -> None:
        conf = self._conf()
        conf.write_text("label {\n    text = hi\n}\n")
        integrations.sync_lock_background(Path("/new.mp4"), enabled=True, conf=conf)
        self.assertEqual(conf.read_text(), "label {\n    text = hi\n}\n")

    def test_rewrites_path_inside_background_block(self) -> None:
        conf = _write(
            self._tmp.name,
            "# header\nbackground {\n    monitor =\n    path = /mnt/o.png\n"
            "    blur_passes = 2\n}\nlabel {\n    path = /other\n}\n",
        )
        integrations.sync_lock_background(Path("/new/video.mp4"), True, conf=conf)
        text = conf.read_text()
        self.assertIn("    path = /new/video.mp4", text)
        self.assertNotIn("path = /mnt/o.png", text)
        self.assertIn("label {\n    path = /other", text)
        self.assertIn("    blur_passes = 2", text)
        self.assertIn("# header", text)

    def test_comment_background_sample_is_ignored(self) -> None:
        conf = _write(
            self._tmp.name,
            "# sample: background { path = /old.png }\n"
            "background {\n    path = /real.png\n}\n",
        )
        integrations.sync_lock_background(Path("/new.mp4"), True, conf=conf)
        text = conf.read_text()
        self.assertIn("# sample: background { path = /old.png }", text)
        self.assertIn("path = /new.mp4", text)
        self.assertNotIn("path = /real.png", text)

    def test_brace_inside_path_value_does_not_corrupt(self) -> None:
        conf = _write(
            self._tmp.name,
            "background {\n    path = /mnt/foo}bar.png\n}\n"
            "label {\n    text = hi\n}\n",
        )
        integrations.sync_lock_background(Path("/new.mp4"), True, conf=conf)
        text = conf.read_text()
        self.assertIn("path = /new.mp4", text)
        self.assertIn("label {\n    text = hi", text)
        self.assertNotIn("bar.png", text)

    def test_preserves_file_mode(self) -> None:
        conf = _write(self._tmp.name, "background {\n    path = /a.png\n}\n")
        conf.chmod(0o644)
        integrations.sync_lock_background(Path("/b.mp4"), True, conf=conf)
        self.assertEqual(conf.stat().st_mode & 0o777, 0o644)

    def test_write_failure_leaves_original_and_no_temp(self) -> None:
        conf = _write(self._tmp.name, "background {\n    path = /a.png\n}\n")
        with mock.patch("core.integrations.os.replace", side_effect=OSError("boom")):
            integrations.sync_lock_background(Path("/b.mp4"), True, conf=conf)
        self.assertIn("path = /a.png", conf.read_text())
        self.assertEqual(list(Path(self._tmp.name).iterdir()), [conf])

    def test_preserves_indentation_of_path_line(self) -> None:
        conf = _write(self._tmp.name, "background {\n\tpath = /a.png\n}\n")
        integrations.sync_lock_background(Path("/b.mp4"), True, conf=conf)
        self.assertIn("\tpath = /b.mp4", conf.read_text())

    def test_path_with_spaces_kept_unquoted(self) -> None:
        conf = _write(self._tmp.name, "background {\n    path = /a.png\n}\n")
        integrations.sync_lock_background(Path("/my wallpapers/x.mp4"), True, conf=conf)
        self.assertIn("    path = /my wallpapers/x.mp4", conf.read_text())

    def test_idempotent_second_call_no_change(self) -> None:
        conf = _write(self._tmp.name, "background {\n    path = /a.png\n}\n")
        integrations.sync_lock_background(Path("/b.mp4"), True, conf=conf)
        before = conf.read_text()
        integrations.sync_lock_background(Path("/b.mp4"), True, conf=conf)
        self.assertEqual(conf.read_text(), before)

    def test_image_path_preserved_verbatim(self) -> None:
        conf = _write(self._tmp.name, "background {\n    path = /a.png\n}\n")
        integrations.sync_lock_background(Path("/wall/samurai.png"), True, conf=conf)
        self.assertIn("path = /wall/samurai.png", conf.read_text())

    def test_uses_xdg_config_home_default(self) -> None:
        with tempfile.TemporaryDirectory() as xdg, mock.patch.dict(
            os.environ, {"XDG_CONFIG_HOME": xdg}
        ):
            hypr = Path(xdg) / "hypr"
            hypr.mkdir()
            (hypr / "hyprlock.conf").write_text("background {\n    path = /a\n}\n")
            integrations.sync_lock_background(Path("/b.mp4"), True)
            self.assertIn("path = /b.mp4", (hypr / "hyprlock.conf").read_text())


class ConfigFlagTest(unittest.TestCase):
    def test_lock_background_defaults_false(self) -> None:
        self.assertIs(Config().lock_background, False)

    def test_lock_background_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as xdg, mock.patch.dict(
            os.environ, {"XDG_CONFIG_HOME": xdg}
        ):
            save_config(Config(lock_background=True))
            self.assertIs(load_config().lock_background, True)

    def test_missing_flag_stays_false(self) -> None:
        with tempfile.TemporaryDirectory() as xdg, mock.patch.dict(
            os.environ, {"XDG_CONFIG_HOME": xdg}
        ):
            save_config(Config())
            self.assertIs(load_config().lock_background, False)


if __name__ == "__main__":
    unittest.main()
