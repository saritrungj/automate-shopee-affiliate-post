from celery import Celery

from shopee_affiliate.config import get_settings

settings = get_settings()

celery_app = Celery(
    "shopee_affiliate",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["shopee_affiliate.tasks"],
)

celery_app.conf.timezone = "Asia/Bangkok"
celery_app.conf.beat_schedule = {
    "scrape-products-every-6-hours": {
        "task": "shopee_affiliate.tasks.scrape_products",
        "schedule": 60 * 60 * 6,
    },
    "poll-engagement-every-5-minutes": {
        "task": "shopee_affiliate.tasks.poll_engagement",
        "schedule": 60 * 5,
    },
    "rollup-analytics-daily": {
        "task": "shopee_affiliate.tasks.rollup_analytics",
        "schedule": 60 * 60 * 24,
    },
}

