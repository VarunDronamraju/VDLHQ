import structlog
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = structlog.get_logger()

# Singleton scheduler
scheduler = AsyncIOScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"misfire_grace_time": 60, "coalesce": True},
)


def start_scheduler():
    if not scheduler.running:
        logger.info("starting_apscheduler")

        # Import jobs here to avoid circular imports
        from app.scheduler.jobs import register_all_jobs

        # Register all Phase 9 jobs
        register_all_jobs(scheduler)

        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        logger.info("stopping_apscheduler")
        scheduler.shutdown()
