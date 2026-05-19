from decimal import Decimal
from math import log10
from urllib.parse import urlencode


def build_affiliate_link(product_id: str, platform: str, campaign_id: str, variant_id: str) -> str:
    query = urlencode(
        {
            "utm_source": platform,
            "utm_medium": "affiliate",
            "utm_campaign": campaign_id,
            "utm_content": variant_id,
        }
    )
    return f"https://shope.ee/{product_id}?{query}"


def score_product(
    discount_pct: int,
    rating: Decimal,
    commission_rate: Decimal,
    review_count: int,
) -> Decimal:
    review_count_log = Decimal(str(log10(max(review_count, 1))))
    score = (
        Decimal(discount_pct) * Decimal("0.3")
        + rating * Decimal("0.25")
        + commission_rate * Decimal("0.3")
        + review_count_log * Decimal("0.15")
    )
    return score.quantize(Decimal("0.01"))


class MockPlatformPublisher:
    def publish(self, platform: str, body: str) -> dict[str, str]:
        suffix = abs(hash((platform, body))) % 1_000_000
        return {
            "platform_post_id": f"mock-{platform}-{suffix}",
            "post_url": f"https://mock.social/{platform}/posts/{suffix}",
        }

