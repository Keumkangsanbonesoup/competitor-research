from playwright.sync_api import Page
from playwright_stealth import stealth_sync

from base import BaseCrawler


class CoupangCrawler(BaseCrawler):
    """
    쿠팡 크롤러.
    /np/campaigns/ 는 Akamai에 IP 차단됨 → 메인 페이지에서
    프로모션 배너 링크를 추출하는 방식으로 우회.
    """
    LISTING_URL = "https://www.coupang.com/"

    def __init__(self):
        super().__init__("coupang", "쿠팡", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        # stealth 재적용 (새 navigation 후에도 유지)
        stealth_sync(page)
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # 403 차단 감지
        if "Access Denied" in page.title() or "Access Denied" in page.content()[:500]:
            print("  ⚠️  쿠팡 메인도 차단됨 — 빈 목록 반환")
            return []

        # 메인 페이지에서 캠페인/기획전 링크 추출
        # 쿠팡은 /np/campaigns/, /np/categories/, /deal/ 등 패턴 사용
        promos = page.evaluate("""
            () => {
                const seen = new Set();
                const results = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href || '';
                    const isPromo = (
                        href.includes('/np/campaigns/') ||
                        href.includes('/np/promotion/') ||
                        href.includes('/deal/') ||
                        href.includes('/np/search/?q=') && a.closest('[class*="event"]')
                    );
                    if (!isPromo || seen.has(href)) return;
                    const img = a.querySelector('img');
                    const title = (img?.alt || a.innerText || '').trim().slice(0, 60)
                        || href.split('/').filter(Boolean).pop();
                    if (!title) return;
                    seen.add(href);
                    results.push({ title, url: href });
                });
                return results.slice(0, 8);
            }
        """)

        # 링크가 없으면 메인 배너 영역의 첫 번째 링크라도 수집
        if not promos:
            promos = page.evaluate("""
                () => {
                    const seen = new Set();
                    const bannerLinks = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const img = a.querySelector('img');
                        if (!img || !img.naturalWidth || img.naturalWidth < 200) return;
                        const href = a.href;
                        if (seen.has(href) || !href.startsWith('http')) return;
                        seen.add(href);
                        bannerLinks.push({
                            title: img.alt || a.innerText.trim() || '쿠팡 프로모션',
                            url: href,
                        });
                    });
                    return bannerLinks.slice(0, 5);
                }
            """)

        return promos
