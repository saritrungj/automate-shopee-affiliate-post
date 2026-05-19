from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from shopee_affiliate.db import Base


def new_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


JsonDict = MutableDict.as_mutable(JSON().with_variant(JSONB, "postgresql"))
JsonList = MutableList.as_mutable(JSON().with_variant(JSONB, "postgresql"))


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), default="Default Campaign")
    status: Mapped[str] = mapped_column(String(50), default="active")
    config: Mapped[dict[str, object]] = mapped_column(JsonDict, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    shopee_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    original_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_pct: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0)
    sold_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    image_url: Mapped[str] = mapped_column(Text, default="")
    affiliate_link: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(120), default="general")
    shop_name: Mapped[str] = mapped_column(String(200), default="Mock Shopee Store TH")
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    content_bundles: Mapped[list["ContentBundle"]] = relationship(back_populates="product")


class ContentBundle(Base):
    __tablename__ = "content_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    platform: Mapped[str] = mapped_column(String(40))
    headline: Mapped[str] = mapped_column(String(120), default="")
    post_body: Mapped[str] = mapped_column(Text)
    cta_text: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[list[str]] = mapped_column(JsonList, default=list)
    comment_seed: Mapped[str] = mapped_column(Text, default="")
    quote_commentary: Mapped[str] = mapped_column(Text, default="")
    story_overlay_text: Mapped[str] = mapped_column(String(80), default="")
    dm_reply_template: Mapped[str] = mapped_column(Text, default="")
    affiliate_link: Mapped[str] = mapped_column(Text)
    estimated_read_time_sec: Mapped[int] = mapped_column(Integer, default=15)
    ab_variant: Mapped[str] = mapped_column(String(5), default="A")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    validation_errors: Mapped[list[str]] = mapped_column(JsonList, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    product: Mapped[Product] = relationship(back_populates="content_bundles")
    posts: Mapped[list["Post"]] = relationship(back_populates="content_bundle")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    content_bundle_id: Mapped[str] = mapped_column(ForeignKey("content_bundles.id"))
    platform: Mapped[str] = mapped_column(String(40))
    platform_post_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    post_url: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="pending")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    reach: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    engagement_count: Mapped[int] = mapped_column(Integer, default=0)

    content_bundle: Mapped[ContentBundle] = relationship(back_populates="posts")
    engagement_events: Mapped[list["EngagementEvent"]] = relationship(back_populates="post")


class EngagementEvent(Base):
    __tablename__ = "engagement_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.id"))
    event_type: Mapped[str] = mapped_column(String(40), default="comment")
    platform_event_id: Mapped[str] = mapped_column(String(160), default="")
    content: Mapped[str] = mapped_column(Text)
    intent_label: Mapped[str] = mapped_column(String(60), default="NEUTRAL")
    status: Mapped[str] = mapped_column(String(40), default="new")
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_content: Mapped[str] = mapped_column(Text, default="")
    affiliate_link_included: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    post: Mapped[Post] = relationship(back_populates="engagement_events")


class LinkClick(Base):
    __tablename__ = "link_clicks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    affiliate_link: Mapped[str] = mapped_column(Text)
    post_id: Mapped[str | None] = mapped_column(ForeignKey("posts.id"), nullable=True)
    platform: Mapped[str] = mapped_column(String(40), default="")
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    metrics: Mapped[dict[str, object]] = mapped_column(JsonDict, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ApprovalEvent(Base):
    __tablename__ = "approval_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    content_bundle_id: Mapped[str] = mapped_column(ForeignKey("content_bundles.id"))
    action: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(120), default="admin")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class LLMRun(Base):
    __tablename__ = "llm_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    gateway: Mapped[str] = mapped_column(String(80), default="openclaw")
    prompt_version: Mapped[str] = mapped_column(String(40), default="v1.0")
    status: Mapped[str] = mapped_column(String(40), default="ok")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JsonDict, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

