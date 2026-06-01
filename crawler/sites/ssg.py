from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG 크롤러.
    이벤트 메인 페이지 → 진행 중인 이벤트 목록 → 상세 수집.
    """
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                // SSG 이벤트 카드 구조
                const selectors = [
                    '.evnt_list a',
                    '.event_list a',
                    '[class*="evnt"] a',
                    '[class*="event_item"] a',
                    'ul.lst_event li a',
                    'a[href*="/event/eventDetail"]',
                    'a[href*="/event/"]',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(a => {
                        if (seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        const title = (img?.alt || a.innerText || '').trim();
                        if (!title || !a.href || !a.href.startsWith('http')) return;
                        seen.add(a.href);
                        results.push({ title: title.slice(0, 60), url: a.href });
                    });
                });
                return results.slice(0, 8);
            }
        """)

        return promos
