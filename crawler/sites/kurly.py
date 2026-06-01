from playwright.sync_api import Page

from base import BaseCrawler


class KurlyCrawler(BaseCrawler):
    """
    마켓컬리 크롤러.
    이벤트 목록 페이지 → 진행 중인 이벤트 개별 수집.
    """
    LISTING_URL = "https://www.kurly.com/shop/event/eventList.php"

    def __init__(self):
        super().__init__("kurly", "마켓컬리", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # 이벤트 카드 링크 추출 (컬리 이벤트 목록 구조)
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                // 컬리 이벤트 목록: .event_list li a, [class*='event'] a 등
                const selectors = [
                    '.event_list li a',
                    '[class*="event-list"] a',
                    '[class*="EventList"] a',
                    'ul li a[href*="/shop/event/"]',
                    'ul li a[href*="event.kurly.com"]',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(a => {
                        if (seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        const title = img?.alt || a.innerText.trim();
                        if (!title || !a.href) return;
                        seen.add(a.href);
                        results.push({ title: title.slice(0, 60), url: a.href });
                    });
                });
                return results.slice(0, 8);
            }
        """)

        # 목록 페이지가 로드 안 됐거나 구조가 다른 경우 → 메인 페이지 fallback
        if not promos:
            page.goto("https://www.kurly.com/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            promos = page.evaluate("""
                () => {
                    const seen = new Set();
                    const results = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        const isEvent = (
                            href.includes('/shop/event/') ||
                            href.includes('event.kurly.com') ||
                            href.includes('/kurly-event/')
                        );
                        if (!isEvent || seen.has(href)) return;
                        const img = a.querySelector('img');
                        const title = (img?.alt || a.innerText || '').trim();
                        if (!title) return;
                        seen.add(href);
                        results.push({ title: title.slice(0, 60), url: href });
                    });
                    return results.slice(0, 8);
                }
            """)

        return promos
