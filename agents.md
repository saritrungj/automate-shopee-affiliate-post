# Agents Architecture — Shopee Affiliate Automation System

## Overview

This document defines the multi-agent system responsible for automating Shopee affiliate content generation, posting, engagement, and link distribution across social platforms.

---

## Agent Roster

### 1. `OrchestratorAgent`
**Role:** Master controller — coordinates all agents, manages task queues, handles retries and scheduling.

**Responsibilities:**
- Receives trigger events (cron, webhook, manual)
- Routes tasks to appropriate sub-agents
- Monitors agent health and output quality
- Aggregates logs and reports

**Inputs:** Trigger signal, product list, campaign config  
**Outputs:** Task dispatches to sub-agents  
**LLM Required:** No (pure orchestration logic)  
**Stack:** Python + Celery + Redis

---

### 2. `ProductScraperAgent`
**Role:** Fetches product data from Shopee via affiliate API or scraping fallback.

**Responsibilities:**
- Calls Shopee Affiliate API to get product metadata (title, price, rating, images, category)
- Generates affiliate tracking links via Shopee's link generator
- Deduplicates and caches product data
- Flags low-quality or unavailable products

**Inputs:** Product IDs or category keywords  
**Outputs:** Structured product JSON with affiliate link  
**LLM Required:** No  
**Stack:** Python + httpx + Shopee Affiliate API + Redis cache

```json
// Output Schema
{
  "product_id": "123456789",
  "title": "Nike Air Max 270",
  "price": 2490,
  "original_price": 3200,
  "discount_pct": 22,
  "rating": 4.8,
  "sold_count": 15200,
  "image_url": "https://...",
  "affiliate_link": "https://shope.ee/xxxxx",
  "category": "shoes",
  "shop_name": "Nike Official Store TH"
}
```

---

### 3. `ContentWriterAgent`
**Role:** Core LLM agent — generates all post content, CTAs, captions, and comments.

**Responsibilities:**
- Writes main post body (product description + hook + CTA)
- Generates platform-specific variants (Facebook, Twitter/X, Instagram, TikTok, LINE)
- Writes reply templates for common questions
- Generates quote-tweet / quote-post commentary
- Supports Thai and English output
- A/B variant generation for testing

**Inputs:** Product JSON, platform target, tone config, CTA style  
**Outputs:** `ContentBundle` object per platform  
**LLM Required:** ✅ Claude 3.5 Sonnet  
**Stack:** Anthropic SDK + prompt templates

```json
// ContentBundle Schema
{
  "platform": "facebook",
  "post_body": "...",
  "headline": "...",
  "cta_text": "🛒 ซื้อเลย ราคาพิเศษ!",
  "hashtags": ["#shopee", "#ลดราคา", "#nike"],
  "comment_starters": ["ใครสนใจทักมาเลยนะ!", "..."],
  "quote_commentary": "...",
  "affiliate_link": "https://shope.ee/xxxxx",
  "image_prompt": "product flat-lay on white background..."
}
```

**Prompt Strategy:**
- System prompt sets persona: enthusiastic, trustworthy Thai affiliate blogger
- Few-shot examples per platform
- CTA library injected as context
- Output forced to JSON via structured output

---

### 4. `ImageGeneratorAgent`
**Role:** Creates or enhances product visuals for posts.

**Responsibilities:**
- Generates promotional banners using product image + price overlay
- Creates lifestyle mockup images via image generation API
- Adds discount badges, urgency labels ("เหลือน้อย!", "Flash Sale")
- Resizes/crops for each platform's spec

**Inputs:** Product image URL, discount info, platform dimensions  
**Outputs:** Processed image files / URLs  
**LLM Required:** Optional (for image gen)  
**Stack:** Pillow (overlays) + Cloudinary (CDN) + optional: Stable Diffusion / DALL-E 3

---

### 5. `PostPublisherAgent`
**Role:** Publishes content to social media platforms via APIs.

**Responsibilities:**
- Posts to Facebook Pages / Groups via Graph API
- Posts to Twitter/X via v2 API
- Posts to Instagram via Instagram Graph API
- Posts to LINE OA via LINE Messaging API
- Schedules posts with optimal timing windows
- Handles rate limits and retry logic

**Inputs:** `ContentBundle`, target platform, schedule config  
**Outputs:** Post ID, URL, timestamp  
**LLM Required:** No  
**Stack:** Python + platform SDKs + APScheduler

---

### 6. `EngagementAgent`
**Role:** Monitors and responds to engagement on published posts.

**Responsibilities:**
- Polls for new comments, mentions, DMs
- Classifies intent: question / interest / negative / spam
- Routes to `ReplyWriterAgent` for response generation
- Auto-likes and reacts to positive engagement
- Shares post to relevant groups on trigger

**Inputs:** Post IDs, engagement events  
**Outputs:** Engagement action queue  
**LLM Required:** ✅ (classification)  
**Stack:** Platform webhooks + polling + Claude Haiku for classification

---

### 7. `ReplyWriterAgent`
**Role:** Generates contextual replies to comments and DMs.

**Responsibilities:**
- Answers product questions using product knowledge base
- Handles price inquiries, shipping questions, availability
- Writes friendly CTA-embedded replies ("ลิงก์อยู่ด้านบนเลยนะคะ 🛒")
- Generates quote-reply content when mentioned
- Detects and flags negative sentiment for human review

**Inputs:** Comment/DM text, product context, conversation history  
**Outputs:** Reply text  
**LLM Required:** ✅ Claude 3.5 Haiku (speed-optimized)  
**Stack:** Anthropic SDK + conversation memory (Redis)

---

### 8. `AnalyticsAgent`
**Role:** Tracks performance metrics and feeds data back to optimize content.

**Responsibilities:**
- Collects click-through rates on affiliate links (via UTM + Shopee dashboard)
- Tracks engagement rates per post variant
- Identifies top-performing CTAs, hooks, hashtags
- Feeds performance signals back to `ContentWriterAgent` context
- Generates daily/weekly performance reports

**Inputs:** Post IDs, affiliate link click data, engagement metrics  
**Outputs:** Performance reports, optimization signals  
**LLM Required:** Optional (for report summarization)  
**Stack:** SQLite / PostgreSQL + Metabase / custom dashboard

---

## Agent Communication Flow

```
Cron / Manual Trigger
        │
        ▼
OrchestratorAgent
    │         │
    ▼         ▼
ProductScraper  AnalyticsAgent (reads historical data)
    │
    ▼
ContentWriterAgent ◄─── CTA Library, Brand Voice Config
    │
    ▼
ImageGeneratorAgent
    │
    ▼
PostPublisherAgent ──► Facebook / X / Instagram / LINE
    │
    ▼
EngagementAgent (polls for interactions)
    │
    ▼
ReplyWriterAgent ──► Auto-replies with affiliate link CTAs
    │
    ▼
AnalyticsAgent (ingests results, updates performance DB)
```

---

## Scheduling Strategy

| Task | Frequency | Agent |
|---|---|---|
| Scrape new products | Every 6 hours | ProductScraperAgent |
| Generate posts | 2x daily | ContentWriterAgent |
| Publish posts | 8AM, 12PM, 7PM | PostPublisherAgent |
| Poll engagement | Every 5 minutes | EngagementAgent |
| Auto-reply | Real-time (on event) | ReplyWriterAgent |
| Analytics report | Daily 9AM | AnalyticsAgent |

---

## Error Handling & Guardrails

- All agents emit structured logs to centralized logger (Loguru + file/Loki)
- Failed posts queued for retry with exponential backoff
- Sentiment guardrail: replies flagged as negative escalated to human inbox
- Rate limit budgets tracked per platform per agent
- Daily spend cap on LLM tokens (configurable)
- Human-in-the-loop override available at any stage via admin dashboard
