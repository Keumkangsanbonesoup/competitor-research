from playwright.sync_api import Page

from base import BaseCrawler


class CoupangCrawler(BaseCrawler):
    # 쿠팡 기획전·이벤트 메인 페이지
    PROMO_URL = "https://www.coupang.com/np/campaigns/"

    def __init__(self):
        super().__init__(
            site_key="coupang",
            site_name="쿠팡",
            promo_url=self.PROMO_URL,
        )

    def crawl(self, page: Page) -> dict:
        page.goto(self.promo_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # KV 영역(최초 화면) 스크린샷 → AI 분석용
        kv_shot = self.take_viewport_screenshot(page, "kv")
        # 전체 페이지 스크린샷 → 아카이브용
        full_shot = self.take_screenshot(page, "full")

        images = self.extract_large_images(page)
        page_text = self.extract_visible_text(page)

        return {
            "site": self.site_key,
            "site_name": self.site_name,
            "crawled_at": self.crawled_at,
            "url": self.promo_url,
            "screenshot": kv_shot,
            "full_screenshot": full_shot,
            "page_images": images,
            "page_text": page_text,
        }
