from shopee_affiliate.config import get_settings
from shopee_affiliate.schemas import ContentBundlePayload


MAX_POST_LENGTH = {
    "facebook": 5000,
    "twitter": 280,
    "instagram": 2200,
    "line": 5000,
}

FORBIDDEN_PHRASES = [
    "รับประกัน 100%",
    "รวยแน่นอน",
    "ไม่ต้องทำอะไรก็รวย",
    "สินค้าของแท้ 100%",
]


def validate_content_bundle(bundle: ContentBundlePayload, expected_link: str) -> list[str]:
    settings = get_settings()
    errors: list[str] = []
    limit = MAX_POST_LENGTH.get(bundle.platform, 5000)

    if len(bundle.post_body) > limit:
        errors.append(f"post_body exceeds {limit} characters for {bundle.platform}")
    if not bundle.post_body.strip():
        errors.append("post_body is required")
    if bundle.affiliate_link != expected_link:
        errors.append("affiliate link was modified")
    if settings.affiliate_disclosure_hashtag not in bundle.hashtags:
        errors.append(f"missing disclosure hashtag {settings.affiliate_disclosure_hashtag}")
    if not any(link in bundle.post_body for link in [expected_link, bundle.affiliate_link]):
        errors.append("post_body must include affiliate link")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in bundle.post_body:
            errors.append(f"forbidden phrase: {phrase}")
    return errors

