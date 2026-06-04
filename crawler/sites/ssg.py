from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG닷컴 크롤러. eventMain.ssg 상단 메인 히어로 캐러셀(ssghero) 배너를 수집.
    실제 DOM 기준:
        <a class="ssghero24_imglink" href="/plan/planShop.ssg?dispCmptId=...">
          <img alt="...배너 카피...">
          <div class="ssghero24_tit"><h3 class="ssghero24_titmain"><span>..</span></h3>
            <p class="ssghero24_titsub"><span>..</span></p></div>
        </a>
    (이전 버그: eventDetail 링크를 긁어 캐러셀이 아닌 상세 이벤트를 수집)
    """
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(600)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(400)

        # 1순위: 메인 히어로 캐러셀 (ssghero**_imglink). 버전 변경(ssghero24→25) 대비해 부분일치.
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                document.querySelectorAll('a[class*="ssghero"][class*="imglink"], a[class*="hero"][class*="imglink"]').forEach(a => {
                    if (!a.href || seen.has(a.href)) return;   // swiper 복제 슬라이드 중복 제거
                    const img = a.querySelector('img');
                    // 제목: titmain 우선 → img alt 폴백
                    let title = '';
                    const main = a.querySelector('[class*="titmain"]');
                    const sub  = a.querySelector('[class*="titsub"]');
                    if (main) title = main.innerText.replace(/\\s+/g, ' ').trim();
                    if (!title && img) title = (img.alt || '').trim();
                    if (sub) {
                        const s = sub.innerText.replace(/\\s+/g, ' ').trim();
                        if (s) title = (title + ' · ' + s).trim();
                    }
                    // 배너 이미지: srcset 2x(고해상) 우선 → src
                    let banner_url = '';
                    if (img) {
                        if (img.srcset) banner_url = img.srcset.split(',').pop().trim().split(' ')[0];
                        banner_url = banner_url || img.src || img.dataset?.src || '';
                    }
                    seen.add(a.href);
                    results.push({ title: title.slice(0, 70), url: a.href, banner_url });
                });
                return results.slice(0, 8);
            }
        """)

        # 2순위(폴백): 폭 큰 배너 이미지 링크
        if len(promos) < 2:
            more = page.evaluate("""
                () => {
                    const seen = new Set(); const results = [];
                    const bad = /icon|sprite|blank|btn_|arrow|dot/i;
                    document.querySelectorAll('a').forEach(a => {
                        const img = a.querySelector('img');
                        if (!img || !a.href) return;
                        const src = img.src || img.dataset?.src || '';
                        if (!src || bad.test(src)) return;
                        const w = img.naturalWidth || img.width || 0;
                        if (w < 500) return;
                        if (seen.has(a.href)) return;
                        seen.add(a.href);
                        results.push({ title:(img.alt||'').trim().slice(0,70), url:a.href, banner_url:src });
                    });
                    return results.slice(0, 8);
                }
            """)
            urls = {p["url"] for p in promos}
            for m in more:
                if m["url"] not in urls:
                    promos.append(m); urls.add(m["url"])

        return promos
