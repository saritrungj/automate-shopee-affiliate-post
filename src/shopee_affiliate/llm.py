import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from shopee_affiliate.config import get_settings


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    gateway: str
    status: str = "ok"
    latency_ms: int = 0
    error_message: str = ""


class OpenClawLLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> LLMResult:
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": f"ollama/{self.settings.ollama_model}",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        try:
            response = httpx.post(
                f"{self.settings.openclaw_base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            text = _extract_text(data)
            return LLMResult(
                text=text,
                model=self.settings.ollama_model,
                gateway="openclaw",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001 - recorded and optionally mocked
            return LLMResult(
                text="",
                model=self.settings.ollama_model,
                gateway="openclaw",
                status="error",
                latency_ms=int((time.perf_counter() - started) * 1000),
                error_message=str(exc),
            )


class MockLLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def content_json(self, product: dict[str, Any], platform: str) -> str:
        link = str(product["affiliate_link"])
        title = str(product["title"])
        hashtags = ["#shopee", "#ลดราคา", self.settings.affiliate_disclosure_hashtag]
        body = (
            f"🔥 {title} ลด {product['discount_pct']}%\n\n"
            f"คะแนน {product['rating']}/5 ขายแล้วกว่า {product['sold_count']} ชิ้น "
            "เหมาะสำหรับคนที่กำลังมองหาดีลคุ้ม ๆ บน Shopee\n\n"
            f"ดูรายละเอียดและสั่งซื้อได้ที่ {link}\n"
            f"{' '.join(hashtags)}"
        )
        data = {
            "platform": platform,
            "headline": f"{title} ดีลคุ้มวันนี้",
            "post_body": body,
            "cta_text": f"สั่งซื้อผ่าน Shopee ได้ที่ {link}",
            "hashtags": hashtags,
            "comment_seed": f"ลิงก์สินค้า: {link}",
            "quote_commentary": f"ดีลนี้น่าสนใจมาก ลด {product['discount_pct']}%\n{link}",
            "story_overlay_text": f"ลด {product['discount_pct']}%",
            "dm_reply_template": f"ดูรายละเอียดและราคาได้ที่ {link} นะคะ",
            "affiliate_link": link,
            "estimated_read_time_sec": 15,
            "ab_variant": "A",
        }
        return json.dumps(data, ensure_ascii=False)

    def reply_text(self, affiliate_link: str) -> str:
        return f"ดูรายละเอียดสินค้าและราคาล่าสุดได้ที่ลิงก์นี้เลยนะคะ {affiliate_link}"

    def summary_text(self) -> str:
        return "ยังไม่มีข้อมูลเพียงพอสำหรับสรุปเชิงลึก ระบบใช้สถิติพื้นฐานจากโพสต์และคลิกที่มีอยู่"


def _extract_text(data: dict[str, Any]) -> str:
    if "choices" in data:
        message = data["choices"][0].get("message", {})
        return str(message.get("content", ""))
    if "output_text" in data:
        return str(data["output_text"])
    return str(data)

