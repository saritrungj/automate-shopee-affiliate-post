# OpenClaw + Ollama Local LLM Setup

This project treats OpenClaw as the LLM gateway and Ollama as the local runtime.
The application calls:

```text
POST {OPENCLAW_BASE_URL}/v1/chat/completions
model: ollama/{OLLAMA_MODEL}
```

Default local settings:

```env
LLM_GATEWAY=openclaw
OPENCLAW_BASE_URL=http://127.0.0.1:7331
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b
LLM_FALLBACK_MODE=mock
```

Recommended local flow:

```powershell
ollama pull qwen3:8b
ollama serve
```

Start OpenClaw using `openclaw/local-ollama.json` and point it at the Ollama server.
If OpenClaw or Ollama is unavailable, the app records the failed LLM run and uses deterministic mock output so automation can still be tested without cloud calls.

