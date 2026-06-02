from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page


class BaseCrawler(ABC):
    MAX_PROMOTIONS = 3  # 사이트당 최대 수집 (상단 노출=대형·중요 프로모션 우선)

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
    def get_promo_detail(self, page: Page, title: str, url: str, idx: int,
                         listing_banner_url: str | None = None) -> dict:
        """개별 프로모션 페이지 진입 → 스크린샷·텍스트·이미지 수집."""
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)

            # ① KV(첫 화면)는 반드시 '최상단'에서 촬영 (스크롤 전)
            #    - 이전 버그: 페이지 중간으로 스크롤한 뒤 찍어 SSG 등 긴 페이지의
            #      KV가 본문 중간(유의사항·상품그리드)으로 잡혔음.
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(600)
            kv_shot = self._screenshot(page, f"promo_{idx:02d}_kv", full_page=False)

            # ② 전체 페이지: lazy 이미지 로드를 위해 단계적으로 스크롤 후 촬영
            page.evaluate("""
                () => {
                    const h = document.body.scrollHeight;
                    [0.25, 0.5, 0.75, 1.0].forEach(p => window.scrollTo(0, h * p));
                }
            """)
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(400)
            full_shot = self._screenshot(page, f"promo_{idx:02d}_full", full_page=True)

            banner = self._download_banner(page, idx, listing_banner_url)
            text   = self._visible_text(page)

            # 페이지 제목 추출: og:title 우선(헤더 로고 'SSG.COM' 회피)
            page_title = page.evaluate("""
                () => {
                    const og = document.querySelector('meta[property="og:title"]')?.content;
                    if (og && og.trim()) return og.trim().split('\\n')[0].slice(0, 80);
                    const sel = 'main h1, main h2, [class*="event"] [class*="tit"], [class*="visual"] [class*="tit"], h1, h2';
                    const h = document.querySelector(sel);
                    return (h?.innerText || document.title || '').trim().split('\\n')[0].slice(0, 80);
                }
            """)

            GENERIC = {"SSG.COM", "SSG", "전체 알림", "고객행복센터", "유의사항",
                       "쿠폰 유의사항", "카드사 쿠폰 유의사항", ""}
            final_title = page_title if (not title or title.strip() in GENERIC) else title

            return {
                "title": final_title or page_title,
                "listing_title": title,
                "page_title": page_title,
                "url": url,
                "kv_screenshot": kv_shot,
                "full_screenshot": full_shot,
                "banner_image": banner,
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
            detail = self.get_promo_detail(
                page, promo["title"], promo["url"], i,
                listing_banner_url=promo.get("banner_url")
            )
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

    def _download_banner(self, page: Page, promo_idx: int,
                         banner_url: str | None = None) -> str | None:
        """목록 페이지에서 수집한 배너 URL을 파일로 저장."""
        if not banner_url:
            print(f"    배너 URL 없음 (promo_{promo_idx:02d})")
            return None
        try:
            response = page.request.get(banner_url, timeout=10000)
            if not response.ok:
                print(f"    배너 다운로드 실패 (HTTP {response.status}): {banner_url[:60]}")
                return None
            ext = banner_url.split("?")[0].rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "gif", "webp", "avif"):
                ext = "jpg"
            path = self.img_dir / f"promo_{promo_idx:02d}_banner.{ext}"
            path.write_bytes(response.body())
            print(f"    배너 이미지 저장: {path.name}")
            return str(path)
        except Exception as e:
            print(f"    배너 다운로드 실패: {e}")
            return None

    def _large_images(self, page: Page, min_width: int = 200) -> list:
        """배너·KV·섹션 이미지 수집. lazy load 대응 + <picture> + srcset 포함."""
        page.evaluate("""
            () => {
                const h = document.body.scrollHeight;
                [0.25, 0.5, 0.75, 1.0].forEach(p => window.scrollTo(0, h * p));
            }
        """)
        page.wait_for_timeout(800)

        return page.evaluate(f"""
            () => {{
                const seen = new Set();
                const add = src => {{
                    if (!src || src.startsWith('data:') || seen.has(src)) return;
                    seen.add(src);
                }};
                document.querySelectorAll('img').forEach(img => {{
                    const w = img.naturalWidth || img.width || 0;
                    if (w < {min_width}) return;
                    const src = img.src || img.dataset.src || img.dataset.lazySrc || '';
                    add(src);
                    if (img.srcset) {{
                        const best = img.srcset.split(',').map(s => s.trim().split(' ')[0]).pop();
                        if (best) add(best);
                    }}
                }});
                document.querySelectorAll('picture source').forEach(s => {{
                    const url = (s.srcset || '').split(',')[0].trim().split(' ')[0];
                    if (url) add(url);
                }});
                document.querySelectorAll(
                    '[class*="banner"], [class*="kv"], [class*="hero"], [class*="visual"], section, div[style]'
                ).forEach(el => {{
                    const bg = window.getComputedStyle(el).backgroundImage;
                    const m = bg && bg.match(/url\(["']?([^"')]+)["']?\)/);
                    if (m && m[1]) add(m[1]);
                }});
                return Array.from(seen).slice(0, 40);
            }}
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
                return walk(document.body).replace(/\s+/g, ' ').trim();
            }
        """)
        return text[:max_chars]
