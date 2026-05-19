from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shopee_id: str
    title: str
    price: Decimal
    original_price: Decimal
    discount_pct: int
    rating: Decimal
    sold_count: int
    affiliate_link: str
    category: str
    shop_name: str
    score: Decimal


class ContentBundlePayload(BaseModel):
    platform: str
    headline: str = Field(max_length=120)
    post_body: str
    cta_text: str
    hashtags: list[str]
    comment_seed: str = ""
    quote_commentary: str = ""
    story_overlay_text: str = ""
    dm_reply_template: str = ""
    affiliate_link: str
    estimated_read_time_sec: int = 15
    ab_variant: str = "A"


class ContentBundleOut(ContentBundlePayload):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    status: str
    validation_errors: list[str]
    created_at: datetime


class CampaignRunRequest(BaseModel):
    campaign_id: str | None = None
    keywords: list[str] = Field(default_factory=lambda: ["flash sale"])
    platforms: list[str] = Field(default_factory=lambda: ["facebook", "instagram", "twitter", "line"])


class CampaignRunResponse(BaseModel):
    campaign_id: str
    product_count: int
    content_count: int
    post_count: int


class EngagementEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: str
    event_type: str
    content: str
    intent_label: str
    status: str
    reply_content: str


class PublishResponse(BaseModel):
    post_id: str
    platform_post_id: str
    post_url: HttpUrl | str
    status: str

