from playwright.sync_api import Page

from base import BaseCrawler


class NaverKurlyCrawler(BaseCrawler):
    LISTING_URL = "https://shopping.naver.com/kurlynmart/home"

    def __init__(self):
        super().__init__("naver_kurly", "네이버 컬리N마트", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4)")
        page.wait_for_timeout(1500)

        # 네비게이션 탭 제외 키워드
        NAV_SKIP = ['베스트','신상품','알뜰쇼핑','카테고리','컬리N마트','선택됨',
                    '홈','검색','장바구니','마이','로그인']

        # 기획전/이벤트 URL 패턴 우선
        promos = page.evaluate(f"""
            () => {{
                const skip = {NAV_SKIP};
                const seen = new Set();
                const results = [];
                const isNav = t => skip.some(w => t.includes(w));

                // 기획전/이벤트 링크 먼저
                document.querySelectorAll('a[href]').forEach(a => {{
                    const href = a.href;
                    const isPromo = href.includes('exhibition') || href.includes('event')
                        || href.includes('promotion') || href.includes('planshop');
                    if (!isPromo || seen.has(href)) return;
                    const img = a.querySelector('img');
                    const text = (img?.alt || a.innerText || '').trim();
                    if (!text || isNav(text) || text.length < 4) return;
                    seen.add(href);
                    results.push({{ title: text.slice(0, 60), url: href }});
                }});

                // fallback: 배너 이미지 있는 링크 (네비게이션 제외)
                if (results.length === 0) {{
                    document.querySelectorAll('a[href]').forEach(a => {{
                        if (seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        if (!img || img.naturalWidth < 200) return;
                        const text = (img.alt || a.innerText || '').trim();
                        if (!text || isNav(text) || text.length < 4) return;
                        seen.add(a.href);
                        results.push({{ title: text.slice(0, 60), url: a.href }});
                    }});
                }}
                return results.slice(0, 8);
            }}
        """)

        return promos
