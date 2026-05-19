# System Design — Shopee Affiliate Automation Platform

## 1. System Goals

Build a fully automated pipeline that:
1. Discovers high-converting Shopee products
2. Generates platform-native affiliate content (posts, captions, CTAs)
3. Publishes across Facebook, Instagram, Twitter/X, LINE OA
4. Engages with audiences: replies, quote-posts, comment seeding, link sharing
5. Measures affiliate click performance and self-optimizes

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     ADMIN DASHBOARD                      │
│         (Campaign config, approval queue, metrics)        │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   ORCHESTRATION LAYER                    │
│              Celery Workers + Redis Queue                 │
└───┬──────────┬──────────┬──────────┬────────────────────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
[Scraper]  [AI Core]  [Publisher] [Engagement]
    │          │          │          │
    ▼          ▼          ▼          ▼
Shopee API  Anthropic  Platform    Webhook
+ Cache     Claude API  APIs       Listeners
    │          │          │          │
    └──────────┴──────────┴──────────┘
                          │
               ┌──────────▼──────────┐
               │    PostgreSQL DB     │
               │  + Redis + S3/CDN   │
               └─────────────────────┘
```

---

## 3. Core Modules

### 3.1 Data Ingestion Module

**Purpose:** Pull product data from Shopee and prepare it for content generation.

**Components:**
- `ShopeeAPIClient` — wraps Shopee Affiliate Open Platform API
- `LinkGenerator` — creates trackable affiliate URLs with custom UTM params
- `ProductFilter` — scores and ranks products by: discount %, rating, sales velocity, commission rate
- `ProductCache` — Redis TTL cache (6h) to avoid redundant API calls

**Product Scoring Formula:**
```
score = (discount_pct * 0.3) + (rating * 0.25) + (commission_rate * 0.3) + (review_count_log * 0.15)
```

**Affiliate Link Pattern:**
```
Base: https://shope.ee/{product_id}
UTM:  ?utm_source={platform}&utm_medium=affiliate&utm_campaign={campaign_id}&utm_content={variant_id}
```

---

### 3.2 AI Content Generation Module

**Purpose:** Transform raw product data into platform-specific viral content.

**Pipeline:**
```
Product JSON
    │
    ▼
PromptBuilder ──► injects: product data, CTA library, platform rules, tone persona
    │
    ▼
Claude API (claude-sonnet-4-20250514)
    │
    ▼
ContentParser ──► validates JSON schema, detects missing fields
    │
    ▼
ContentBundle ──► stored in DB, ready for publishing
```

**Content Types Generated Per Product:**

| Type | Description | Platform |
|---|---|---|
| Main Post | Full description + hook + CTA + link | All |
| Short Caption | 1-2 line punchy version | Instagram, Twitter/X |
| Story Text | Swipe-up style CTA overlay text | IG Stories |
| Comment Seed | First comment with affiliate link | Facebook |
| Quote Commentary | Commentary for quote-retweet / quote-post | Twitter/X |
| DM Reply Template | For "ราคาเท่าไหร่?" type inquiries | All |
| GROUP Post | Formatted for Facebook group posting | Facebook |

**CTA Framework (AIDA-based):**
```
Attention  → Hook line (price drop, limited stock, viral angle)
Interest   → Key benefits, social proof (X คนซื้อแล้ว, ⭐4.8)
Desire     → Emotional trigger (คุ้มมากก, ต้องมี!)
Action     → Direct CTA + affiliate link
```

**Example Post Structure (Thai):**
```
🔥 [HOOK: ลดแรงมาก! Nike Air Max ลด 22%]

[INTEREST: รองเท้าขายดีอันดับ 1 บน Shopee ⭐4.8 
มีคนซื้อไปแล้วกว่า 15,000 คู่!]

[DESIRE: ใส่สบาย ดีไซน์เก๋ เหมาะทุกโอกาส]

✅ ราคาปกติ: ฿3,200
💰 ราคาพิเศษ: ฿2,490

🛒 ซื้อได้เลยที่ลิงก์นี้ 👇
https://shope.ee/xxxxx

#nike #shopee #รองเท้า #ลดราคา #affiliate
```

---

### 3.3 Publishing Module

**Purpose:** Deliver content to each platform at the right time.

**Platform Adapters:**

| Platform | API | Auth Method | Content Limits |
|---|---|---|---|
| Facebook Page | Graph API v19+ | Page Access Token | 63,206 chars |
| Facebook Group | Graph API | User Token | Same |
| Instagram | IG Graph API | Business Account Token | 2,200 chars |
| Twitter/X | API v2 | OAuth 2.0 / Bearer | 280 chars |
| LINE OA | Messaging API | Channel Access Token | 5,000 chars |

**Scheduling Strategy:**
```
Peak Engagement Windows (Thailand TZ: UTC+7):
  Morning:   07:00 – 09:00  (commute browsing)
  Lunch:     11:30 – 13:00  (lunch break)
  Evening:   19:00 – 22:00  (post-work peak)

Flash Sale Targeting:
  Shopee Flash Sale: 00:00, 12:00 → post 30 min before
```

**Publishing Queue:**
```python
class PublishTask:
    content_bundle_id: str
    platform: Platform
    scheduled_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    status: Literal["pending", "published", "failed"]
```

---

### 3.4 Engagement Automation Module

**Purpose:** Simulate natural human engagement to boost algorithmic reach and drive clicks.

**Actions Automated:**

1. **Comment Seeding**
   - Posts first comment with affiliate link + CTA on own posts
   - Adds emoji reactions
   - Seeds 2-3 follow-up comments from secondary accounts (optional)

2. **Reply Automation**
   - Detects comment intent via Claude Haiku classification
   - Auto-replies within 60 seconds for high-intent signals
   - Embeds affiliate link naturally in reply

3. **Quote Posting**
   - Monitors mentions and shares
   - Generates quote-post commentary that adds value
   - Re-amplifies top-performing posts with fresh angle

4. **Group Sharing**
   - Identifies relevant Facebook groups (shopping, deals, category-specific)
   - Auto-shares with group-adapted post variant
   - Respects group posting frequency limits

**Comment Classification (Claude Haiku):**
```
Labels: [HIGH_INTENT, QUESTION_PRICE, QUESTION_SHIPPING, 
         QUESTION_QUALITY, NEGATIVE, SPAM, NEUTRAL]

Routing:
  HIGH_INTENT      → reply with direct affiliate link + urgency CTA
  QUESTION_PRICE   → reply with price + link
  QUESTION_SHIP    → reply with shipping info + link
  QUESTION_QUALITY → reply with rating/reviews context + link
  NEGATIVE         → flag for human review
  SPAM             → ignore / hide
  NEUTRAL          → optional friendly reply
```

---

### 3.5 Analytics & Optimization Module

**Purpose:** Track ROI, measure content performance, and feed signals back to improve generation.

**Metrics Tracked:**

| Metric | Source | Frequency |
|---|---|---|
| Affiliate link clicks | Shopee dashboard + UTM | Hourly |
| Post reach / impressions | Platform APIs | Daily |
| Engagement rate | Platform APIs | Daily |
| Comment-to-click rate | Computed | Daily |
| Revenue / commission | Shopee Affiliate | Daily |
| Top-performing CTAs | Internal DB | Weekly |
| Best posting times | Platform insights | Weekly |

**Feedback Loop:**
```
AnalyticsAgent reads top-performing posts
    │
    ▼
Extracts: hooks, CTA phrases, hashtags, post lengths that drove highest CTR
    │
    ▼
Injects as "performance context" into ContentWriterAgent system prompt
    │
    ▼
ContentWriter biases future generation toward proven patterns
```

---

## 4. Database Schema (PostgreSQL)

```sql
-- Products
CREATE TABLE products (
  id UUID PRIMARY KEY,
  shopee_id VARCHAR NOT NULL UNIQUE,
  title TEXT,
  price DECIMAL,
  original_price DECIMAL,
  discount_pct INT,
  rating DECIMAL,
  sold_count INT,
  affiliate_link TEXT,
  category VARCHAR,
  score DECIMAL,
  last_scraped_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Content Bundles
CREATE TABLE content_bundles (
  id UUID PRIMARY KEY,
  product_id UUID REFERENCES products(id),
  platform VARCHAR,
  post_body TEXT,
  headline TEXT,
  cta_text TEXT,
  hashtags TEXT[],
  affiliate_link TEXT,
  variant CHAR(1) DEFAULT 'A', -- A/B testing
  created_at TIMESTAMP DEFAULT NOW()
);

-- Posts
CREATE TABLE posts (
  id UUID PRIMARY KEY,
  content_bundle_id UUID REFERENCES content_bundles(id),
  platform VARCHAR,
  platform_post_id VARCHAR,
  status VARCHAR DEFAULT 'pending',
  published_at TIMESTAMP,
  error_message TEXT,
  reach INT,
  impressions INT,
  engagement_count INT
);

-- Engagement Events
CREATE TABLE engagement_events (
  id UUID PRIMARY KEY,
  post_id UUID REFERENCES posts(id),
  event_type VARCHAR, -- comment, reply, share, like
  platform_event_id VARCHAR,
  content TEXT,
  intent_label VARCHAR,
  replied_at TIMESTAMP,
  reply_content TEXT,
  affiliate_link_included BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Performance
CREATE TABLE link_clicks (
  id UUID PRIMARY KEY,
  affiliate_link TEXT,
  post_id UUID,
  platform VARCHAR,
  clicked_at TIMESTAMP,
  converted BOOLEAN DEFAULT FALSE,
  commission_amount DECIMAL
);
```

---

## 5. Infrastructure & Deployment

```
┌─────────────────────────────────────┐
│         Docker Compose Stack         │
├─────────────────────────────────────┤
│  app          FastAPI backend        │
│  worker       Celery workers (x4)    │
│  beat         Celery Beat scheduler  │
│  redis        Task queue + cache     │
│  postgres     Primary database       │
│  dashboard    Metabase / Grafana     │
│  nginx        Reverse proxy          │
└─────────────────────────────────────┘

Cloud: Railway / Render / VPS (DigitalOcean)
CDN:   Cloudinary (image hosting)
Secrets: .env + Railway secrets manager
```

---

## 6. Security & Compliance

- All platform tokens stored encrypted (Fernet) in secrets manager
- Shopee affiliate API keys rotated every 90 days
- Rate limit budgets enforced per platform per hour
- No fake engagement from third-party accounts (platform ToS)
- Content moderation: no misleading price claims, no spam
- Thai consumer protection law compliance: clear affiliate disclosure
- Affiliate disclosure label appended to all posts: `#โฆษณา #Affiliate`
