from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page


class BaseCrawler(ABC):
    MAX_PROMOTIONS = 5  # 사이트당 최대 수집할 프로모션 수

    def __init__(self, site_key: str, site_name: str, listing_url: str):
        self.site_key = site_key
        self.site_name = site_name
        self.listing_url = listing_url
        self.crawled_at = datetime.now().strftime("%Y-%m-%d")
        self.img_dir = Path("data") / self.crawled_at / site_key
        self.img_dir.mkdir(parents=True, exist_ok=True)

    # ── 하위 클래스에서 반드시 구현 ──────────────────────────────
    @abstractmethod
    def get_promo_urls(self, page: Page) -> list:
        """이벤트 목록 페이지에서 개별 프로모션 {title, url} 리스트 반환."""
        pass

    # ── 공통 상세 수집 ────────────────────────────────────────────
    def get_promo_detail(self, page: Page, title: str, url: str, idx: int) -> dict:
        """개별 프로모션 페이지 진입 → 스크린샷·텍스트·이미지 수집."""
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            # 스크롤해서 전체 콘텐츠 로드
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(1000)

            kv_shot  = self._screenshot(page, f"promo_{idx:02d}_kv",  full_page=False)
            full_shot = self._screenshot(page, f"promo_{idx:02d}_full", full_page=True)
            images   = self._large_images(page)
            text     = self._visible_text(page)

            # 페이지에서 실제 제목 추출 (슬러그보다 정확한 한국어 제목)
            page_title = page.evaluate("""
                () => {
                    const h = document.querySelector('h1, h2, [class*="title"], [class*="tit"]');
                    return (h?.innerText || document.title || '').trim().split('\\n')[0].slice(0, 80);
                }
            """)

            return {
                "title": page_title or title,
                "url": url,
                "kv_screenshot": kv_shot,
                "full_screenshot": full_shot,
                "page_images": images[:20],
                "page_text": text,
            }
        except Exception as e:
            return {"title": title, "url": url, "error": str(e)}

    # ── 메인 오케스트레이터 ───────────────────────────────────────
    def crawl(self, page: Page) -> dict:
        print(f"  이벤트 목록 수집 중: {self.listing_url}")
        try:
            promos = self.get_promo_urls(page)[: self.MAX_PROMOTIONS]
        except Exception as e:
            promos = []
            print(f"  목록 수집 실패: {e}")

        print(f"  → {len(promos)}개 프로모션 발견")
        results = []
        for i, promo in enumerate(promos):
            label = promo.get("title", "")[:40]
            print(f"  [{i+1}/{len(promos)}] {label}")
            detail = self.get_promo_detail(page, promo["title"], promo["url"], i)
            results.append(detail)

        return {
            "site": self.site_key,
            "site_name": self.site_name,
            "crawled_at": self.crawled_at,
            "listing_url": self.listing_url,
            "promotions": results,
        }

    # ── 내부 유틸 ─────────────────────────────────────────────────
    def _screenshot(self, page: Page, name: str, full_page: bool = True) -> str:
        path = self.img_dir / f"{name}.png"
        page.screenshot(path=str(path), full_page=full_page)
        return str(path)

    def _large_images(self, page: Page, min_width: int = 300) -> list:
        return page.evaluate(f"""
            () => Array.from(document.images)
                .filter(img => img.naturalWidth >= {min_width})
                .map(img => img.src)
                .filter(src => src && !src.startsWith('data:'))
                .slice(0, 30)
        """)

    def _visible_text(self, page: Page, max_chars: int = 3000) -> str:
        text = page.evaluate("""
            () => {
                const blocked = new Set(['SCRIPT','STYLE','NOSCRIPT','IFRAME']);
                const walk = n => {
                    if (n.nodeType === 3) return n.textContent;
                    if (blocked.has(n.tagName)) return '';
                    return Array.from(n.childNodes).map(walk).join(' ');
                };
                return walk(document.body).replace(/\\s+/g, ' ').trim();
            }
        """)
        return text[:max_chars]
