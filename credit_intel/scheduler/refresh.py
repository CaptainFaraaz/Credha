from __future__ import annotations
from apscheduler.schedulers.background import BackgroundScheduler
from credit_intel.utils.config import DATA_REFRESH_MINUTES
from credit_intel.api.main import refresh


_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = BackgroundScheduler()
    sched.add_job(refresh, "interval", minutes=DATA_REFRESH_MINUTES, id="refresh_job", max_instances=1, coalesce=True)
    sched.start()
    _scheduler = sched
    return sched