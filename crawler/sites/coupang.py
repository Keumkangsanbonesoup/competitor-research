import json

from base import BaseCrawler

HOME_URL = "https://www.coupang.com/"
CAMPAIGNS_URL = "https://www.coupang.com/np/campaigns/"


class CoupangCrawler(BaseCrawler):
    """
    쿠팡 크롤러 (Scrapling/Camoufox 기반 Akamai 우회 시도).
    패턴: 메인 진입 → 20초 대기(Akamai JS 챌린지 자동 해결) → 캠페인 페이지 이동 → 배너 추출.
    - 공유 playwright page 대신 Scrapling StealthyFetcher(Camoufox) 사용 → crawl() 오버라이드.
    - 실패/차단 시 빈 목록 + 진단만 남기고 정상 종료(다른 사이트 영향 없음).
    """
    LISTING_URL = HOME_URL

    def __init__(self):
        super().__init__("coupang", "쿠팡", self.LISTING_URL)

    def get_promo_urls(self, page):
        return []  # 미사용 (crawl 오버라이드)

    def _result(self, promos, note=None, error=None):
        d = {"site": self.site_key, "site_name": self.site_name,
             "crawled_at": self.crawled_at, "listing_url": self.listing_url,
             "promotions": promos}
        if note: d["note"] = note
        if error: d["error"] = error
        return d

    def crawl(self, page):
        try:
            from scrapling.fetchers import StealthyFetcher
        except Exception as e:
            print(f"  [쿠팡] Scrapling 미설치: {e}")
            return self._result([], error=f"scrapling import 실패: {e}")

        img_dir = self.img_dir
        box = {"denied": None, "title": "", "promos": [], "err": None}

        def action(pg):
            try:
                # 1) 메인에서 Akamai JS 챌린지 해결 대기
                pg.wait_for_timeout(20000)
                # 2) 캠페인(이벤트) 페이지로 이동
                pg.goto(CAMPAIGNS_URL, wait_until="domcontentloaded", timeout=40000)
                pg.wait_for_timeout(4000)
                for p in [0.25, 0.5, 0.75, 0.0]:
                    pg.evaluate(f"window.scrollTo(0, document.body.scrollHeight*{p})")
                    pg.wait_for_timeout(700)
                box["title"] = pg.title()
                content = pg.content()
                if "Access Denied" in box["title"] or "Access Denied" in content[:1500]:
                    box["denied"] = True
                    return pg
                box["denied"] = False
                # 캠페인 페이지 전체 스크린샷
                try:
                    pg.screenshot(path=str(img_dir / "campaigns_full.png"), full_page=True)
                except Exception:
                    pass
                # 상단 배너/캠페인 링크 추출 (폭 큰 이미지 링크)
                box["promos"] = pg.evaluate("""
                    () => {
                        const seen=new Set(); const out=[];
                        document.querySelectorAll('a[href]').forEach(a=>{
                            const img=a.querySelector('img'); if(!img) return;
                            const w=img.naturalWidth||img.width||0; if(w<200) return;
                            const href=a.href||''; if(!href.startsWith('http')||seen.has(href)) return;
                            seen.add(href);
                            out.push({title:(img.alt||a.innerText||'쿠팡 프로모션').trim().slice(0,70),
                                      url:href, banner_url:img.src||img.dataset?.src||''});
                        });
                        return out.slice(0,8);
                    }
                """)
            except Exception as e:
                box["err"] = str(e)[:200]
            return pg

        try:
            StealthyFetcher.fetch(HOME_URL, headless=True, network_idle=True,
                                  page_action=action, timeout=120000)
        except Exception as e:
            print(f"  [쿠팡] Scrapling fetch 실패: {e}")
            return self._result([], error=f"scrapling fetch 실패: {e}")

        # 진단 저장
        try:
            (img_dir / "_debug_coupang.json").write_text(json.dumps(
                {"denied": box["denied"], "title": box["title"],
                 "n_promos": len(box["promos"]), "err": box["err"]},
                ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        print(f"  [쿠팡] denied={box['denied']} title={box['title']!r} promos={len(box['promos'])}")

        if box["denied"] or not box["promos"]:
            return self._result([], note="Scrapling 시도 — 차단/빈결과", error=box["err"])

        promos = []
        for i, pr in enumerate(box["promos"][:3]):
            promos.append({"title": pr.get("title") or "쿠팡 프로모션",
                           "url": pr.get("url"), "banner_url": pr.get("banner_url"),
                           "kv_screenshot": "data/%s/coupang/campaigns_full.png" % self.crawled_at,
                           "page_text": ""})
        return self._result(promos, note="Scrapling/Camoufox 성공")
