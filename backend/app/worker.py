"""Background scheduler: `python -m app.worker` (runs in its own container in docker-compose).
Single lightweight loop; a Postgres advisory lock guarantees only one worker runs jobs at a time."""
import logging
import signal
import time

from sqlalchemy import text

from .db import SessionLocal, engine
from .services.automation import JOBS, is_due, run_job
from .services.settings_store import get_automation

TICK_SECONDS = 30
log = logging.getLogger("gst.worker")
_stop = False


def tick() -> list[str]:
    ran: list[str] = []
    with SessionLocal() as db:
        locked = True
        if engine.dialect.name == "postgresql":
            locked = bool(db.scalar(text("select pg_try_advisory_lock(738221)")))
        if not locked:
            log.info("another worker holds the lock; skipping tick")
            return ran
        try:
            dry = get_automation(db).dry_run
            for name in JOBS:
                if is_due(db, name):
                    run_job(db, name, dry_run=dry, trigger="schedule")
                    ran.append(name)
        finally:
            if engine.dialect.name == "postgresql":
                db.execute(text("select pg_advisory_unlock(738221)"))
                db.commit()
    return ran


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__("_stop", True))
    signal.signal(signal.SIGINT, lambda *_: globals().__setitem__("_stop", True))
    log.info("GST worker started (tick=%ss)", TICK_SECONDS)
    while not _stop:
        try:
            ran = tick()
            if ran:
                log.info("tick ran: %s", ran)
        except Exception:
            log.exception("tick failed; will retry")  # DB temporarily down etc.
        for _ in range(TICK_SECONDS):
            if _stop:
                break
            time.sleep(1)
    log.info("GST worker stopped")


if __name__ == "__main__":
    main()
