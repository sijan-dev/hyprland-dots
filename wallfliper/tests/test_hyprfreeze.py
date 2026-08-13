"""Tests for the Hyprland window-freeze watcher."""

from __future__ import annotations

import os
import signal
import unittest
from unittest import mock

from core.hyprfreeze import (
    _Watcher,
    _freeze_action,
    _is_layout_event,
    _parse_active_workspace_windows,
    _RESYNC_INTERVAL_S,
    main,
)


class FreezeActionTest(unittest.TestCase):
    def test_stop_when_windows_appear(self) -> None:
        self.assertEqual(_freeze_action(1, frozen=False), "STOP")

    def test_continue_when_workspace_empties(self) -> None:
        self.assertEqual(_freeze_action(0, frozen=True), "CONT")

    def test_no_action_when_state_matches(self) -> None:
        self.assertIsNone(_freeze_action(2, frozen=True))
        self.assertIsNone(_freeze_action(0, frozen=False))


class LayoutEventTest(unittest.TestCase):
    def test_known_events_are_layout_events(self) -> None:
        self.assertTrue(_is_layout_event("openwindow>>0x1,firefox,Firefox"))
        self.assertTrue(_is_layout_event("closewindow>>0x1"))
        self.assertTrue(_is_layout_event("workspace>>1"))

    def test_v2_variants_are_layout_events(self) -> None:
        self.assertTrue(_is_layout_event("activewindowv2>>0x55"))
        self.assertTrue(_is_layout_event("workspacev2>>1"))
        self.assertTrue(_is_layout_event("focusedmonv2>>eDP-1,6"))

    def test_unrelated_events_are_ignored(self) -> None:
        self.assertFalse(_is_layout_event("windowtitle>>0x1,title"))
        self.assertFalse(_is_layout_event("notify>>hi"))


class ParseActiveWorkspaceTest(unittest.TestCase):
    def test_parses_windows_field(self) -> None:
        self.assertEqual(
            _parse_active_workspace_windows('{"id": 3, "windows": 2, "hasfullscreen": false}'),
            2,
        )


class WatcherTest(unittest.TestCase):
    def test_stops_on_first_window_and_stays(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        signals: list[int] = []
        with mock.patch.object(watcher, "_target_alive", return_value=True), mock.patch.object(
            watcher, "_window_count", return_value=1
        ), mock.patch.object(
            watcher, "_signal", side_effect=lambda sig: signals.append(sig)
        ):
            watcher.sync()
            watcher.sync()
        self.assertEqual(signals, [signal.SIGSTOP])
        self.assertTrue(watcher._frozen)

    def test_resumes_when_workspace_empties(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        watcher._frozen = True
        signals: list[int] = []
        with mock.patch.object(watcher, "_target_alive", return_value=True), mock.patch.object(
            watcher, "_window_count", return_value=0
        ), mock.patch.object(
            watcher, "_signal", side_effect=lambda sig: signals.append(sig)
        ):
            watcher.sync()
        self.assertEqual(signals, [signal.SIGCONT])
        self.assertFalse(watcher._frozen)

    def test_ignores_target_already_gone(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        with mock.patch.object(watcher, "_target_alive", return_value=False), mock.patch.object(
            watcher, "_window_count", return_value=1
        ) as count:
            watcher.sync()
        count.assert_not_called()

    def test_unknown_count_resumes_frozen_target(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        watcher._frozen = True
        signals: list[int] = []
        with mock.patch.object(watcher, "_target_alive", return_value=True), mock.patch.object(
            watcher, "_window_count", return_value=None
        ), mock.patch.object(
            watcher, "_signal", side_effect=lambda sig: signals.append(sig)
        ):
            watcher.sync()
        self.assertEqual(signals, [signal.SIGCONT])
        self.assertFalse(watcher._frozen)

    def test_unknown_count_never_freezes(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        signals: list[int] = []
        with mock.patch.object(watcher, "_target_alive", return_value=True), mock.patch.object(
            watcher, "_window_count", return_value=None
        ), mock.patch.object(
            watcher, "_signal", side_effect=lambda sig: signals.append(sig)
        ):
            watcher.sync()
        self.assertEqual(signals, [])
        self.assertFalse(watcher._frozen)

    def test_window_count_retries_transient_failure(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        results = iter(
            [
                mock.Mock(returncode=1, stdout=""),
                mock.Mock(returncode=0, stdout='{"windows": 0}'),
            ]
        )
        with mock.patch("core.hyprfreeze.subprocess.run", side_effect=lambda *a, **k: next(results)):
            self.assertEqual(watcher._window_count(), 0)

    def test_event_loop_runs_sync_on_timer(self) -> None:
        """A quiet socket must re-sync on the timer, healing a missed closewindow.

        Initial sync: workspace occupied (count 1), already frozen → aligned, no
        signal. Then select times out (no event — the closewindow was missed) and
        the timer sync sees an empty workspace → CONT. EOF then resumes (no-op).
        """
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        watcher._frozen = True
        signals: list[int] = []
        counts = iter([1, 0])
        select_results = iter([([], [], []), ([True], [], [])])
        with mock.patch(
            "core.hyprfreeze.select.select", side_effect=lambda *a, **k: next(select_results)
        ), mock.patch("core.hyprfreeze.socket.socket") as sock_cls, mock.patch.object(
            watcher, "_target_alive", return_value=True
        ), mock.patch.object(
            watcher, "_window_count", side_effect=lambda: next(counts)
        ), mock.patch.object(
            watcher, "_signal", side_effect=lambda sig: signals.append(sig)
        ):
            sock_cls.return_value.__enter__.return_value.connect = mock.Mock()
            sock_cls.return_value.__enter__.return_value.sendall = mock.Mock()
            lines = sock_cls.return_value.__enter__.return_value.makefile.return_value
            lines.readline.return_value = ""
            lines.__enter__.return_value = lines
            result = watcher.run()
        self.assertEqual(result, 0)
        # timer heal CONTs the frozen target; the EOF teardown CONTs again (no-op)
        self.assertEqual(signals, [signal.SIGCONT, signal.SIGCONT])
        self.assertFalse(watcher._frozen)

    def test_connect_failure_resumes_a_frozen_target(self) -> None:
        watcher = _Watcher(123, "/usr/bin/hyprctl")
        signals: list[int] = []
        with mock.patch.object(watcher, "_target_alive", return_value=True), mock.patch.object(
            watcher, "_window_count", return_value=1
        ), mock.patch.object(
            watcher, "_signal", side_effect=lambda sig: signals.append(sig)
        ), mock.patch(
            "core.hyprfreeze.socket.socket"
        ) as sock:
            sock.return_value.__enter__.return_value.connect.side_effect = OSError
            result = watcher.run()
        self.assertEqual(result, 0)
        self.assertEqual(signals, [signal.SIGSTOP, signal.SIGCONT])


class MainGateTest(unittest.TestCase):
    def test_exits_without_hyprland_env(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "core.hyprfreeze.shutil.which", return_value="/usr/bin/hyprctl"
        ):
            self.assertEqual(main(["42"]), 1)

    def test_exits_without_hyprctl(self) -> None:
        with mock.patch.dict(os.environ, {"HYPRLAND_INSTANCE_SIGNATURE": "sig"}, clear=True), mock.patch(
            "core.hyprfreeze.shutil.which", return_value=None
        ):
            self.assertEqual(main(["42"]), 1)


if __name__ == "__main__":
    unittest.main()
