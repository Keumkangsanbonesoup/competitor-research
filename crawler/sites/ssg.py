from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # SSG 이벤트 상세 URL 패턴: /event/eventDetail.ssg?id=xxxx
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                // 이벤트 상세 링크만 (탭 메뉴 제외)
                document.querySelectorAll('a[href*="eventDetail"]').forEach(a => {
                    if (seen.has(a.href)) return;
                    const card = a.closest('li') || a.closest('article') || a;
                    const titleEl = card.querySelector(
                        '[class*="tit"], [class*="title"], [class*="name"], h2, h3, p.desc, strong'
                    );
                    const imgAlt = a.querySelector('img')?.alt || '';
                    const title = (titleEl?.innerText || imgAlt || '').trim();
                    if (!title || !a.href) return;
                    seen.add(a.href);
                    results.push({ title: title.slice(0, 60), url: a.href });
                });
                return results.slice(0, 8);
            }
        """)

        # fallback: 진행중인 이벤트 탭 클릭 후 재시도
        if not promos:
            try:
                # "진행중인 이벤트" 탭 클릭
                btn = page.query_selector('a:has-text("진행중인"), button:has-text("진행중인")')
                if btn:
                    btn.click()
                    page.wait_for_timeout(1500)
                promos = page.evaluate("""
                    () => {
                        const seen = new Set();
                        const results = [];
                        document.querySelectorAll('a[href*="eventDetail"], a[href*="/event/"]').forEach(a => {
                            if (seen.has(a.href)) return;
                            const img = a.querySelector('img');
                            if (!img) return;  // 이미지 없는 건 탭/메뉴
                            const title = (img.alt || a.innerText || '').trim();
                            if (!title || title.length < 3) return;
                            seen.add(a.href);
                            results.push({ title: title.slice(0, 60), url: a.href });
                        });
                        return results.slice(0, 8);
                    }
                """)
            except Exception:
                pass

        return promos
