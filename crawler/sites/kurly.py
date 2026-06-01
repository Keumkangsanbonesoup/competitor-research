from playwright.sync_api import Page

from base import BaseCrawler


class KurlyCrawler(BaseCrawler):
    # 컬리 마켓이벤트 페이지 (매주 업데이트되므로 URL 변경 필요 시 여기서 수정)
    PROMO_URL = "https://event.kurly.com/lego/event/2025/0623/market-event"

    def __init__(self):
        super().__init__(
            site_key="kurly",
            site_name="마켓컬리",
            promo_url=self.PROMO_URL,
        )

    def crawl(self, page: Page) -> dict:
        page.goto(self.promo_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        kv_shot = self.take_viewport_screenshot(page, "kv")
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
