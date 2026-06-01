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

            kv_shot   = self._screenshot(page, f"promo_{idx:02d}_kv",   full_page=False)
            full_shot = self._screenshot(page, f"promo_{idx:02d}_full", full_page=True)
            # 배너 이미지 1장만 다운로드 (와이드 KV 배너)
            banner    = self._download_banner(page, idx)
            text      = self._visible_text(page)

            # 페이지에서 실제 제목 추출 (슬러그보다 정확한 한국어 제목)
            page_title = page.evaluate("""
                () => {
                    const h = document.querySelector('h1, h2, [class*="title"], [class*="tit"]');
                    return (h?.innerText || document.title || '').trim().split('\\n')[0].slice(0, 80);
                }
            """)

            return {
                "title": title or page_title,  # 목록에서 가져온 제목 우선
                "page_title": page_title,       # 페이지 자체 제목은 별도 보관
                "url": url,
                "kv_screenshot": kv_shot,
                "full_screenshot": full_shot,
                "banner_image": banner,         # 메인 배너 1장 (영구 보관용 로컬 파일)
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

    def _download_banner(self, page: Page, promo_idx: int) -> str | None:
        """메인 배너(KV) 이미지 1장만 다운로드.
        와이드형(가로:세로 ≥ 1.8, 가로 ≥ 400px) 이미지 중 가장 큰 것을 배너로 판단."""
        banner_url = page.evaluate("""
            () => {
                let best = null, bestW = 0;
                document.querySelectorAll('img').forEach(img => {
                    const w = img.naturalWidth  || img.width  || 0;
                    const h = img.naturalHeight || img.height || 1;
                    if (w < 400) return;        // 너무 작은 이미지 제외
                    if (w / h < 1.8) return;    // 세로형(상품 썸네일 등) 제외
                    const src = img.src || img.dataset.src || img.dataset.lazySrc || '';
                    if (!src || src.startsWith('data:')) return;
                    if (w > bestW) { bestW = w; best = src; }
                });
                return best;
            }
        """)
        if not banner_url:
            print(f"    배너 이미지를 찾지 못했어요 (promo_{promo_idx:02d})")
            return None
        try:
            response = page.request.get(banner_url, timeout=10000)
            if not response.ok:
                return None
            ext = banner_url.split("?")[0].rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "gif", "webp", "avif"):
                ext = "jpg"
            path = self.img_dir / f"promo_{promo_idx:02d}_banner.{ext}"
            path.write_bytes(response.body())
            print(f"    배너 이미지 저장: {path.name}")
            return str(path)
        except Exception as e:
            print(f"    배너 이미지 다운로드 실패: {e}")
            return None

    def _large_images(self, page: Page, min_width: int = 200) -> list:
        """배너·KV·섹션 이미지 수집. lazy load 대응 + <picture> + srcset 포함."""
        # 스크롤해서 lazy load 이미지 트리거
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

                // 1) <img> — naturalWidth 또는 width 기준
                document.querySelectorAll('img').forEach(img => {{
                    const w = img.naturalWidth || img.width || 0;
                    if (w < {min_width}) return;
                    const src = img.src || img.dataset.src || img.dataset.lazySrc || '';
                    add(src);
                    // srcset에서 가장 큰 URL 추출
                    if (img.srcset) {{
                        const best = img.srcset.split(',').map(s => s.trim().split(' ')[0]).pop();
                        if (best) add(best);
                    }}
                }});

                // 2) <picture> > <source>
                document.querySelectorAll('picture source').forEach(s => {{
                    const url = (s.srcset || '').split(',')[0].trim().split(' ')[0];
                    if (url) add(url);
                }});

                // 3) CSS background-image (배너 섹션에 많음)
                document.querySelectorAll(
                    '[class*="banner"], [class*="kv"], [class*="hero"], [class*="visual"], section, div[style]'
                ).forEach(el => {{
                    const bg = window.getComputedStyle(el).backgroundImage;
                    const m = bg && bg.match(/url\\(["']?([^"')]+)["']?\\)/);
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
                return walk(document.body).replace(/\\s+/g, ' ').trim();
            }
        """)
        return text[:max_chars]
