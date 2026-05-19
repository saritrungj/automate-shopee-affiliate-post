from sqlalchemy import select

from shopee_affiliate.agents import (
    AnalyticsAgent,
    ContentWriterAgent,
    EngagementAgent,
    ImageGeneratorAgent,
    OrchestratorAgent,
    PostPublisherAgent,
    ProductScraperAgent,
    ReplyWriterAgent,
)
from shopee_affiliate.celery_app import celery_app
from shopee_affiliate.db import SessionLocal, create_db
from shopee_affiliate.models import ContentBundle, EngagementEvent, Post, Product


@celery_app.task(name="shopee_affiliate.tasks.scrape_products")
def scrape_products() -> int:
    create_db()
    with SessionLocal() as db:
        products = ProductScraperAgent().scrape(db, ["flash sale"], "celery")
        return len(products)


@celery_app.task(name="shopee_affiliate.tasks.generate_content")
def generate_content(platform: str = "facebook") -> int:
    create_db()
    with SessionLocal() as db:
        products = db.scalars(select(Product)).all()
        writer = ContentWriterAgent()
        for product in products:
            writer.generate(db, product, platform)
        return len(products)


@celery_app.task(name="shopee_affiliate.tasks.generate_images")
def generate_images() -> int:
    with SessionLocal() as db:
        bundles = db.scalars(select(ContentBundle)).all()
        image_agent = ImageGeneratorAgent()
        for bundle in bundles:
            image_agent.generate_banner(bundle)
        return len(bundles)


@celery_app.task(name="shopee_affiliate.tasks.schedule_publish")
def schedule_publish() -> int:
    with SessionLocal() as db:
        bundles = db.scalars(select(ContentBundle).where(ContentBundle.status.in_(["draft", "approved"]))).all()
        publisher = PostPublisherAgent()
        for bundle in bundles:
            publisher.schedule(db, bundle)
        return len(bundles)


@celery_app.task(name="shopee_affiliate.tasks.poll_engagement")
def poll_engagement() -> int:
    with SessionLocal() as db:
        return len(EngagementAgent().ingest_mock_events(db))


@celery_app.task(name="shopee_affiliate.tasks.write_reply")
def write_reply(event_id: str) -> str:
    with SessionLocal() as db:
        event = db.get(EngagementEvent, event_id)
        if event is None:
            return "missing"
        ReplyWriterAgent().reply(db, event)
        return event.status


@celery_app.task(name="shopee_affiliate.tasks.rollup_analytics")
def rollup_analytics() -> dict[str, object]:
    with SessionLocal() as db:
        return AnalyticsAgent().rollup(db)


@celery_app.task(name="shopee_affiliate.tasks.run_campaign")
def run_campaign() -> dict[str, int | str]:
    create_db()
    with SessionLocal() as db:
        return OrchestratorAgent().run_campaign(
            db,
            keywords=["flash sale"],
            platforms=["facebook", "instagram", "twitter", "line"],
        )


@celery_app.task(name="shopee_affiliate.tasks.publish_post")
def publish_post(post_id: str) -> str:
    with SessionLocal() as db:
        post = db.get(Post, post_id)
        if post is None:
            return "missing"
        PostPublisherAgent().publish(db, post)
        return post.status

