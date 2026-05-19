# Shopee Affiliate Automation

Local-first Shopee affiliate automation built from `agents.md`, `design.md`, and `llms.txt`.
The app uses FastAPI, Celery, PostgreSQL, Redis, server-rendered admin pages, and an OpenClaw
LLM gateway backed by Ollama. Shopee and social platform integrations are mocked by default so
the workflow can run before credentials are available.

## What Is Included

- FastAPI REST API and Jinja2 admin UI.
- Celery worker and beat schedules for scraping, content generation, publishing, engagement, and analytics.
- SQLAlchemy models and Alembic migration for products, content bundles, posts, engagement events, clicks, campaigns, prompt versions, approval events, and LLM runs.
- OpenClaw local LLM gateway client with deterministic mock fallback.
- Ollama-oriented config using `qwen3:8b`.
- Prompt files with repaired Thai disclosure text: `#โฆษณา`.
- Mock Shopee product scraping and mock social publishing.

## Local Setup

```powershell
Copy-Item .env.example .env
pip install -e ".[dev]"
uvicorn shopee_affiliate.main:app --reload
```

Open the admin UI at:

```text
http://127.0.0.1:8000
```

## OpenClaw + Ollama

Default LLM settings:

```env
LLM_GATEWAY=openclaw
OPENCLAW_BASE_URL=http://127.0.0.1:7331
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
LLM_FALLBACK_MODE=mock
```

Pull and run the default local model:

```powershell
ollama pull qwen3:8b
ollama serve
```

Then run OpenClaw with the local Ollama routing described in `openclaw/local-ollama.json`.
If OpenClaw is unavailable, the app records the failed LLM run and uses mock-safe output.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

To also start the optional Ollama service:

```powershell
docker compose --profile local-llm up --build
```

## API

- `POST /api/campaigns/run`
- `GET /api/products`
- `GET /api/content-bundles`
- `POST /api/content-bundles/{id}/approve`
- `POST /api/posts/{id}/publish`
- `GET /api/engagement-events`
- `POST /api/engagement-events/{id}/reply`
- `GET /healthz`
- `GET /readyz`

## Verification

```powershell
pytest
ruff check .
mypy src
docker compose config
curl http://127.0.0.1:11434/api/tags
```

## Notes

The initial scaffold is intentionally local-safe. Shopee, Facebook, Instagram, X, and LINE
tokens are listed in `.env.example`, but adapters remain mocked until live credentials and
platform approvals are added.
