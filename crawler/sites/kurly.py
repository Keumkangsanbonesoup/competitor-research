from playwright.sync_api import Page

from base import BaseCrawler


class KurlyCrawler(BaseCrawler):
    """
    마켓컬리 크롤러.
    컬리는 현재 event.kurly.com/lego/event/ 패턴 사용.
    메인 페이지에서 해당 링크를 추출.
    """
    LISTING_URL = "https://www.kurly.com/"

    def __init__(self):
        super().__init__("kurly", "마켓컬리", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        # 스크롤해서 이벤트 섹션 로드
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
        page.wait_for_timeout(1000)

        # event.kurly.com 링크 우선 추출
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    if (!href.includes('event.kurly.com') || seen.has(href)) return;
                    const img = a.querySelector('img');
                    const titleEl = a.closest('li, article, div[class*="item"], div[class*="card"]')
                        ?.querySelector('[class*="tit"], [class*="title"], [class*="name"], p, span');
                    const title = (titleEl?.innerText || img?.alt || a.innerText || '').trim();
                    if (!title || title.length < 2) return;
                    seen.add(href);
                    results.push({ title: title.slice(0, 60), url: href });
                });
                return results.slice(0, 8);
            }
        """)

        # fallback 1: kurly.com/np/categories 또는 이벤트 관련 링크
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set();
                    const results = [];
                    const skip = ['로그인','회원가입','장바구니','마이컬리','고객센터',
                                  '카테고리','베스트','신상품','알뜰쇼핑'];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href;
                        if (!href.includes('kurly.com') || seen.has(href)) return;
                        const img = a.querySelector('img');
                        if (!img || img.naturalWidth < 200) return;
                        const title = (img.alt || a.innerText || '').trim();
                        const isSkip = skip.some(w => title.includes(w));
                        if (!title || isSkip || title.length < 2) return;
                        seen.add(href);
                        results.push({ title: title.slice(0, 60), url: href });
                    });
                    return results.slice(0, 8);
                }
            """)

        # fallback 2: 이벤트 목록 직접 접근
        if not promos:
            for url in [
                "https://www.kurly.com/shop/event/eventList.php",
                "https://m.kurly.com/event",
            ]:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)
                promos = page.evaluate("""
                    () => {
                        const seen = new Set();
                        const results = [];
                        document.querySelectorAll('a[href]').forEach(a => {
                            const href = a.href;
                            const isEvent = href.includes('event.kurly') || href.includes('eventView') || href.includes('bn_id');
                            if (!isEvent || seen.has(href)) return;
                            const img = a.querySelector('img');
                            const title = (img?.alt || a.innerText || '').trim();
                            if (!title || title.length < 2) return;
                            seen.add(href);
                            results.push({ title: title.slice(0, 60), url: href });
                        });
                        return results.slice(0, 8);
                    }
                """)
                if promos:
                    break

        return promos
