from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG닷컴 크롤러.
    eventMain.ssg 상단의 '메인 롤링 배너(캐러셀)'를 우선 수집한다.
    - 이전 버그: a[href*="eventDetail"] 만 긁어 캐러셀이 아닌 하단 이벤트(체험단 등)를 수집.
    - 개선: 페이지 상단의 '폭이 큰 배너 이미지'를 가진 링크를 DOM 순서대로 수집(=캐러셀 우선).
    """
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        # 캐러셀 lazy 이미지 트리거 (살짝 스크롤)
        page.evaluate("window.scrollTo(0, 300)")
        page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # 1순위: 상단 메인 롤링 배너(캐러셀). 폭이 큰 배너 이미지를 가진 링크를 DOM 순서대로.
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                const push = (href, title, banner_url) => {
                    if (!href || seen.has(href)) return;
                    seen.add(href);
                    results.push({ title: (title||'').slice(0,60), url: href, banner_url: banner_url||'' });
                };
                // 메인 비주얼/롤링/스와이퍼 컨테이너 우선 탐색
                const conts = document.querySelectorAll(
                    '[class*="rolling"], [class*="visual"], [class*="swiper"], [class*="banner"], [class*="cmmi"]'
                );
                for (const c of conts) {
                    const rect = c.getBoundingClientRect();
                    // 페이지 상단(상위 1400px)의 넓은 영역만 = 메인 배너 영역
                    if (rect.width < 500) continue;
                    c.querySelectorAll('a').forEach(a => {
                        const img = a.querySelector('img');
                        if (!img) return;
                        const w = img.naturalWidth || img.width || img.getBoundingClientRect().width || 0;
                        if (w < 500) return;                 // 메인 배너급 폭
                        const alt = (img.alt || '').trim();
                        const src = img.src || img.dataset?.src || '';
                        push(a.href, alt, src);
                    });
                    if (results.length >= 8) break;
                }
                return results.slice(0, 8);
            }
        """)

        # 2순위(폴백): 페이지 전체에서 폭 큰 배너 이미지 링크
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set(); const results = [];
                    document.querySelectorAll('a').forEach(a => {
                        const img = a.querySelector('img');
                        if (!img) return;
                        const w = img.naturalWidth || img.width || 0;
                        if (w < 600) return;
                        if (!a.href || seen.has(a.href)) return;
                        seen.add(a.href);
                        results.push({ title: (img.alt||'').trim().slice(0,60), url: a.href, banner_url: img.src||'' });
                    });
                    return results.slice(0, 8);
                }
            """)

        # 3순위(최종 폴백): 기존 eventDetail 링크 방식
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set(); const results = [];
                    document.querySelectorAll('a[href*="eventDetail"]').forEach(a => {
                        if (seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        const title = (img?.alt || a.innerText || '').trim();
                        if (!a.href) return;
                        seen.add(a.href);
                        results.push({ title: title.slice(0,60), url: a.href, banner_url: img?.src || '' });
                    });
                    return results.slice(0, 8);
                }
            """)

        return promos
