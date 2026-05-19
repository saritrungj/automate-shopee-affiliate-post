import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shopee_affiliate.config import get_settings
from shopee_affiliate.guardrails import validate_content_bundle
from shopee_affiliate.integrations import MockPlatformPublisher, build_affiliate_link, score_product
from shopee_affiliate.llm import MockLLMClient, OpenClawLLMClient
from shopee_affiliate.models import (
    ApprovalEvent,
    Campaign,
    ContentBundle,
    EngagementEvent,
    LLMRun,
    Post,
    Product,
    PromptVersion,
    now_utc,
)
from shopee_affiliate.prompts import PromptStore
from shopee_affiliate.schemas import ContentBundlePayload


def _record_llm_run(db: Session, agent: str, result_status: str, error: str, latency_ms: int) -> None:
    settings = get_settings()
    db.add(
        LLMRun(
            agent=agent,
            model=settings.ollama_model,
            gateway=settings.llm_gateway,
            status=result_status,
            error_message=error,
            latency_ms=latency_ms,
        )
    )


class ProductScraperAgent:
    def scrape(self, db: Session, keywords: list[str], campaign_id: str) -> list[Product]:
        seed = keywords[0] if keywords else "flash sale"
        raw_products = [
            {
                "shopee_id": "100001",
                "title": f"{seed.title()} Wireless Earbuds",
                "price": Decimal("399"),
                "original_price": Decimal("699"),
                "discount_pct": 43,
                "rating": Decimal("4.8"),
                "sold_count": 15200,
                "review_count": 6400,
                "commission_rate": Decimal("8.5"),
                "category": "electronics",
                "shop_name": "Shopee Mall Audio TH",
            },
            {
                "shopee_id": "100002",
                "title": f"{seed.title()} Mini Blender",
                "price": Decimal("289"),
                "original_price": Decimal("490"),
                "discount_pct": 41,
                "rating": Decimal("4.7"),
                "sold_count": 8300,
                "review_count": 2100,
                "commission_rate": Decimal("7.0"),
                "category": "home",
                "shop_name": "Kitchen Deals TH",
            },
        ]
        products: list[Product] = []
        for item in raw_products:
            link = build_affiliate_link(item["shopee_id"], "multi", campaign_id, "A")
            product = db.scalar(select(Product).where(Product.shopee_id == item["shopee_id"]))
            if product is None:
                product = Product(shopee_id=item["shopee_id"], affiliate_link=link, title=item["title"])
                db.add(product)
            for key, value in item.items():
                setattr(product, key, value)
            product.affiliate_link = link
            product.score = score_product(
                int(item["discount_pct"]),
                Decimal(item["rating"]),
                Decimal(item["commission_rate"]),
                int(item["review_count"]),
            )
            product.last_scraped_at = now_utc()
            products.append(product)
        db.commit()
        return products


class ContentWriterAgent:
    def __init__(self) -> None:
        self.prompts = PromptStore()
        self.openclaw = OpenClawLLMClient()
        self.mock = MockLLMClient()

    def generate(self, db: Session, product: Product, platform: str) -> ContentBundle:
        product_json = self._product_json(product)
        system = self.prompts.load("content_writer", "v1.0_system.txt")
        user = self.prompts.load("content_writer", "v1.0_user.txt").format(
            product_json=json.dumps(product_json, ensure_ascii=False),
            platform=platform,
            tone="energetic",
            cta_style="social-proof",
            language="mixed",
            performance_hints="Use clear price drop, rating, and affiliate disclosure.",
            affiliate_link=product.affiliate_link,
        )
        result = self.openclaw.generate(system, user, temperature=0.8)
        _record_llm_run(db, "ContentWriterAgent", result.status, result.error_message, result.latency_ms)
        raw = result.text if result.status == "ok" and result.text.strip() else ""
        payload = self._parse_or_mock(raw, product_json, platform)
        errors = validate_content_bundle(payload, product.affiliate_link)
        status = "needs_review" if errors else "draft"
        bundle = ContentBundle(
            product_id=product.id,
            platform=payload.platform,
            headline=payload.headline,
            post_body=payload.post_body,
            cta_text=payload.cta_text,
            hashtags=payload.hashtags,
            comment_seed=payload.comment_seed,
            quote_commentary=payload.quote_commentary,
            story_overlay_text=payload.story_overlay_text,
            dm_reply_template=payload.dm_reply_template,
            affiliate_link=payload.affiliate_link,
            estimated_read_time_sec=payload.estimated_read_time_sec,
            ab_variant=payload.ab_variant,
            status=status,
            validation_errors=errors,
        )
        db.add(bundle)
        db.commit()
        db.refresh(bundle)
        return bundle

    def _parse_or_mock(
        self, raw: str, product_json: dict[str, Any], platform: str
    ) -> ContentBundlePayload:
        try:
            return ContentBundlePayload.model_validate_json(raw)
        except Exception:
            mock_json = self.mock.content_json(product_json, platform)
            return ContentBundlePayload.model_validate_json(mock_json)

    @staticmethod
    def _product_json(product: Product) -> dict[str, Any]:
        return {
            "product_id": product.shopee_id,
            "title": product.title,
            "price": str(product.price),
            "original_price": str(product.original_price),
            "discount_pct": product.discount_pct,
            "rating": str(product.rating),
            "sold_count": product.sold_count,
            "image_url": product.image_url,
            "affiliate_link": product.affiliate_link,
            "category": product.category,
            "shop_name": product.shop_name,
        }


class ImageGeneratorAgent:
    SIZES = {
        "facebook": (1200, 630),
        "instagram": (1080, 1080),
        "twitter": (1200, 675),
        "line": (1040, 1040),
    }

    def generate_banner(self, bundle: ContentBundle) -> Path:
        settings = get_settings()
        width, height = self.SIZES.get(bundle.platform, (1200, 630))
        image = Image.new("RGB", (width, height), "#ff6b35")
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 40, width - 40, height - 40), outline="#ffffff", width=6)
        draw.text((70, 80), bundle.headline[:60], fill="#ffffff")
        draw.text((70, height - 140), bundle.cta_text[:80], fill="#ffffff")
        path = settings.generated_dir / f"{bundle.id}-{bundle.platform}.jpg"
        image.save(path, quality=90)
        return path


class PostPublisherAgent:
    def __init__(self) -> None:
        self.publisher = MockPlatformPublisher()

    def schedule(self, db: Session, bundle: ContentBundle) -> Post:
        post = Post(content_bundle_id=bundle.id, platform=bundle.platform, scheduled_at=now_utc())
        db.add(post)
        db.commit()
        db.refresh(post)
        return post

    def publish(self, db: Session, post: Post) -> Post:
        result = self.publisher.publish(post.platform, post.content_bundle.post_body)
        post.platform_post_id = result["platform_post_id"]
        post.post_url = result["post_url"]
        post.status = "published"
        post.published_at = datetime.now(UTC)
        db.commit()
        db.refresh(post)
        return post


class EngagementAgent:
    LABELS = {
        "price": "QUESTION_PRICE",
        "ราคา": "QUESTION_PRICE",
        "ส่ง": "QUESTION_SHIPPING",
        "shipping": "QUESTION_SHIPPING",
        "ดีไหม": "QUESTION_QUALITY",
        "quality": "QUESTION_QUALITY",
        "ซื้อ": "HIGH_INTENT",
        "buy": "HIGH_INTENT",
        "โกง": "NEGATIVE",
        "แย่": "NEGATIVE",
        "spam": "SPAM",
    }

    def classify(self, text: str) -> str:
        lowered = text.lower()
        for needle, label in self.LABELS.items():
            if needle in lowered:
                return label
        return "NEUTRAL"

    def ingest_mock_events(self, db: Session) -> list[EngagementEvent]:
        posts = db.scalars(select(Post).where(Post.status == "published")).all()
        events: list[EngagementEvent] = []
        for post in posts:
            exists = db.scalar(select(EngagementEvent).where(EngagementEvent.post_id == post.id))
            if exists:
                continue
            content = "ราคาเท่าไหร่คะ สนใจค่ะ"
            event = EngagementEvent(
                post_id=post.id,
                platform_event_id=f"mock-comment-{post.id}",
                content=content,
                intent_label=self.classify(content),
                status="needs_reply",
            )
            db.add(event)
            events.append(event)
        db.commit()
        return events


class ReplyWriterAgent:
    def __init__(self) -> None:
        self.prompts = PromptStore()
        self.openclaw = OpenClawLLMClient()
        self.mock = MockLLMClient()

    def reply(self, db: Session, event: EngagementEvent) -> EngagementEvent:
        bundle = event.post.content_bundle
        product = bundle.product
        system = self.prompts.load("reply_writer", "v1.0_system.txt")
        user = self.prompts.load("reply_writer", "v1.0_user.txt").format(
            product_json=json.dumps(ContentWriterAgent._product_json(product), ensure_ascii=False),
            original_post_text=bundle.post_body,
            comment_text=event.content,
            intent_label=event.intent_label,
            affiliate_link=bundle.affiliate_link,
        )
        result = self.openclaw.generate(system, user, temperature=0.5)
        _record_llm_run(db, "ReplyWriterAgent", result.status, result.error_message, result.latency_ms)
        text = result.text.strip() if result.status == "ok" else ""
        if not text:
            text = self.mock.reply_text(bundle.affiliate_link)
        event.reply_content = text[:1000]
        event.affiliate_link_included = bundle.affiliate_link in event.reply_content
        event.replied_at = now_utc()
        event.status = "human_review" if event.intent_label == "NEGATIVE" else "replied"
        db.commit()
        db.refresh(event)
        return event


class AnalyticsAgent:
    def rollup(self, db: Session) -> dict[str, object]:
        return {
            "products": db.scalar(select(func.count(Product.id))) or 0,
            "content_bundles": db.scalar(select(func.count(ContentBundle.id))) or 0,
            "published_posts": db.scalar(select(func.count(Post.id)).where(Post.status == "published")) or 0,
            "engagement_events": db.scalar(select(func.count(EngagementEvent.id))) or 0,
            "summary": MockLLMClient().summary_text(),
        }


class OrchestratorAgent:
    def run_campaign(
        self, db: Session, keywords: list[str], platforms: list[str], campaign_id: str | None = None
    ) -> dict[str, int | str]:
        campaign = self._get_or_create_campaign(db, campaign_id)
        products = ProductScraperAgent().scrape(db, keywords, campaign.id)
        writer = ContentWriterAgent()
        publisher = PostPublisherAgent()
        image_agent = ImageGeneratorAgent()
        content_count = 0
        post_count = 0
        for product in products:
            for platform in platforms:
                bundle = writer.generate(db, product, platform)
                image_agent.generate_banner(bundle)
                post = publisher.schedule(db, bundle)
                content_count += 1
                post_count += 1 if post else 0
        return {
            "campaign_id": campaign.id,
            "product_count": len(products),
            "content_count": content_count,
            "post_count": post_count,
        }

    def _get_or_create_campaign(self, db: Session, campaign_id: str | None) -> Campaign:
        if campaign_id:
            campaign = db.get(Campaign, campaign_id)
            if campaign:
                return campaign
        campaign = Campaign(name="Local OpenClaw Campaign", config={"llm": "openclaw", "runtime": "ollama"})
        db.add(campaign)
        self._seed_prompt_versions(db)
        db.commit()
        db.refresh(campaign)
        return campaign

    def _seed_prompt_versions(self, db: Session) -> None:
        for agent, path in {
            "content_writer": "prompts/content_writer/v1.0_system.txt",
            "reply_writer": "prompts/reply_writer/v1.0_system.txt",
            "classifier": "prompts/classifier/v1.0_user.txt",
        }.items():
            exists = db.scalar(select(PromptVersion).where(PromptVersion.agent == agent))
            if not exists:
                db.add(PromptVersion(agent=agent, version="v1.0", path=path, active=True))

