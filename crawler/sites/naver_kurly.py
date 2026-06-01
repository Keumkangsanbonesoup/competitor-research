from playwright.sync_api import Page

from base import BaseCrawler


class NaverKurlyCrawler(BaseCrawler):
    # 네이버 컬리N마트 홈
    PROMO_URL = "https://shopping.naver.com/kurlynmart/home"

    def __init__(self):
        super().__init__(
            site_key="naver_kurly",
            site_name="네이버 컬리N마트",
            promo_url=self.PROMO_URL,
        )

    def crawl(self, page: Page) -> dict:
        page.goto(self.promo_url, wait_until="domcontentloaded", timeout=30000)
        # 네이버는 JS 초기화가 느려서 추가 대기
        page.wait_for_timeout(5000)

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
