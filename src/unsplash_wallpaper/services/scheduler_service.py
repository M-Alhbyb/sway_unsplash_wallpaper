from __future__ import annotations

import logging
from typing import Any

import gi
gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")

from gi.repository import GLib

from unsplash_wallpaper.constants import INTERVALS

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self) -> None:
        self._timer_id: int | None = None
        self._interval_minutes: int = 60
        self._callback = None
        self._running = False

    def set_interval(self, interval_label: str) -> None:
        minutes = INTERVALS.get(interval_label, 60)
        self._interval_minutes = minutes
        logger.info("Scheduler interval set to %s (%d minutes)", interval_label, minutes)
        if self._running:
            self.stop()
            self.start()

    def get_interval(self) -> str:
        for label, minutes in INTERVALS.items():
            if minutes == self._interval_minutes:
                return label
        return "1 hour"

    def get_interval_minutes(self) -> int:
        return self._interval_minutes

    def start(self, callback) -> None:
        self._callback = callback
        self._running = True
        milliseconds = self._interval_minutes * 60 * 1000
        self._timer_id = GLib.timeout_add(milliseconds, self._tick)
        logger.info(
            "Scheduler started with %d minute interval",
            self._interval_minutes,
        )

    def stop(self) -> None:
        self._running = False
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        logger.info("Scheduler stopped")

    def _tick(self) -> bool:
        if not self._running:
            return False
        if self._callback:
            try:
                self._callback()
            except Exception as e:
                logger.error("Scheduler callback error: %s", e)
        return self._running

    @property
    def is_running(self) -> bool:
        return self._running
