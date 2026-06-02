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
        # 캐러셀 lazy 슬라이드 트리거: '다음' 화살표를 여러 번 눌러 슬라이드 강제 로드
        for sel in ['[class*="next"]', 'button[class*="next"]', 'a[class*="next"]',
                    '[class*="arrow"][class*="r"]', '[class*="btn_next"]']:
            try:
                btn = page.query_selector(sel)
                if btn:
                    for _ in range(7):
                        btn.click(timeout=800)
                        page.wait_for_timeout(400)
                    break
            except Exception:
                continue
        page.wait_for_timeout(500)

        # 1순위: 상단 배너/비주얼/롤링/스와이퍼 컨테이너 내 모든 슬라이드 링크(숨은 것 포함)
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                const bad = /icon|sprite|blank|spacer|btn_|arrow|dot|1x1|loading/i;
                const okImg = img => {
                    const src = img.src || img.dataset?.src || img.dataset?.original || '';
                    if (!src || src.startsWith('data:') || bad.test(src)) return '';
                    // 아이콘급(명시 width/height 작은) 제외
                    const aw = parseInt(img.getAttribute('width') || '0', 10);
                    if (aw && aw < 200) return '';
                    return src;
                };
                const conts = document.querySelectorAll(
                    '[class*="rolling"], [class*="visual"], [class*="swiper"], [class*="banner"], [class*="cmmi"]'
                );
                for (const c of conts) {
                    if (c.getBoundingClientRect().width < 500) continue;
                    c.querySelectorAll('a').forEach(a => {
                        if (!a.href || seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        if (!img) return;
                        const src = okImg(img);
                        if (!src) return;
                        seen.add(a.href);
                        results.push({ title: (img.alt||'').trim().slice(0,60), url: a.href, banner_url: src });
                    });
                    if (results.length >= 10) break;
                }
                return results.slice(0, 8);
            }
        """)

        # 2순위(폴백): 페이지 전체 폭 큰 배너 이미지 링크
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
                        const w = img.naturalWidth || img.width || parseInt(img.getAttribute('width')||'0',10) || 0;
                        if (w < 500) return;
                        if (seen.has(a.href)) return;
                        seen.add(a.href);
                        results.push({ title: (img.alt||'').trim().slice(0,60), url: a.href, banner_url: src });
                    });
                    return results.slice(0, 8);
                }
            """)
            # 기존 결과 + 폴백 병합(중복 url 제거)
            urls = {p["url"] for p in promos}
            for m in more:
                if m["url"] not in urls:
                    promos.append(m); urls.add(m["url"])

        # 3순위(최종 폴백): eventDetail 링크
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set(); const results = [];
                    document.querySelectorAll('a[href*="eventDetail"]').forEach(a => {
                        if (seen.has(a.href)) return;
                        const img = a.querySelector('img');
                        if (!a.href) return;
                        seen.add(a.href);
                        results.push({ title:(img?.alt||a.innerText||'').trim().slice(0,60), url:a.href, banner_url:img?.src||'' });
                    });
                    return results.slice(0, 8);
                }
            """)

        return promos
