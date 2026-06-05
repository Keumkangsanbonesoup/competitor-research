# -*- coding: utf-8 -*-
"""
build 스테이지 엔트리포인트.
  data/<날짜>.json + 스크린샷  →  (Gemini 정제)  →  _deploy/index.html + _deploy/img/
- Gemini(google-generativeai)로 page_text를 5개 항목 구조로 정제.
- GEMINI_API_KEY 없거나 호출 실패 시: page_text 발췌 폴백(파이프라인 안 깨짐).
- 이미지는 _deploy/img/ 로 복사(상대경로 <img src>)해서 Songbird 배포.
사용: python crawler/build_report.py        # CI build 잡에서 실행
"""
import os, sys, json, glob, shutil, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo 루트
DATA_DIR = os.path.join(ROOT, "data")
DEPLOY = os.path.join(ROOT, "_deploy")
IMG = os.path.join(DEPLOY, "img")
SITES_ORDER = [("naver_kurly", "네이버 컬리N마트", "#03c75a"),
               ("kurly", "마켓컬리", "#5f0080"),
               ("ssg", "SSG", "#cc1717")]

# ---------- Gemini 정제 ----------
PROMPT = """너는 B마트마케팅팀의 경쟁사 프로모션 분석 에디터야.
아래는 '{site}'의 프로모션 페이지에서 수집한 텍스트야. (제목: {title})

[목표] 이 프로모션을 아래 항목으로 정리해줘.
[작성 규칙]
- 한국어. 추측 금지(텍스트에 없으면 "정보 없음").
- coupons는 핵심 혜택을 짧은 칩으로: tag=핵심 숫자/혜택(예 "멤버십 10%"), desc=짧은 조건.
- label은 프로모션을 한 줄로 요약한 제목.

[출력 포맷] 아래 JSON으로만:
{{
 "label": "...",
 "benefit": "메인 베네핏 1~2문장",
 "coupons": [{{"tag":"...","desc":"..."}}],
 "category": "대표 상품·카테고리",
 "feat": "프로모션 특징",
 "util": "B마트 활용방안"
}}

[수집 텍스트]
{raw}
"""

def gemini_refine(site_name, title, raw_text):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        cfg = {"response_mime_type": "application/json"}
        prompt = PROMPT.format(site=site_name, title=title or "", raw=(raw_text or "")[:6000])
        # 라이브러리/계정별로 가용 모델명이 다를 수 있어 순차 시도
        last = None
        for mname in ("gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest"):
            try:
                model = genai.GenerativeModel(mname, generation_config=cfg)
                resp = model.generate_content(prompt)
                data = json.loads(resp.text)
                break
            except Exception as e:
                last = e; continue
        else:
            raise last or RuntimeError("no model")
        if "coupons" not in data or not isinstance(data.get("coupons"), list):
            data["coupons"] = []
        return data
    except Exception as e:
        print(f"    [Gemini 실패] {site_name}/{title}: {e}")
        return None

def fallback_refine(title, raw_text):
    snip = re.sub(r"\s+", " ", (raw_text or "")).strip()[:240]
    return {"label": title or "프로모션", "benefit": snip or "정보 없음",
            "coupons": [], "category": "정보 없음", "feat": "정보 없음",
            "util": "정보 없음 (Gemini 미적용 — 폴백)"}

# ---------- 이미지 준비 ----------
def prep_images(date, site, idx, src_dir):
    """full(또는 kv) 상단 크롭 + 배너 → _deploy/img/ 로 저장, 상대경로 반환."""
    out = {"thumb": "", "banner": ""}
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        full = os.path.join(src_dir, f"promo_{idx:02d}_full.png")
        kv = os.path.join(src_dir, f"promo_{idx:02d}_kv.png")
        src = full if (os.path.exists(full) and os.path.getsize(full) > 1000) else kv
        if os.path.exists(src):
            im = Image.open(src).convert("RGB")
            w, h = im.size
            crop = im.crop((0, 0, w, min(760, h)))
            name = f"{site}_promo_{idx:02d}_top.jpg"
            crop.save(os.path.join(IMG, name), "JPEG", quality=82)
            out["thumb"] = "img/" + name
    except Exception as e:
        print(f"    [thumb 실패] {site}/{idx}: {e}")
    for b in glob.glob(os.path.join(src_dir, f"promo_{idx:02d}_banner.*")):
        try:
            from PIL import Image
            im = Image.open(b).convert("RGB")
            name = f"{site}_promo_{idx:02d}_banner.jpg"
            im.save(os.path.join(IMG, name), "JPEG", quality=82)
            out["banner"] = "img/" + name
        except Exception:
            ext = b.rsplit(".", 1)[-1]
            name = f"{site}_promo_{idx:02d}_banner.{ext}"
            shutil.copy(b, os.path.join(IMG, name)); out["banner"] = "img/" + name
        break
    return out

# ---------- HTML 렌더 ----------
def esc(s):
    import html as h
    return h.escape(s or "")

def render(date, sites):
    css = open(os.path.join(ROOT, "_report_style.css"), encoding="utf-8").read()
    rp = os.path.join(ROOT, "_reference.html")
    ref = open(rp, encoding="utf-8").read() if os.path.exists(rp) else ""
    tabs, panels = [], []
    for i, s in enumerate(sites):
        ac = s["accent"]; act = " active" if i == 0 else ""
        tabs.append(f'<button class="tab{act}" data-t="{s["key"]}" style="--ac:{ac}">{esc(s["name"])}</button>')
        cards = ""
        for idx, p in enumerate(s["promos"]):
            media = ""
            if p.get("banner"): media += f'<figure><figcaption>진입 배너</figcaption><img loading="lazy" src="{p["banner"]}"></figure>'
            if p.get("thumb"): media += f'<figure><figcaption>기획전 첫 화면</figcaption><img loading="lazy" src="{p["thumb"]}"></figure>'
            chips = "".join(f'<span class="chip"><b>{esc(c.get("tag",""))}</b><i>{esc(c.get("desc",""))}</i></span>' for c in p.get("coupons", []))
            coupon_row = f'<div class="row hl-c"><h4>쿠폰 스킴</h4><div class="chips">{chips}</div></div>' if chips else ""
            def row(lbl, val, cls=""):
                return f'<div class="row {cls}"><h4>{lbl}</h4><p>{esc(val)}</p></div>' if val else ""
            info = (row("메인 베네핏", p.get("benefit"), "hl-b") + coupon_row
                    + row("대표 상품·카테고리", p.get("category"))
                    + row("프로모션 특징", p.get("feat"))
                    + row("B마트 활용방안", p.get("util"), "hl-u"))
            open_btn = f'<a class="open" href="{esc(p.get("url","#"))}" target="_blank" rel="noopener">프로모션 페이지 열기 ↗</a>'
            cards += (f'<article class="pc"><div class="pc-head"><span class="ix">PROMO {idx+1:02d}</span><h3>{esc(p.get("label"))}</h3></div>'
                      f'<div class="pc-body"><div class="pc-media">{media}{open_btn}</div><div class="pc-info">{info}</div></div></article>')
        panels.append(f'<section class="panel{act}" id="p-{s["key"]}" style="--ac:{ac}"><div class="shead"><span class="dot"></span>'
                      f'<h2>{esc(s["name"])}</h2><span class="cnt">상위 노출 {len(s["promos"])}건</span></div>{cards}</section>')
    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>이번 주 경쟁사 프로모션 브리핑 — {date}</title><style>{css}</style></head>
<body><header class="top"><div class="wrap"><div class="ey">COMPETITOR PROMOTION BRIEFING</div>
<h1>이번 주 경쟁사 프로모션 브리핑</h1>
<div class="meta">수집일 {date} · 대상 3개 사이트(쿠팡 제외) · Gemini 자동 정제 · 작성 B마트마케팅팀 김예인</div>
</div></header><div class="wrap"><div class="tabs">{''.join(tabs)}</div>{''.join(panels)}{ref}
<footer>경쟁사 프로모션 모니터링 · GitLab CI → Gemini 정제 → Songbird 배포 (자동)</footer></div>
<script>document.querySelectorAll(".tab").forEach(function(b){{b.addEventListener("click",function(){{
document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
document.querySelectorAll(".panel").forEach(x=>x.classList.remove("active"));
b.classList.add("active");document.getElementById("p-"+b.dataset.t).classList.add("active");
window.scrollTo({{top:0,behavior:"smooth"}});}});}});</script></body></html>"""
    return html

def main():
    jsons = sorted(glob.glob(os.path.join(DATA_DIR, "20*.json")))
    if not jsons:
        print("data/*.json 없음 — 종료"); sys.exit(1)
    data_path = jsons[-1]
    date = os.path.basename(data_path)[:-5]
    raw = json.load(open(data_path, encoding="utf-8"))
    os.makedirs(IMG, exist_ok=True)
    use_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    print(f"[build] data={data_path} date={date} gemini={'ON' if use_gemini else 'OFF(폴백)'}")

    sites = []
    for key, name, accent in SITES_ORDER:
        promos_in = (raw.get(key) or {}).get("promotions", [])[:3]
        promos = []
        src_dir = os.path.join(DATA_DIR, date, key)
        for idx, pr in enumerate(promos_in):
            if pr.get("error"): 
                continue
            refined = gemini_refine(name, pr.get("title"), pr.get("page_text")) or fallback_refine(pr.get("title"), pr.get("page_text"))
            imgs = prep_images(date, key, idx, src_dir)
            refined.update({"url": pr.get("url", "#"), "thumb": imgs["thumb"], "banner": imgs["banner"]})
            promos.append(refined)
        if promos:
            sites.append({"key": key, "name": name, "accent": accent, "promos": promos})

    html = render(date, sites)
    os.makedirs(DEPLOY, exist_ok=True)
    open(os.path.join(DEPLOY, "index.html"), "w", encoding="utf-8").write(html)
    print(f"[build] _deploy/index.html 생성 ({len(sites)}개 사이트), 이미지 {len(os.listdir(IMG))}개")

if __name__ == "__main__":
    main()
