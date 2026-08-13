"""Tests for headless CLI actions (`--random`)."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main as app
from core.backends import BackendError
from core.backends.base import ImageTransition
from core.state import Config


def _images_dir() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmp = tempfile.TemporaryDirectory()
    return tmp, Path(tmp.name)


class RandomImageTest(unittest.TestCase):
    def test_returns_only_image_files(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        for name in ("a.jpg", "b.PNG", "c.gif", "d.txt", "e.jpeg"):
            (d / name).write_text("x")
        picked = {app._random_image(d) for _ in range(200)}
        self.assertEqual(
            picked, {d / "a.jpg", d / "b.PNG", d / "c.gif", d / "e.jpeg"}
        )

    def test_returns_none_when_no_images(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        (d / "notes.txt").write_text("x")
        self.assertIsNone(app._random_image(d))

    def test_returns_none_when_dir_missing(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        self.assertIsNone(app._random_image(d / "missing"))


class RandomCommandTest(unittest.TestCase):
    def test_applies_random_image_and_runs_hooks(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        img = d / "pic.jpg"
        img.write_text("x")
        cfg = Config(
            wallpaper_dir=str(d),
            color_hook="matugen image {path} -m dark",
            lock_background=True,
        )
        applied: list[Path] = []
        transitions: list[ImageTransition | None] = []
        order: list[str] = []
        with mock.patch("main.load_config", return_value=cfg), mock.patch(
            "main.get_backend"
        ) as get_bk, mock.patch("main.notify_color_tools") as notify, mock.patch(
            "main.sync_lock_background"
        ) as sync, mock.patch("main.save_state") as save:
            get_bk.return_value.set_image.side_effect = (
                lambda p, transition=None: (
                    applied.append(p),
                    transitions.append(transition),
                )
            )
            notify.side_effect = lambda *a, **k: order.append("notify")
            sync.side_effect = lambda *a, **k: order.append("sync")
            save.side_effect = lambda *a, **k: order.append("save")
            self.assertEqual(app._random(), 0)
        self.assertEqual(applied, [img])
        self.assertEqual(transitions, [ImageTransition(duration=0.5)])
        notify.assert_called_once_with(img, "image", cfg.color_hook)
        sync.assert_called_once_with(img, True)
        save.assert_called_once_with(img, "image")
        self.assertEqual(order, ["notify", "sync", "save"])

    def test_missing_wallpaper_dir_errors(self) -> None:
        cfg = Config(wallpaper_dir=None)
        with mock.patch("main.load_config", return_value=cfg):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(app._random(), 1)

    def test_empty_dir_errors(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        cfg = Config(wallpaper_dir=str(d))
        with mock.patch("main.load_config", return_value=cfg):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(app._random(), 1)

    def test_backend_failure_errors_and_skips_hooks(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        img = d / "pic.jpg"
        img.write_text("x")
        cfg = Config(wallpaper_dir=str(d))
        with mock.patch("main.load_config", return_value=cfg), mock.patch(
            "main.get_backend"
        ) as get_bk, mock.patch("main.save_state") as save:
            get_bk.return_value.set_image.side_effect = BackendError("boom")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(app._random(), 1)
        save.assert_not_called()


class CliRandomTest(unittest.TestCase):
    def test_random_flag_invokes_random(self) -> None:
        tmp, d = _images_dir()
        self.addCleanup(tmp.cleanup)
        img = d / "pic.jpg"
        img.write_text("x")
        cfg = Config(wallpaper_dir=str(d))
        with mock.patch("main.load_config", return_value=cfg), mock.patch(
            "main.get_backend"
        ) as get_bk, mock.patch("main.save_state") as save, mock.patch(
            "main.config_dir", return_value=d / "cfg"
        ):
            self.assertEqual(app.main(["--random"]), 0)
        get_bk.return_value.set_image.assert_called_once()
        save.assert_called_once()
