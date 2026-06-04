import json

from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG닷컴 크롤러.
    메인 히어로 캐러셀(ssghero/planShop 배너)은 eventMain.ssg가 아니라 '홈(www.ssg.com)'에
    존재함(진단으로 확인). → 홈을 크롤해 히어로 배너를 수집한다.
    폴백: 홈에서 못 잡으면 eventMain의 eventDetail 대표 이벤트.
    """
    HOME_URL = "https://www.ssg.com/"
    EVENT_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        # listing_url 은 홈으로 (히어로 배너가 여기 있음)
        super().__init__("ssg", "SSG", self.HOME_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        page.wait_for_timeout(2500)
        try:
            page.wait_for_selector('a[class*="ssghero"][class*="imglink"], a[href*="planShop"]', timeout=6000)
        except Exception:
            pass
        for pct in [0.15, 0.3, 0.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            page.wait_for_timeout(700)

        diag = page.evaluate("""
            () => ({
                ssghero: document.querySelectorAll('a[class*="ssghero"][class*="imglink"]').length,
                planShop: document.querySelectorAll('a[href*="planShop"]').length,
            })
        """)
        try:
            (self.img_dir / "_debug_listing.json").write_text(
                json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        print(f"    [SSG 진단] ssghero={diag.get('ssghero')} planShop={diag.get('planShop')}")

        # ── 히어로 캐러셀 배너 수집 ──
        promos = page.evaluate("""
            () => {
                const seen=new Set(); const out=[];
                const nodes = document.querySelectorAll('a[class*="ssghero"][class*="imglink"], a[href*="planShop"]');
                nodes.forEach(a => {
                    if (!a.href || seen.has(a.href)) return;          // swiper 복제 슬라이드 dedupe
                    const img=a.querySelector('img');
                    let t='';
                    const main=a.querySelector('[class*="titmain"]'), sub=a.querySelector('[class*="titsub"]');
                    if (main) t=main.innerText.replace(/\\s+/g,' ').trim();
                    if (!t && img) t=(img.alt||'').trim();
                    if (sub){const s=sub.innerText.replace(/\\s+/g,' ').trim(); if(s) t=(t+' · '+s).trim();}
                    let b=''; if(img){ if(img.srcset) b=img.srcset.split(',').pop().trim().split(' ')[0]; b=b||img.src||img.dataset?.src||''; }
                    seen.add(a.href);
                    out.push({title:t.slice(0,80), url:a.href, banner_url:b});
                });
                return out.slice(0,8);
            }
        """)

        # ── 폴백: 홈에서 못 잡으면 eventMain 대표 이벤트 ──
        if len(promos) < 1:
            page.goto(self.EVENT_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)
            for pct in [0.2, 0.4, 0.0]:
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
                page.wait_for_timeout(600)
            promos = page.evaluate("""
                () => {
                    const seen=new Set(); const out=[]; const bad=/icon|sprite|blank|btn_|arrow|dot|logo|common/i;
                    document.querySelectorAll('a[href*="eventDetail"]').forEach(a => {
                        if (!a.href || seen.has(a.href) || !/nevntId=\\d/.test(a.href)) return;
                        const img=a.querySelector('img'); if(!img) return;
                        const b=img.src||img.dataset?.src||'';
                        if (b && bad.test(b)) return;
                        const t=(img.alt||a.innerText||'').replace(/\\s+/g,' ').trim();
                        seen.add(a.href); out.push({title:t.slice(0,80), url:a.href, banner_url:b});
                    });
                    return out.slice(0,8);
                }
            """)

        return promos
