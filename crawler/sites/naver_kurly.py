from playwright.sync_api import Page

from base import BaseCrawler


class NaverKurlyCrawler(BaseCrawler):
    """
    네이버 컬리N마트 크롤러.
    홈 → 프로모션/기획전 배너 링크 → 상세 수집.
    """
    LISTING_URL = "https://shopping.naver.com/kurlynmart/home"

    def __init__(self):
        super().__init__("naver_kurly", "네이버 컬리N마트", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        # 네이버는 JS 초기화 느림
        page.wait_for_timeout(5000)
        # 스크롤로 더 많은 콘텐츠 로드
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
        page.wait_for_timeout(1500)

        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                // 네이버쇼핑 내 컬리N마트 기획전/이벤트 링크
                const selectors = [
                    'a[href*="kurlynmart/exhibition"]',
                    'a[href*="kurlynmart/event"]',
                    'a[href*="kurlynmart/promotion"]',
                    'a[href*="/kurlynmart/"]',
                ];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(a => {
                        if (seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        const title = (img?.alt || a.innerText || '').trim();
                        if (!title || !a.href) return;
                        seen.add(a.href);
                        results.push({ title: title.slice(0, 60), url: a.href });
                    });
                });

                // fallback: 큰 이미지를 가진 배너 링크
                if (results.length === 0) {
                    document.querySelectorAll('a[href]').forEach(a => {
                        if (seen.has(a.href) || !a.href.includes('naver')) return;
                        const img = a.querySelector('img');
                        if (!img || img.naturalWidth < 250) return;
                        const title = (img.alt || a.innerText || '네이버 컬리N마트 프로모션').trim();
                        seen.add(a.href);
                        results.push({ title: title.slice(0, 60), url: a.href });
                    });
                }

                return results.slice(0, 8);
            }
        """)

        return promos
