from pathlib import Path

from decimal import Decimal

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from shopee_affiliate.agents import (
    AnalyticsAgent,
    EngagementAgent,
    OrchestratorAgent,
    PostPublisherAgent,
    ReplyWriterAgent,
)
from shopee_affiliate.config import get_settings
from shopee_affiliate.db import create_db, get_db
from shopee_affiliate.integrations import build_affiliate_link, score_product
from shopee_affiliate.models import (
    ApprovalEvent,
    ContentBundle,
    EngagementEvent,
    Post,
    Product,
    PromptVersion,
)
from shopee_affiliate.schemas import CampaignRunRequest, CampaignRunResponse, ContentBundleOut

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Shopee Affiliate Automation", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def on_startup() -> None:
    create_db()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(select(Product.id).limit(1))
    return {"status": "ready"}


@app.post("/api/campaigns/run", response_model=CampaignRunResponse)
def run_campaign(payload: CampaignRunRequest, db: Session = Depends(get_db)) -> dict[str, int | str]:
    return OrchestratorAgent().run_campaign(db, payload.keywords, payload.platforms, payload.campaign_id)


@app.get("/api/products")
def products(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    rows = db.scalars(select(Product).order_by(desc(Product.created_at))).all()
    return [
        {
            "id": row.id,
            "shopee_id": row.shopee_id,
            "title": row.title,
            "price": str(row.price),
            "discount_pct": row.discount_pct,
            "rating": str(row.rating),
            "score": str(row.score),
        }
        for row in rows
    ]


@app.get("/api/content-bundles", response_model=list[ContentBundleOut])
def content_bundles(db: Session = Depends(get_db)) -> list[ContentBundle]:
    return list(db.scalars(select(ContentBundle).order_by(desc(ContentBundle.created_at))).all())


@app.post("/api/content-bundles/{bundle_id}/approve")
def approve_content(bundle_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    bundle = db.get(ContentBundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Content bundle not found")
    bundle.status = "approved"
    db.add(ApprovalEvent(content_bundle_id=bundle.id, action="approved"))
    db.commit()
    return {"status": "approved", "id": bundle.id}


@app.post("/api/posts/{post_id}/publish")
def publish_post(post_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    published = PostPublisherAgent().publish(db, post)
    return {
        "post_id": published.id,
        "platform_post_id": published.platform_post_id or "",
        "post_url": published.post_url,
        "status": published.status,
    }


@app.get("/api/engagement-events")
def engagement_events(db: Session = Depends(get_db)) -> list[dict[str, str]]:
    events = db.scalars(select(EngagementEvent).order_by(desc(EngagementEvent.created_at))).all()
    return [
        {
            "id": event.id,
            "post_id": event.post_id,
            "intent_label": event.intent_label,
            "status": event.status,
            "content": event.content,
            "reply_content": event.reply_content,
        }
        for event in events
    ]


@app.post("/api/engagement-events/{event_id}/reply")
def reply_to_event(event_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    event = db.get(EngagementEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Engagement event not found")
    ReplyWriterAgent().reply(db, event)
    return {"status": event.status, "reply_content": event.reply_content}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    metrics = AnalyticsAgent().rollup(db)
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"metrics": metrics, "settings": settings},
    )


@app.post("/admin/run")
def admin_run(
    keywords: str = Form("flash sale"),
    platforms: str = Form("facebook,instagram,twitter,line"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    OrchestratorAgent().run_campaign(
        db,
        keywords=[part.strip() for part in keywords.split(",") if part.strip()],
        platforms=[part.strip() for part in platforms.split(",") if part.strip()],
    )
    return RedirectResponse("/", status_code=303)


@app.get("/products", response_class=HTMLResponse)
def admin_products(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    rows = db.scalars(select(Product).order_by(desc(Product.score))).all()
    return templates.TemplateResponse(request, "products.html", {"products": rows})


@app.post("/products")
def admin_create_product(
    shopee_id: str = Form(...),
    title: str = Form(...),
    price: Decimal = Form(...),
    original_price: Decimal = Form(...),
    discount_pct: int = Form(0),
    rating: Decimal = Form(0),
    sold_count: int = Form(0),
    review_count: int = Form(1),
    commission_rate: Decimal = Form(0),
    category: str = Form("general"),
    shop_name: str = Form("Manual Store"),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    existing = db.scalar(select(Product).where(Product.shopee_id == shopee_id))
    if existing:
        product = existing
    else:
        product = Product(
            shopee_id=shopee_id,
            title=title,
            affiliate_link=build_affiliate_link(shopee_id, "manual", "manual", "A"),
        )
        db.add(product)
    product.title = title
    product.price = price
    product.original_price = original_price
    product.discount_pct = discount_pct
    product.rating = rating
    product.sold_count = sold_count
    product.review_count = review_count
    product.commission_rate = commission_rate
    product.category = category
    product.shop_name = shop_name
    product.score = score_product(discount_pct, rating, commission_rate, review_count)
    db.commit()
    return RedirectResponse("/products", status_code=303)


@app.post("/products/{product_id}/update")
def admin_update_product(
    product_id: str,
    title: str = Form(...),
    price: Decimal = Form(...),
    original_price: Decimal = Form(...),
    discount_pct: int = Form(0),
    rating: Decimal = Form(0),
    sold_count: int = Form(0),
    review_count: int = Form(1),
    commission_rate: Decimal = Form(0),
    category: str = Form("general"),
    shop_name: str = Form("Manual Store"),
    available: bool = Form(False),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.title = title
    product.price = price
    product.original_price = original_price
    product.discount_pct = discount_pct
    product.rating = rating
    product.sold_count = sold_count
    product.review_count = review_count
    product.commission_rate = commission_rate
    product.category = category
    product.shop_name = shop_name
    product.available = available
    product.score = score_product(discount_pct, rating, commission_rate, review_count)
    db.commit()
    return RedirectResponse("/products", status_code=303)


@app.post("/products/{product_id}/delete")
def admin_delete_product(product_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    bundles = db.scalars(select(ContentBundle).where(ContentBundle.product_id == product.id)).all()
    for bundle in bundles:
        posts = db.scalars(select(Post).where(Post.content_bundle_id == bundle.id)).all()
        for post in posts:
            events = db.scalars(select(EngagementEvent).where(EngagementEvent.post_id == post.id)).all()
            for event in events:
                db.delete(event)
            db.delete(post)
        db.delete(bundle)
    db.delete(product)
    db.commit()
    return RedirectResponse("/products", status_code=303)


@app.get("/content", response_class=HTMLResponse)
def admin_content(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    rows = db.scalars(select(ContentBundle).order_by(desc(ContentBundle.created_at))).all()
    return templates.TemplateResponse(request, "content.html", {"bundles": rows})


@app.post("/content/{bundle_id}/approve")
def admin_approve_content(bundle_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    approve_content(bundle_id, db)
    return RedirectResponse("/content", status_code=303)


@app.post("/content/{bundle_id}/update")
def admin_update_content(
    bundle_id: str,
    headline: str = Form(...),
    post_body: str = Form(...),
    cta_text: str = Form(""),
    status: str = Form("draft"),
    hashtags: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    bundle = db.get(ContentBundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Content bundle not found")
    bundle.headline = headline
    bundle.post_body = post_body
    bundle.cta_text = cta_text
    bundle.status = status
    bundle.hashtags = [part.strip() for part in hashtags.split(",") if part.strip()]
    db.commit()
    return RedirectResponse("/content", status_code=303)


@app.post("/content/{bundle_id}/delete")
def admin_delete_content(bundle_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    bundle = db.get(ContentBundle, bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Content bundle not found")
    posts = db.scalars(select(Post).where(Post.content_bundle_id == bundle.id)).all()
    for post in posts:
        events = db.scalars(select(EngagementEvent).where(EngagementEvent.post_id == post.id)).all()
        for event in events:
            db.delete(event)
        db.delete(post)
    db.delete(bundle)
    db.commit()
    return RedirectResponse("/content", status_code=303)


@app.get("/posts", response_class=HTMLResponse)
def admin_posts(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    rows = db.scalars(select(Post).order_by(desc(Post.scheduled_at))).all()
    return templates.TemplateResponse(request, "posts.html", {"posts": rows})


@app.post("/posts/{post_id}/publish")
def admin_publish_post(post_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    publish_post(post_id, db)
    return RedirectResponse("/posts", status_code=303)


@app.post("/posts/{post_id}/update")
def admin_update_post(
    post_id: str,
    status: str = Form("pending"),
    platform_post_id: str = Form(""),
    post_url: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = status
    post.platform_post_id = platform_post_id or None
    post.post_url = post_url
    db.commit()
    return RedirectResponse("/posts", status_code=303)


@app.post("/posts/{post_id}/delete")
def admin_delete_post(post_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    events = db.scalars(select(EngagementEvent).where(EngagementEvent.post_id == post.id)).all()
    for event in events:
        db.delete(event)
    db.delete(post)
    db.commit()
    return RedirectResponse("/posts", status_code=303)


@app.get("/engagement", response_class=HTMLResponse)
def admin_engagement(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    EngagementAgent().ingest_mock_events(db)
    rows = db.scalars(select(EngagementEvent).order_by(desc(EngagementEvent.created_at))).all()
    return templates.TemplateResponse(request, "engagement.html", {"events": rows})


@app.post("/engagement/{event_id}/reply")
def admin_reply(event_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    reply_to_event(event_id, db)
    return RedirectResponse("/engagement", status_code=303)


@app.post("/engagement/{event_id}/update")
def admin_update_engagement(
    event_id: str,
    intent_label: str = Form("NEUTRAL"),
    status: str = Form("new"),
    reply_content: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    event = db.get(EngagementEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Engagement event not found")
    event.intent_label = intent_label
    event.status = status
    event.reply_content = reply_content
    db.commit()
    return RedirectResponse("/engagement", status_code=303)


@app.post("/engagement/{event_id}/delete")
def admin_delete_engagement(event_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    event = db.get(EngagementEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Engagement event not found")
    db.delete(event)
    db.commit()
    return RedirectResponse("/engagement", status_code=303)


@app.get("/prompts", response_class=HTMLResponse)
def admin_prompts(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    rows = db.scalars(select(PromptVersion).order_by(PromptVersion.agent)).all()
    settings = get_settings()
    return templates.TemplateResponse(
        request,
        "prompts.html",
        {"prompts": rows, "settings": settings},
    )


@app.post("/prompts")
def admin_create_prompt(
    agent: str = Form(...),
    version: str = Form("v1.0"),
    path: str = Form(...),
    active: bool = Form(False),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    db.add(PromptVersion(agent=agent, version=version, path=path, active=active))
    db.commit()
    return RedirectResponse("/prompts", status_code=303)


@app.post("/prompts/{prompt_id}/update")
def admin_update_prompt(
    prompt_id: str,
    agent: str = Form(...),
    version: str = Form("v1.0"),
    path: str = Form(...),
    active: bool = Form(False),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    prompt = db.get(PromptVersion, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt.agent = agent
    prompt.version = version
    prompt.path = path
    prompt.active = active
    db.commit()
    return RedirectResponse("/prompts", status_code=303)


@app.post("/prompts/{prompt_id}/delete")
def admin_delete_prompt(prompt_id: str, db: Session = Depends(get_db)) -> RedirectResponse:
    prompt = db.get(PromptVersion, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    db.delete(prompt)
    db.commit()
    return RedirectResponse("/prompts", status_code=303)
