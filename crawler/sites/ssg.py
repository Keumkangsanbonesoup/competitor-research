import json
from pathlib import Path

from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG닷컴 크롤러. eventMain.ssg 메인 히어로 캐러셀(ssghero) 배너 수집 + 진단 로그.
    """
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        page.goto(self.listing_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        # JS 캐러셀 렌더 대기: ssghero가 뜨면 잡고, 없으면 8초까지 기다렸다 진행
        try:
            page.wait_for_selector('a[class*="ssghero"], a[class*="hero"][class*="imglink"]', timeout=8000)
        except Exception:
            pass
        for pct in [0.15, 0.3, 0.15, 0.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            page.wait_for_timeout(700)

        # ── 진단: 크롤러가 실제로 받은 DOM에서 셀렉터별 개수/샘플 수집 ──
        diag = page.evaluate("""
            () => {
                const cnt = sel => document.querySelectorAll(sel).length;
                const sample = sel => Array.from(document.querySelectorAll(sel)).slice(0,5).map(a => ({
                    cls: a.className, href: a.href,
                    alt: (a.querySelector('img')?.alt||'').slice(0,40)
                }));
                return {
                    title: document.title,
                    bodyLen: document.body.innerText.length,
                    cnt_ssghero: cnt('a[class*="ssghero"]'),
                    cnt_hero: cnt('a[class*="hero"]'),
                    cnt_imglink: cnt('a[class*="imglink"]'),
                    cnt_planShop: cnt('a[href*="planShop"]'),
                    cnt_eventDetail: cnt('a[href*="eventDetail"]'),
                    cnt_swiper: cnt('[class*="swiper"]'),
                    cnt_aImg: Array.from(document.querySelectorAll('a')).filter(a=>a.querySelector('img')).length,
                    sample_planShop: sample('a[href*="planShop"]'),
                    sample_imglink: sample('a[class*="imglink"]'),
                };
            }
        """)
        try:
            (self.img_dir / "_debug_listing.json").write_text(
                json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        print(f"    [SSG 진단] ssghero={diag.get('cnt_ssghero')} planShop={diag.get('cnt_planShop')} "
              f"imglink={diag.get('cnt_imglink')} eventDetail={diag.get('cnt_eventDetail')} aImg={diag.get('cnt_aImg')}")

        # 1순위: 히어로 캐러셀
        promos = page.evaluate("""
            () => {
                const seen = new Set(); const results = [];
                document.querySelectorAll('a[class*="ssghero"][class*="imglink"], a[class*="hero"][class*="imglink"]').forEach(a => {
                    if (!a.href || seen.has(a.href)) return;
                    const img = a.querySelector('img');
                    let title = '';
                    const main = a.querySelector('[class*="titmain"]');
                    const sub  = a.querySelector('[class*="titsub"]');
                    if (main) title = main.innerText.replace(/\\s+/g,' ').trim();
                    if (!title && img) title = (img.alt||'').trim();
                    if (sub) { const s=sub.innerText.replace(/\\s+/g,' ').trim(); if(s) title=(title+' · '+s).trim(); }
                    let banner_url='';
                    if (img){ if(img.srcset) banner_url=img.srcset.split(',').pop().trim().split(' ')[0]; banner_url=banner_url||img.src||img.dataset?.src||''; }
                    seen.add(a.href);
                    results.push({ title: title.slice(0,70), url: a.href, banner_url });
                });
                return results.slice(0,8);
            }
        """)

        # 2순위: planShop 링크(히어로가 클래스 없이 렌더된 경우)
        if len(promos) < 2:
            more = page.evaluate("""
                () => {
                    const seen=new Set(); const results=[];
                    document.querySelectorAll('a[href*="planShop"]').forEach(a => {
                        if (seen.has(a.href)) return;
                        const img=a.querySelector('img');
                        const title=(a.querySelector('[class*="titmain"]')?.innerText || img?.alt || a.innerText||'').replace(/\\s+/g,' ').trim();
                        seen.add(a.href);
                        results.push({ title:title.slice(0,70), url:a.href, banner_url:img?.src||'' });
                    });
                    return results.slice(0,8);
                }
            """)
            urls={p["url"] for p in promos}
            for m in more:
                if m["url"] not in urls and m.get("url"): promos.append(m); urls.add(m["url"])

        # 3순위: 폭 큰 배너 이미지
        if len(promos) < 2:
            more = page.evaluate("""
                () => {
                    const seen=new Set(); const results=[]; const bad=/icon|sprite|blank|btn_|arrow|dot/i;
                    document.querySelectorAll('a').forEach(a => {
                        const img=a.querySelector('img'); if(!img||!a.href) return;
                        const src=img.src||img.dataset?.src||''; if(!src||bad.test(src)) return;
                        const w=img.naturalWidth||img.width||0; if(w<500) return;
                        if(seen.has(a.href)) return; seen.add(a.href);
                        results.push({ title:(img.alt||'').trim().slice(0,70), url:a.href, banner_url:src });
                    });
                    return results.slice(0,8);
                }
            """)
            urls={p["url"] for p in promos}
            for m in more:
                if m["url"] not in urls: promos.append(m); urls.add(m["url"])

        return promos
