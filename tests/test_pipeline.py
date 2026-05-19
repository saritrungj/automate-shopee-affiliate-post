from shopee_affiliate.agents import EngagementAgent, OrchestratorAgent, PostPublisherAgent, ReplyWriterAgent
from shopee_affiliate.db import SessionLocal
from shopee_affiliate.models import ContentBundle, EngagementEvent, Post, Product
from sqlalchemy import select


def test_full_mock_pipeline(client) -> None:
    with SessionLocal() as db:
        result = OrchestratorAgent().run_campaign(db, ["flash sale"], ["facebook"])

        assert result["product_count"] == 2
        assert db.scalar(select(Product)) is not None
        bundle = db.scalar(select(ContentBundle))
        assert bundle is not None
        assert "#โฆษณา" in bundle.hashtags

        post = db.scalar(select(Post))
        assert post is not None
        PostPublisherAgent().publish(db, post)
        assert post.status == "published"

        events = EngagementAgent().ingest_mock_events(db)
        assert events
        ReplyWriterAgent().reply(db, events[0])
        assert events[0].status == "replied"
        assert db.scalar(select(EngagementEvent)) is not None


def test_api_campaign_and_admin_pages(client) -> None:
    response = client.post(
        "/api/campaigns/run",
        json={"keywords": ["flash sale"], "platforms": ["facebook"]},
    )
    assert response.status_code == 200
    assert response.json()["content_count"] == 2

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Dashboard" in dashboard.text

    content = client.get("/content")
    assert content.status_code == 200
    assert "Content Approval" in content.text

