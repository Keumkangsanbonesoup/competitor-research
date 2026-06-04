import json
import re

from playwright.sync_api import Page

from base import BaseCrawler


class SSGCrawler(BaseCrawler):
    """
    SSG닷컴 크롤러 (진단 강화판).
    - 페이지가 호출하는 배너/ajax 요청 URL을 기록
    - ajaxVerticalBanners 직접 호출 + 응답 스니펫 저장
    - page.content()에 히어로 배너 데이터가 들어있는지 검사
    - 폴백: eventDetail 대표 이벤트
    """
    LISTING_URL = "https://www.ssg.com/event/eventMain.ssg"
    HOME_URL = "https://www.ssg.com/"

    def __init__(self):
        super().__init__("ssg", "SSG", self.LISTING_URL)

    def get_promo_urls(self, page: Page) -> list:
        captured = []
        def on_resp(resp):
            try:
                u = resp.url
                if re.search(r"banner|ajax|disp|main|vertical|hero|promo", u, re.I):
                    captured.append({"url": u[:200], "status": resp.status,
                                     "ct": resp.headers.get("content-type", "")[:40]})
            except Exception:
                pass
        page.on("response", on_resp)

        # 홈으로 먼저 가서 메인 히어로 배너 트리거 시도
        page.goto(self.HOME_URL, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        page.wait_for_timeout(2500)
        for pct in [0.15, 0.3, 0.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            page.wait_for_timeout(700)

        # page.content() 안에 히어로 흔적이 있는지
        html = ""
        try:
            html = page.content()
        except Exception:
            pass
        content_checks = {
            "html_len": len(html),
            "has_ssghero": "ssghero" in html,
            "has_planShop": "planShop" in html,
            "has_titmain": "titmain" in html,
            "has_carousel_kw": bool(re.search(r"고래잇|장보기특가|오픈런|썸머", html)),
        }

        # ajaxVerticalBanners 직접 호출(세션 쿠키 사용)
        ajax = {}
        for u in ["https://www.ssg.com/ssgMain/ajaxVerticalBanners.ssg",
                  "https://www.ssg.com/ssgMain/ajaxMainBanners.ssg"]:
            try:
                r = page.request.get(u, timeout=10000)
                body = r.text()
                ajax[u] = {"status": r.status, "len": len(body),
                           "snippet": body[:600]}
            except Exception as e:
                ajax[u] = {"error": str(e)[:120]}

        diag = {
            "content_checks": content_checks,
            "captured_requests": captured[:40],
            "ajax_probe": ajax,
        }
        try:
            (self.img_dir / "_debug_network.json").write_text(
                json.dumps(diag, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        print(f"    [SSG 네트워크 진단] content={content_checks} captured={len(captured)}건")

        # ── 폴백 수집: eventMain 의 eventDetail 대표 이벤트 (리포트가 비지 않도록) ──
        page.goto(self.LISTING_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        for pct in [0.2, 0.4, 0.0]:
            page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pct})")
            page.wait_for_timeout(600)
        promos = page.evaluate("""
            () => {
                const seen=new Set(); const out=[]; const bad=/icon|sprite|blank|btn_|arrow|dot|logo|common/i;
                document.querySelectorAll('a[href*="eventDetail"]').forEach(a => {
                    if (!a.href || seen.has(a.href)) return;
                    if (!/nevntId=\\d/.test(a.href)) return;
                    const img=a.querySelector('img'); if(!img) return;
                    const b=img.src||img.dataset?.src||img.dataset?.original||'';
                    if (b && bad.test(b)) return;
                    const t=(img.alt||a.innerText||'').replace(/\\s+/g,' ').trim();
                    seen.add(a.href);
                    out.push({title:t.slice(0,70), url:a.href, banner_url:b});
                });
                return out.slice(0,8);
            }
        """)
        return promos
