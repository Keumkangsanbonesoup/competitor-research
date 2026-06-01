from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page


class BaseCrawler(ABC):
    def __init__(self, site_key: str, site_name: str, promo_url: str):
        self.site_key = site_key
        self.site_name = site_name
        self.promo_url = promo_url
        self.crawled_at = datetime.now().strftime("%Y-%m-%d")
        self.img_dir = Path("data") / self.crawled_at / site_key
        self.img_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def crawl(self, page: Page) -> dict:
        pass

    def take_screenshot(self, page: Page, name: str = "full") -> str:
        path = self.img_dir / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
        return str(path)

    def take_viewport_screenshot(self, page: Page, name: str = "viewport") -> str:
        """현재 화면(KV 영역)만 캡처."""
        path = self.img_dir / f"{name}.png"
        page.screenshot(path=str(path), full_page=False)
        return str(path)

    def extract_large_images(self, page: Page, min_width: int = 300) -> list:
        """일정 크기 이상의 이미지 URL만 추출 (아이콘 등 제외)."""
        return page.evaluate(f"""
            () => Array.from(document.images)
                .filter(img => img.naturalWidth >= {min_width})
                .map(img => img.src)
                .filter(src => src && !src.startsWith('data:'))
                .slice(0, 30)
        """)

    def extract_visible_text(self, page: Page, max_chars: int = 3000) -> str:
        """페이지 본문 텍스트 추출 (script/style 제외)."""
        text = page.evaluate("""
            () => {
                const blocked = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME']);
                const walk = (node) => {
                    if (node.nodeType === 3) return node.textContent;
                    if (blocked.has(node.tagName)) return '';
                    return Array.from(node.childNodes).map(walk).join(' ');
                };
                return walk(document.body).replace(/\\s+/g, ' ').trim();
            }
        """)
        return text[:max_chars]
