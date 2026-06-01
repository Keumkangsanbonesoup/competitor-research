from playwright.sync_api import Page

from base import BaseCrawler


class KurlyCrawler(BaseCrawler):
    LISTING_URL = "https://www.kurly.com/shop/event/eventList.php"

    def __init__(self):
        super().__init__("kurly", "마켓컬리", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # 컬리 이벤트 상세 URL 패턴: /shop/event/eventView.php?bn_id=xxxx
        # 이벤트 카드 내 실제 텍스트 제목을 우선 추출
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                document.querySelectorAll('a[href*="eventView"], a[href*="bn_id="]').forEach(a => {
                    if (seen.has(a.href)) return;
                    // 카드 컨테이너에서 텍스트 제목 찾기
                    const card = a.closest('li') || a.closest('article') || a;
                    const titleEl = card.querySelector(
                        '[class*="tit"], [class*="title"], [class*="name"], h2, h3, strong, p'
                    );
                    const imgAlt = a.querySelector('img')?.alt || '';
                    const title = (titleEl?.innerText || imgAlt || '').trim()
                        .replace(/메인배너|이미지/gi, '').trim();
                    if (!title || !a.href) return;
                    seen.add(a.href);
                    results.push({ title: title.slice(0, 60), url: a.href });
                });
                return results.slice(0, 8);
            }
        """)

        # fallback: 이미지 alt가 아닌 카드 내 텍스트로 재시도
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set();
                    const results = [];
                    document.querySelectorAll('li a, .event_item a').forEach(a => {
                        if (seen.has(a.href)) return;
                        const href = a.href;
                        // 이벤트 관련 URL만 (탭/메뉴 링크 제외)
                        if (!href.includes('event') && !href.includes('kurly.com/np/')) return;
                        // 네비게이션 메뉴 제외: 텍스트가 너무 짧거나 메뉴성 단어
                        const skipWords = ['모든이벤트','진행중','종료','당첨','베스트','신상','카테고리'];
                        const text = a.innerText.trim();
                        if (skipWords.some(w => text.replace(/\\s/g,'').includes(w))) return;
                        if (!text || !a.href.startsWith('http')) return;
                        seen.add(href);
                        results.push({ title: text.slice(0, 60), url: href });
                    });
                    return results.slice(0, 8);
                }
            """)

        return promos
