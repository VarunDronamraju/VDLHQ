from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import structlog

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
        from app.jobs.inactivity_scanner import scan_inactive_leads
        
        # Add jobs
        scheduler.add_job(
            scan_inactive_leads,
            "interval",
            hours=1,
            id="inactivity_scanner",
            replace_existing=True
        )
        
        scheduler.start()

def stop_scheduler():
    if scheduler.running:
        logger.info("stopping_apscheduler")
        scheduler.shutdown()
