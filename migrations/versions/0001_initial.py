"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("shopee_id", sa.String(length=80), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_pct", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False),
        sa.Column("sold_count", sa.Integer(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("affiliate_link", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("shop_name", sa.String(length=200), nullable=False),
        sa.Column("score", sa.Numeric(8, 2), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_products_shopee_id", "products", ["shopee_id"])
    op.create_table(
        "content_bundles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("headline", sa.String(length=120), nullable=False),
        sa.Column("post_body", sa.Text(), nullable=False),
        sa.Column("cta_text", sa.Text(), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=False),
        sa.Column("comment_seed", sa.Text(), nullable=False),
        sa.Column("quote_commentary", sa.Text(), nullable=False),
        sa.Column("story_overlay_text", sa.String(length=80), nullable=False),
        sa.Column("dm_reply_template", sa.Text(), nullable=False),
        sa.Column("affiliate_link", sa.Text(), nullable=False),
        sa.Column("estimated_read_time_sec", sa.Integer(), nullable=False),
        sa.Column("ab_variant", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("content_bundle_id", sa.String(length=36), sa.ForeignKey("content_bundles.id"), nullable=False),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("platform_post_id", sa.String(length=160), nullable=True),
        sa.Column("post_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("reach", sa.Integer(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("engagement_count", sa.Integer(), nullable=False),
    )
    op.create_table(
        "engagement_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("post_id", sa.String(length=36), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("platform_event_id", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent_label", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reply_content", sa.Text(), nullable=False),
        sa.Column("affiliate_link_included", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "link_clicks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("affiliate_link", sa.Text(), nullable=False),
        sa.Column("post_id", sa.String(length=36), sa.ForeignKey("posts.id"), nullable=True),
        sa.Column("platform", sa.String(length=40), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("converted", sa.Boolean(), nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "approval_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("content_bundle_id", sa.String(length=36), sa.ForeignKey("content_bundles.id"), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "llm_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("gateway", sa.String(length=80), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("llm_runs")
    op.drop_table("approval_events")
    op.drop_table("prompt_versions")
    op.drop_table("link_clicks")
    op.drop_table("engagement_events")
    op.drop_table("posts")
    op.drop_table("content_bundles")
    op.drop_index("ix_products_shopee_id", table_name="products")
    op.drop_table("products")
    op.drop_table("campaigns")

