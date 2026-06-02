from __future__ import annotations



from unsplash_wallpaper.constants import INTERVALS
from unsplash_wallpaper.services.scheduler_service import SchedulerService


class TestSchedulerService:
    def test_default_interval(self) -> None:
        sched = SchedulerService()
        assert sched.get_interval() == "1 hour"
        assert sched.get_interval_minutes() == 60

    def test_set_interval(self) -> None:
        sched = SchedulerService()
        sched.set_interval("15 minutes")
        assert sched.get_interval() == "15 minutes"
        assert sched.get_interval_minutes() == 15

        sched.set_interval("24 hours")
        assert sched.get_interval() == "24 hours"
        assert sched.get_interval_minutes() == 1440

    def test_start_stop(self) -> None:
        sched = SchedulerService()
        callback_count = 0

        def callback() -> None:
            nonlocal callback_count
            callback_count += 1

        sched.set_interval("15 minutes")
        sched.start(callback)
        assert sched.is_running is True

        sched.stop()
        assert sched.is_running is False

    def test_all_intervals(self) -> None:
        for label, minutes in INTERVALS.items():
            sched = SchedulerService()
            sched.set_interval(label)
            assert sched.get_interval_minutes() == minutes
            assert sched.get_interval() == label

    def test_multiple_start_stop(self) -> None:
        sched = SchedulerService()

        def callback() -> None:
            pass

        sched.start(callback)
        assert sched.is_running is True
        sched.stop()
        assert sched.is_running is False
        sched.start(callback)
        assert sched.is_running is True
        sched.stop()
        assert sched.is_running is False
