from playwright.sync_api import Page

from base import BaseCrawler

CURRENT_YEARS = ("2026", "2027")


class KurlyCrawler(BaseCrawler):
    """
    마켓컬리 크롤러.
    메인 페이지에서 event.kurly.com/lego/event/ 링크 추출.
    이미지 alt가 전부 '메인배너'이므로 URL 슬러그를 임시 제목으로 사용.
    """
    LISTING_URL = "https://www.kurly.com/"

    def __init__(self):
        super().__init__("kurly", "마켓컬리", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4)")
        page.wait_for_timeout(1000)

        promos = page.evaluate(f"""
            () => {{
                const seen = new Set();
                const results = [];
                const current = {list(CURRENT_YEARS)};
                document.querySelectorAll('a[href*="event.kurly.com/lego/event/"]').forEach(a => {{
                    const href = a.href;
                    if (seen.has(href)) return;
                    // 현재 연도 이벤트만 필터
                    if (!current.some(y => href.includes('/' + y + '/'))) return;
                    // URL 마지막 슬러그를 임시 제목으로
                    const parts = href.replace(/\\/$/, '').split('/');
                    const slug = parts[parts.length - 1] || parts[parts.length - 2];
                    // alt에서 '메인배너' 제거 후 실제 설명이 있으면 우선 사용
                    const img = a.querySelector('img');
                    const alt = (img?.alt || '').replace(/^메인배너[_\\s]*/i, '').trim();
                    const title = alt || slug;
                    const banner_url = img?.src || img?.dataset?.src || '';
                    seen.add(href);
                    results.push({{ title: title.slice(0, 60), url: href, banner_url }});
                }});
                return results.slice(0, 8);
            }}
        """)

        return promos
