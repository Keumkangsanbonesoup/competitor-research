from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG닷컴 크롤러. eventMain.ssg 상단 '메인 롤링 배너(캐러셀)' 우선 수집.
    - 캐러셀은 자동 회전 + lazy load라 보이는 슬라이드 1장만 잡히던 문제 →
      숨은 슬라이드까지(dataset.src 포함) 수집하도록 개선.
    """
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)

        # 실제 DOM 분석 결과: 메인 슬라이드는 class="ssghero24_slide_col" 하위 a[href*="eventDetail"]
        # javascript:void(0) 링크(gate_unit)는 제외
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                document.querySelectorAll('[class*="ssghero24_slide_col"] a[href*="eventDetail"]').forEach(a => {
                    if (!a.href || seen.has(a.href)) return;
                    const img = a.querySelector('img');
                    if (!img) return;
                    const src = img.src || img.dataset?.src || '';
                    const title = (img.alt || '').trim();
                    seen.add(a.href);
                    results.push({ title: title.slice(0, 60), url: a.href, banner_url: src });
                });
                return results.slice(0, 8);
            }
        """)

        # 폴백: ssghero24 선택자 실패 시 eventDetail 링크 전체에서 수집
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set(); const results = [];
                    document.querySelectorAll('a[href*="eventDetail"]').forEach(a => {
                        if (!a.href || seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        if (!img) return;
                        const title = (img.alt || '').trim();
                        if (!title) return;
                        seen.add(a.href);
                        results.push({ title: title.slice(0, 60), url: a.href, banner_url: img.src || '' });
                    });
                    return results.slice(0, 8);
                }
            """)

        return promos
