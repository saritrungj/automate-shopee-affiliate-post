# Installation Guide: Shopee Affiliate Automation

คู่มือนี้เรียงขั้นตอนติดตั้งแบบใช้งานจริงบน Windows/PowerShell สำหรับโปรเจกต์นี้:

- FastAPI รันบนเครื่อง local
- PostgreSQL และ Redis รันผ่าน Docker
- Ollama รัน local model
- OpenClaw เป็น LLM gateway

## 1. สิ่งที่ต้องติดตั้ง

ต้องมี:

- Python 3.11 ขึ้นไป
- Git
- Docker Desktop
- Node.js 22.14+ หรือ Node.js 24
- Ollama
- OpenClaw

Python dependencies จะติดตั้งจาก `pyproject.toml` เช่น FastAPI, Uvicorn, Celery, SQLAlchemy, Alembic, psycopg, Redis client, Pydantic, Jinja2, Pillow, HTTPX, Pytest, Ruff และ Mypy

## 2. เข้าโฟลเดอร์โปรเจกต์

```powershell
cd E:\git\automate-shopee-affiliate-post
```

ทุกคำสั่งต่อจากนี้ให้รันจากโฟลเดอร์นี้ ยกเว้นตอนที่บอกให้เปิด PowerShell หน้าต่างใหม่

## 3. สร้าง Python Virtual Environment

ตรวจ Python:

```powershell
python --version
```

ถ้ายังไม่มี Python ให้ติดตั้งจาก:

```text
https://www.python.org/downloads/
```

ตอนติดตั้งให้เลือก `Add python.exe to PATH`

สร้าง venv:

```powershell
python -m venv .venv
```

เปิดใช้งาน venv:

```powershell
.\.venv\Scripts\Activate.ps1
```

ถ้า PowerShell บล็อก script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

ติดตั้ง dependencies:

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

ตรวจว่า command หลักใช้ได้:

```powershell
uvicorn --version
alembic --version
pytest --version
```

## 4. ตั้งค่า `.env`

คัดลอกไฟล์ตัวอย่าง:

```powershell
Copy-Item .env.example .env
```

ถ้ารัน FastAPI บนเครื่อง Windows โดยตรง และใช้ PostgreSQL/Redis ผ่าน Docker ให้ `.env` เป็นแบบนี้:

```env
APP_ENV=local
SECRET_KEY=change-me
DATABASE_URL=postgresql+psycopg://shopee:shopee@localhost:5432/shopee_affiliate
REDIS_URL=redis://localhost:6379/0

LLM_GATEWAY=openclaw
OPENCLAW_BASE_URL=http://127.0.0.1:18789
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
LLM_FALLBACK_MODE=mock
AFFILIATE_DISCLOSURE_HASHTAG=#โฆษณา
```

สำคัญ:

- รัน app บนเครื่อง local: ใช้ DB host เป็น `localhost`
- รัน app ใน Docker Compose: ใช้ DB host เป็น `postgres`
- OpenClaw ของคุณรันที่ `127.0.0.1:18789`

## 5. เปิด PostgreSQL และ Redis

รัน:

```powershell
docker compose up -d postgres redis
```

ตรวจสถานะ:

```powershell
docker compose ps
```

ควรเห็น `postgres` และ `redis` เป็น running

ค่าเชื่อมต่อ PostgreSQL สำหรับ Navicat:

```text
Host: localhost
Port: 5432
Database: shopee_affiliate
User: shopee
Password: shopee
```

## 6. รัน Database Migration

ต้อง activate venv ก่อน:

```powershell
.\.venv\Scripts\Activate.ps1
```

รัน migration:

```powershell
alembic upgrade head
```

ถ้า `alembic` ไม่เจอ:

```powershell
python -m alembic upgrade head
```

ถ้า connect DB ไม่ได้ ให้ตรวจว่า `.env` ใช้:

```env
DATABASE_URL=postgresql+psycopg://shopee:shopee@localhost:5432/shopee_affiliate
```

และตรวจ container:

```powershell
docker compose ps
```

## 7. ติดตั้งและเปิด Ollama

ติดตั้งจาก:

```text
https://ollama.com/download
```

ตรวจ:

```powershell
ollama --version
```

โหลด model:

```powershell
ollama pull qwen3:8b
```

เปิด Ollama:

```powershell
ollama serve
```

ถ้าขึ้นว่า port ถูกใช้อยู่แล้ว แปลว่า Ollama service เปิดอยู่แล้ว ใช้ต่อได้

ทดสอบ:

```powershell
curl http://127.0.0.1:11434/api/tags
```

ควรเห็น `qwen3:8b` ในรายการ

## 8. ติดตั้งและเปิด OpenClaw

ติดตั้ง OpenClaw บน Windows:

```powershell
iwr -useb https://openclaw.ai/install.ps1 | iex
```

หรือผ่าน npm:

```powershell
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

ตรวจ:

```powershell
openclaw --version
openclaw doctor
```

ระหว่าง QuickStart แนะนำ:

- Channel: `ClickClack`
- Search provider: `Skip for now`
- Skill dependencies: `Skip for now`
- GOOGLE_PLACES_API_KEY: `No`
- OPENAI_API_KEY/openai-whisper: `No`
- ELEVENLABS_API_KEY/sag: `No`
- Hooks: `Skip for now`
- Hatch agent: `Hatch in Terminal`

ตรวจ gateway:

```powershell
openclaw gateway status
```

ควรเห็นประมาณนี้:

```text
Runtime: running
Connectivity probe: ok
Listening: 127.0.0.1:18789
```

เปิด dashboard:

```powershell
openclaw dashboard
```

ถ้า browser ขึ้น `Device pairing required` ให้ approve:

```powershell
openclaw devices list
openclaw devices approve <request-id>
```

ทดสอบ OpenClaw endpoint:

```powershell
curl http://127.0.0.1:18789/v1/models
```

หมายเหตุ: ถ้า OpenClaw ยังไม่เปิด แอปนี้ยังควรรันได้ เพราะตั้ง `LLM_FALLBACK_MODE=mock` ไว้ แต่ตอนกด `Run Campaign` ระบบจะใช้ mock output แทน local LLM

## 9. รัน FastAPI

ใน PowerShell ที่ activate venv แล้ว:

```powershell
uvicorn shopee_affiliate.main:app --reload
```

เปิดหน้าเว็บ:

```text
http://127.0.0.1:8000
```

ตรวจ health:

```powershell
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## 10. ถ้าเจอ Internal Server Error

โดยปกติ OpenClaw ไม่เปิดไม่ควรทำให้หน้า dashboard `/` พังทันที เพราะหน้าแรกอ่าน metrics จาก DB และแสดง config เท่านั้น

OpenClaw จะเกี่ยวตอน:

- กด `Run Campaign`
- เรียก `/api/campaigns/run`
- generate content/reply/classification

และแม้ตอนนั้น ถ้า `LLM_FALLBACK_MODE=mock` ระบบควร fallback เป็น mock output ได้

สาเหตุที่พบบ่อยของ `Internal Server Error`:

1. PostgreSQL ยังไม่เปิด
2. `.env` ใช้ DB host ผิด เช่นใช้ `postgres` ทั้งที่รัน app บนเครื่อง
3. ยังไม่ได้รัน `alembic upgrade head`
4. schema ใน DB เก่า หรือ migration ไม่ครบ
5. ค่า env ภาษาไทยเสีย encoding

ให้ดู stack trace ใน terminal ที่รัน `uvicorn` ก่อนเสมอ

เช็กทีละข้อ:

```powershell
docker compose ps
```

```powershell
Get-Content .env
```

ต้องเห็น:

```env
DATABASE_URL=postgresql+psycopg://shopee:shopee@localhost:5432/shopee_affiliate
AFFILIATE_DISCLOSURE_HASHTAG=#โฆษณา
```

รัน migration ซ้ำได้:

```powershell
alembic upgrade head
```

ลอง health:

```powershell
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

ถ้า `/healthz` ได้ แต่ `/readyz` พัง แปลว่าปัญหาอยู่ที่ DB

ถ้า `/healthz` และ `/readyz` ได้ แต่หน้า `/` พัง ให้ copy stack trace จาก terminal มาดูต่อ

## 11. ทดลอง Workflow แรก

เมื่อหน้าเว็บเปิดได้แล้ว กด `Run Campaign` บน Dashboard หรือเรียก:

```powershell
curl -X POST http://127.0.0.1:8000/api/campaigns/run `
  -H "Content-Type: application/json" `
  -d "{\"keywords\":[\"flash sale\"],\"platforms\":[\"facebook\"]}"
```

จากนั้นเปิด:

```text
http://127.0.0.1:8000/products
http://127.0.0.1:8000/content
http://127.0.0.1:8000/posts
http://127.0.0.1:8000/engagement
http://127.0.0.1:8000/prompts
```

## 12. รัน Celery Worker และ Beat

เปิด PowerShell หน้าต่างใหม่:

```powershell
cd E:\git\automate-shopee-affiliate-post
.\.venv\Scripts\Activate.ps1
```

รัน worker บน Windows ให้ใช้ `solo` pool:

```powershell
celery -A shopee_affiliate.celery_app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

หรือถ้าต้องการให้ทำงานพร้อมกันมากกว่า 1 งานบน Windows ให้ลองใช้ thread pool:

```powershell
celery -A shopee_affiliate.celery_app.celery_app worker --loglevel=INFO --pool=threads --concurrency=4
```

เปิด PowerShell อีกหน้าหนึ่ง:

```powershell
cd E:\git\automate-shopee-affiliate-post
.\.venv\Scripts\Activate.ps1
celery -A shopee_affiliate.celery_app.celery_app beat --loglevel=INFO
```

Celery ต้องใช้ Redis ดังนั้นต้องเปิด Redis ก่อน:

```powershell
docker compose up -d redis
```

ถ้าเห็น error แบบนี้บน Windows:

```text
PermissionError: [WinError 5] Access is denied
Pool process ... exited with 'exitcode 1'
```

แปลว่า Celery กำลังใช้ default `prefork` pool ซึ่งไม่เหมาะกับ Windows ให้หยุดด้วย `Ctrl+C` แล้วรันใหม่ด้วย `--pool=solo`

## 13. รันด้วย Docker Compose ทั้งระบบ

ถ้าต้องการให้ app, worker, beat, PostgreSQL, Redis รันใน Docker ให้ `.env` ใช้:

```env
DATABASE_URL=postgresql+psycopg://shopee:shopee@postgres:5432/shopee_affiliate
REDIS_URL=redis://redis:6379/0
OPENCLAW_BASE_URL=http://host.docker.internal:18789
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

รัน:

```powershell
docker compose up --build
```

ถ้าจะเปิด Ollama container ด้วย:

```powershell
docker compose --profile local-llm up --build
```

## 14. ทดสอบระบบ

```powershell
pytest
ruff check .
mypy src
docker compose config
```

## 15. Credentials สำหรับต่อ API จริง

ตอนนี้ระบบใช้ mock Shopee และ mock social publisher

ถ้าจะต่อของจริงภายหลัง ต้องเตรียม:

- Shopee Affiliate API key/secret
- Facebook Page Access Token
- Instagram Graph API token
- Twitter/X API credentials
- LINE Messaging API channel access token
- Cloudinary URL ถ้าจะอัปโหลดภาพขึ้น CDN

ค่าเหล่านี้อยู่ใน `.env.example` แล้ว แต่ adapter จริงยังต้อง implement เพิ่มก่อนใช้ production

## 16. วิธีหา Credential แต่ละแพลตฟอร์มแบบละเอียด

หมายเหตุสำคัญ: โปรเจกต์เวอร์ชันนี้ยังใช้ mock adapter สำหรับ Shopee และ social publisher อยู่ ค่า credential ด้านล่างเป็นการเตรียมไว้สำหรับขั้นตอนถัดไปเมื่อต้อง implement live adapter จริง ห้าม commit `.env` หรือ secret ใด ๆ ขึ้น Git

### 16.1 Shopee Affiliate API key/secret

ค่าที่ต้องการใน `.env`:

```env
SHOPEE_AFFILIATE_KEY=your_app_id_or_partner_id
SHOPEE_AFFILIATE_SECRET=your_secret_or_partner_key
```

สิ่งที่ต้องมีก่อน:

- บัญชี Shopee Affiliate ที่สมัครและผ่านเงื่อนไขแล้ว
- สิทธิ์เข้า Shopee Affiliate Portal หรือ Shopee Open Platform ในประเทศ/region ที่ใช้งาน
- ถ้าต้องใช้ API จริง บาง region อาจต้องขอเปิด API access เพิ่ม

วิธีหา:

1. เข้า Shopee Affiliate Portal หรือ Shopee Open Platform
2. มองหาเมนูประมาณ `Open API`, `API Access`, `Developer`, `App Management` หรือ `App List`
3. สร้าง app ใหม่ หรือเลือก app ที่มีอยู่
4. ในหน้า app detail ให้หา `App ID`, `Partner ID` หรือ `Affiliate App ID`
5. คัดลอกค่านี้ไปใส่ `SHOPEE_AFFILIATE_KEY`
6. หา `Secret`, `Secret Key`, `Partner Key` หรือ `App Secret`
7. คัดลอกค่านี้ไปใส่ `SHOPEE_AFFILIATE_SECRET`
8. ถ้ามีให้ตั้ง callback/redirect/webhook URL ให้ใส่ URL ของ backend ภายหลัง เช่น production domain

ทดสอบเบื้องต้น:

- ตอนนี้โปรเจกต์ยังไม่มี live Shopee adapter จึงยังไม่มี command ทดสอบ key โดยตรง
- ให้เก็บค่าไว้ใน `.env` ก่อน
- เมื่อ implement live adapter แล้วค่อยเพิ่ม endpoint เช่น `GET /api/integrations/shopee/health`

เอกสารอ้างอิง:

- Shopee Affiliate API Access: https://help.shopee.sg/portal/10/article/191702-API-Access
- Shopee Affiliate Portal: https://help.shopee.sg/portal/10/article/191692-Navigating-Shopee-Affiliate-Portal

### 16.2 Facebook Page Access Token

ค่าที่ต้องการใน `.env`:

```env
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token
```

สิ่งที่ต้องมีก่อน:

- Facebook Page ที่คุณเป็น admin หรือมีสิทธิ์จัดการ
- Meta Developer account
- Meta app ใน https://developers.facebook.com/
- Permission ที่มักเกี่ยวข้องกับ page publishing/management เช่น `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_metadata`
- ถ้าจะใช้กับผู้ใช้นอก app roles ต้องผ่าน App Review ตาม policy ของ Meta

วิธีหาแบบทดสอบด้วย Graph API Explorer:

1. เข้า https://developers.facebook.com/tools/explorer/
2. เลือก Meta app ของคุณด้านบน
3. กด `Generate Access Token`
4. เลือก permissions ที่ต้องใช้ เช่น `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `pages_manage_metadata`
5. Login และอนุญาตสิทธิ์
6. เรียก endpoint `GET /me/accounts`
7. ใน response จะเห็น Page แต่ละตัวพร้อม `access_token`
8. คัดลอก page access token ของ Page ที่ต้องการไปใส่ `FACEBOOK_PAGE_ACCESS_TOKEN`

ทดสอบด้วย curl:

```powershell
curl "https://graph.facebook.com/v24.0/me?fields=id,name&access_token=YOUR_PAGE_ACCESS_TOKEN"
```

ข้อควรระวัง:

- Token จาก Graph API Explorer มักมีอายุสั้น ใช้ทดสอบเท่านั้น
- Production ควรใช้ token flow ที่ถูกต้องและเก็บ token ใน secret manager
- อย่าใช้ user token แทน page token สำหรับการ publish ไป Page

เอกสารอ้างอิง:

- Meta Page Access Tokens: https://developers.facebook.com/docs/facebook-login/guides/access-tokens#pagetokens
- Graph API Explorer: https://developers.facebook.com/tools/explorer/

### 16.3 Instagram Graph API token

ค่าที่ต้องการใน `.env`:

```env
INSTAGRAM_ACCESS_TOKEN=your_meta_page_or_user_access_token_for_ig_graph
```

สิ่งที่ต้องมีก่อน:

- Instagram Professional account: Business หรือ Creator
- Instagram account ต้องเชื่อมกับ Facebook Page
- Meta Developer app
- สิทธิ์ของ Facebook Page ที่เชื่อมกับ Instagram account
- Permission สำหรับ Instagram Graph API เช่น `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`

วิธีหา Instagram Business Account ID และ token:

1. สร้างหรือเลือก Meta app
2. ไปที่ Graph API Explorer
3. Generate token พร้อม permissions ที่เกี่ยวข้อง
4. เรียก `GET /me/accounts`
5. เลือก Facebook Page ที่เชื่อมกับ Instagram
6. เรียก `GET /{page-id}?fields=instagram_business_account`
7. จด `instagram_business_account.id` ไว้ เพราะ live adapter ภายหลังจะต้องใช้ ID นี้
8. นำ token ที่ใช้เรียก Instagram Graph API ได้ไปใส่ `INSTAGRAM_ACCESS_TOKEN`

ทดสอบ:

```powershell
curl "https://graph.facebook.com/v24.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN"
```

ข้อควรระวัง:

- Instagram Graph API ใช้กับ Professional account ที่ผูกกับ Page ไม่ใช่ personal IG account
- Publishing media ต้องใช้ flow สร้าง media container แล้ว publish container
- Permission หลายตัวต้องผ่าน App Review ถ้าใช้กับบัญชีนอกทีม dev/test

เอกสารอ้างอิง:

- Instagram Content Publishing: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/content-publishing
- Meta Access Tokens: https://developers.facebook.com/docs/facebook-login/guides/access-tokens

### 16.4 Twitter/X API credentials

ค่าที่แนะนำใน `.env`:

```env
TWITTER_BEARER_TOKEN=your_bearer_token
```

ถ้าจะ publish จริงภายหลัง มักต้องเพิ่มค่าเหล่านี้ด้วย:

```env
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

สิ่งที่ต้องมีก่อน:

- X Developer account
- Project และ App ใน X Developer Portal
- Access tier ที่รองรับ endpoint ที่ต้องใช้
- ถ้าจะ post ต้องมี write permission และ user context token ไม่ใช่ bearer token อย่างเดียว

วิธีหา:

1. เข้า https://developer.x.com/
2. เปิด Developer Portal
3. สร้าง Project
4. สร้าง App ภายใต้ Project
5. ไปที่ app settings หรือ keys/tokens
6. คัดลอก `Bearer Token` ไปใส่ `TWITTER_BEARER_TOKEN`
7. ถ้าจะ post จริง ให้ตั้ง app permission เป็น read/write หรือ OAuth setting ตามที่ X กำหนด
8. สร้างหรือ generate `API Key`, `API Secret`, `Access Token`, `Access Token Secret`
9. ใส่ค่าเพิ่มใน `.env` ตามชื่อด้านบน

ทดสอบ Bearer token:

```powershell
curl "https://api.x.com/2/users/me" `
  -H "Authorization: Bearer YOUR_BEARER_TOKEN"
```

ข้อควรระวัง:

- Bearer token เหมาะกับ app-only/read หลายกรณี แต่การโพสต์มักต้องใช้ OAuth user context
- Free/Basic/Pro tier มี rate limit และ permission ต่างกัน
- X เปลี่ยนนโยบาย API บ่อย ให้ดู pricing/access tier ก่อนใช้งานจริง

เอกสารอ้างอิง:

- X API docs: https://docs.x.com/
- X Developer Platform: https://developer.x.com/en/docs/twitter-api

### 16.5 LINE Messaging API channel access token

ค่าที่ต้องการใน `.env`:

```env
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
```

สิ่งที่ต้องมีก่อน:

- LINE Business ID
- LINE Official Account
- Messaging API channel
- Provider ใน LINE Developers Console

วิธีสร้าง channel และหา token:

1. เข้า LINE Official Account Manager: https://manager.line.biz/
2. สร้าง LINE Official Account
3. เปิดใช้งาน Messaging API ให้ Official Account นั้น
4. ระบบจะสร้าง Messaging API channel ใน LINE Developers Console
5. เข้า LINE Developers Console: https://developers.line.biz/console/
6. เลือก provider
7. เลือก Messaging API channel
8. ไปที่ tab `Messaging API`
9. หา `Channel access token`
10. กด issue/reissue token
11. คัดลอกไปใส่ `LINE_CHANNEL_ACCESS_TOKEN`

ทดสอบ token:

```powershell
curl https://api.line.me/v2/bot/info `
  -H "Authorization: Bearer YOUR_LINE_CHANNEL_ACCESS_TOKEN"
```

ข้อควรระวัง:

- ตั้ง webhook URL ภายหลังเมื่อ backend มี public HTTPS URL
- ตอน dev บนเครื่อง local อาจต้องใช้ tunnel เช่น ngrok/cloudflared ถ้าจะรับ webhook จริง
- เก็บ channel secret แยกด้วยถ้าต้อง verify webhook signature ใน live adapter

เอกสารอ้างอิง:

- LINE Messaging API getting started: https://developers.line.biz/en/docs/messaging-api/getting-started/
- LINE issue channel access token v2.1: https://developers.line.biz/en/docs/messaging-api/generate-json-web-token/
- LINE Messaging API reference: https://developers.line.biz/en/reference/messaging-api/

### 16.6 Cloudinary URL สำหรับอัปโหลดภาพขึ้น CDN

ค่าที่ต้องการใน `.env`:

```env
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

สิ่งที่ต้องมีก่อน:

- Cloudinary account
- Product environment/cloud

วิธีหา:

1. เข้า https://console.cloudinary.com/
2. Login หรือสมัคร account
3. เปิด Console Dashboard
4. ไปที่ `Settings` หรือ `Product Environment Settings`
5. หา `Cloud name`, `API key`, `API secret`
6. ประกอบค่าเป็นรูปแบบ `cloudinary://API_KEY:API_SECRET@CLOUD_NAME`
7. นำไปใส่ `CLOUDINARY_URL`

ตัวอย่าง:

```env
CLOUDINARY_URL=cloudinary://123456789012345:abcdefg_secret@my-cloud-name
```

ข้อควรระวัง:

- `API secret` เป็น secret จริง ห้าม commit
- ตอนนี้โปรเจกต์ยัง generate ภาพไว้ local ใน `generated/` เป็นหลัก
- ต้อง implement Cloudinary upload adapter เพิ่มก่อนใช้ `CLOUDINARY_URL` ใน runtime จริง

เอกสารอ้างอิง:

- Cloudinary CLI/config docs: https://cloudinary.com/documentation/cloudinary_cli
- Cloudinary SDK docs: https://cloudinary.com/documentation/cloudinary_sdks

### 16.7 ตัวอย่าง `.env` เมื่อเตรียม credential ครบ

```env
SHOPEE_AFFILIATE_KEY=your_shopee_app_id
SHOPEE_AFFILIATE_SECRET=your_shopee_secret

FACEBOOK_PAGE_ACCESS_TOKEN=your_facebook_page_token
INSTAGRAM_ACCESS_TOKEN=your_instagram_graph_token

TWITTER_BEARER_TOKEN=your_x_bearer_token
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_user_access_token
X_ACCESS_TOKEN_SECRET=your_x_user_access_token_secret

LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token

CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

หลังแก้ `.env` ให้ restart process ที่อ่าน env:

```powershell
Ctrl+C
uvicorn shopee_affiliate.main:app --reload
```

และ restart Celery worker/beat ถ้าเปิดอยู่
