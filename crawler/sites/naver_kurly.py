from playwright.sync_api import Page

from base import BaseCrawler


class NaverKurlyCrawler(BaseCrawler):
    """
    네이버 컬리N마트 크롤러.
    홈의 기획전·이벤트 섹션에서 개별 프로모션 수집.
    """
    LISTING_URL = "https://shopping.naver.com/kurlynmart/home"

    def __init__(self):
        super().__init__("naver_kurly", "네이버 컬리N마트", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        # 전체 페이지 스크롤 (더 많은 배너 로드)
        for scroll_pct in [0.25, 0.5, 0.75, 1.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pct})")
            page.wait_for_timeout(800)

        NAV_SKIP = ['베스트','신상품','알뜰쇼핑','카테고리','컬리N마트','선택됨',
                    '홈','검색','장바구니','마이','로그인','내정보','메뉴']

        promos = page.evaluate(f"""
            () => {{
                const skip = {NAV_SKIP};
                const seen = new Set();
                const results = [];
                const isNav = t => skip.some(w => t.replace(/\\s/g,'').includes(w.replace(/\\s/g,'')));

                // 1순위: 기획전/이벤트/프로모션 URL 패턴
                const promoPatterns = ['exhibition','event','promotion','planshop','benefit','deal'];
                document.querySelectorAll('a[href]').forEach(a => {{
                    const href = a.href;
                    const isPromo = promoPatterns.some(p => href.includes(p));
                    if (!isPromo || seen.has(href) || !href.startsWith('http')) return;
                    const img = a.querySelector('img');
                    const text = (img?.alt || a.innerText || '').trim();
                    if (!text || isNav(text) || text.length < 3) return;
                    seen.add(href);
                    results.push({{ title: text.slice(0, 60), url: href }});
                }});

                // 2순위: 큰 배너 이미지 링크 (네비 제외)
                if (results.length < 3) {{
                    document.querySelectorAll('a[href]').forEach(a => {{
                        if (seen.has(a.href) || !a.href.startsWith('http')) return;
                        const img = a.querySelector('img');
                        if (!img) return;
                        // 자연 크기 기준 충분히 큰 이미지
                        const w = img.naturalWidth || img.width;
                        const h = img.naturalHeight || img.height;
                        if (w < 150 || h < 80) return;
                        const text = (img.alt || a.innerText || '').trim();
                        if (!text || isNav(text) || text.length < 3) return;
                        seen.add(a.href);
                        results.push({{ title: text.slice(0, 60), url: a.href }});
                    }});
                }}

                return results.slice(0, 8);
            }}
        """)

        # fallback: 기획전 전용 페이지로 이동
        if not promos:
            for url in [
                "https://shopping.naver.com/kurlynmart/exhibition",
                "https://shopping.naver.com/kurlynmart/event",
            ]:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000)
                    items = page.evaluate("""
                        () => Array.from(document.querySelectorAll('a[href]'))
                            .filter(a => a.querySelector('img'))
                            .map(a => ({
                                title: (a.querySelector('img')?.alt || a.innerText || '').trim(),
                                url: a.href
                            }))
                            .filter(i => i.title.length > 2 && i.url.startsWith('http'))
                            .slice(0, 8)
                    """)
                    if items:
                        promos = items
                        break
                except Exception:
                    continue

        return promos
