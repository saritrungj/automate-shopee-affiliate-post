from decimal import Decimal

from shopee_affiliate.agents import EngagementAgent
from shopee_affiliate.guardrails import validate_content_bundle
from shopee_affiliate.integrations import build_affiliate_link, score_product
from shopee_affiliate.prompts import PromptStore
from shopee_affiliate.schemas import ContentBundlePayload


def test_affiliate_link_contains_utm_fields() -> None:
    link = build_affiliate_link("123", "facebook", "camp-1", "A")

    assert link.startswith("https://shope.ee/123?")
    assert "utm_source=facebook" in link
    assert "utm_campaign=camp-1" in link


def test_product_scoring_formula() -> None:
    score = score_product(40, Decimal("4.8"), Decimal("8.0"), 1000)

    assert score == Decimal("16.05")


def test_guardrails_require_disclosure_and_exact_link() -> None:
    payload = ContentBundlePayload(
        platform="facebook",
        headline="Deal",
        post_body="ซื้อเลย https://shope.ee/123",
        cta_text="ซื้อเลย",
        hashtags=["#shopee"],
        affiliate_link="https://shope.ee/123",
    )

    errors = validate_content_bundle(payload, "https://shope.ee/123")

    assert "missing disclosure hashtag #โฆษณา" in errors


def test_prompt_loading() -> None:
    text = PromptStore().load("content_writer", "v1.0_system.txt")

    assert "#โฆษณา" in text


def test_classifier_rule_fallback() -> None:
    classifier = EngagementAgent()

    assert classifier.classify("ราคาเท่าไหร่คะ") == "QUESTION_PRICE"
    assert classifier.classify("อยากซื้อครับ") == "HIGH_INTENT"
    assert classifier.classify("hello") == "NEUTRAL"
