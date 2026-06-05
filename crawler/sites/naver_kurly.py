from playwright.sync_api import Page

from base import BaseCrawler


class NaverKurlyCrawler(BaseCrawler):
    """
    네이버 컬리N마트 크롤러.
    홈 배너의 bundle-groups / bundles / festa 링크를 실제 프로모션으로 수집.
    """
    LISTING_URL = "https://shopping.naver.com/kurlynmart/home"

    def __init__(self):
        super().__init__("naver_kurly", "네이버 컬리N마트", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        page.wait_for_timeout(5000)
        # 배너 캐러셀 lazy 로드: 더 촘촘히 스크롤 + 대기 (프로모션 1개만 잡히는 문제 완화)
        for pct in [0.2, 0.4, 0.6, 0.8, 0.4, 0.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            page.wait_for_timeout(900)

        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                // 네이버 컬리N마트 실제 프로모션 URL 패턴
                const isPromo = href =>
                    href.includes('kurlynmart/bundle-groups') ||
                    href.includes('kurlynmart/bundles') ||
                    href.includes('shopping.naver.com/festa');

                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    if (!isPromo(href) || seen.has(href)) return;
                    const img = a.querySelector('img');
                    if (!img) return;
                    const w = img.naturalWidth || img.width || 0;
                    if (w < 200) return;
                    // "메인배너_컬리N마트_실제제목" → "실제제목"
                    const rawAlt = img.alt || '';
                    const title = rawAlt
                        .replace(/^메인배너[_\s]*(컬리N마트|컬리)[_\s]*/i, '')
                        .replace(/^메인배너[_\s]*/i, '')
                        .trim();
                    if (!title || title.length < 2) return;
                    const banner_url = img.src || img.dataset?.src || '';
                    seen.add(href);
                    results.push({ title: title.slice(0, 60), url: href, banner_url });
                });
                return results.slice(0, 8);
            }
        """)

        return promos