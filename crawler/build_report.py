# -*- coding: utf-8 -*-
"""
build 스테이지: data/<날짜>.json + 스크린샷 → (Gemini 정제) → _deploy/
- 주차별 누적: _deploy/<주차키>.html + img/<주차키>/ + weeks.json(주차 목록)
- index.html = 이번 주(최신). 좌측 인덱스는 weeks.json 기반.
- 누적은 Songbird S3가 기존 파일을 보존(additive)할 때 유효. 발행 URL의 weeks.json을 불러와 갱신.
"""
import os, sys, json, glob, shutil, re, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DEPLOY = os.path.join(ROOT, "_deploy")
IMG = os.path.join(DEPLOY, "img")
# 발행 사이트 베이스 URL (누적용 weeks.json fetch). CI 변수 SONGBIRD_BASE_URL로 override 가능.
BASE_URL = os.environ.get("SONGBIRD_BASE_URL", "https://songbird.betawoowa.in/yenkim/bmart-competitor-research/").rstrip("/") + "/"
SITES_ORDER = [("naver_kurly", "네이버 컬리N마트", "#03c75a"),
               ("kurly", "마켓컬리", "#5f0080"),
               ("ssg", "SSG", "#cc1717")]

# ---------- 주차 계산 ----------
def week_info(date_str):
    d = datetime.date.fromisoformat(date_str)
    nth = (d.day - 1) // 7 + 1
    label = f"{d.year}년 {d.month}월 {nth}주차"
    key = f"{d.year}-{d.month:02d}-W{nth}"
    return key, label

# ---------- Gemini 정제 ----------
PROMPT = """너는 B마트마케팅팀의 경쟁사 프로모션 분석 에디터야.
아래는 '{site}'의 프로모션 페이지에서 수집한 텍스트야. (제목: {title})
[목표] 이 프로모션을 아래 항목으로 정리해줘.
[작성 규칙]
- 한국어. 추측 금지(텍스트에 없으면 "정보 없음").
- coupons는 핵심 혜택을 짧은 칩으로: tag=핵심 숫자/혜택, desc=짧은 조건.
- label은 프로모션을 한 줄로 요약한 제목.
[출력 포맷] 아래 JSON으로만:
{{"label":"...","benefit":"메인 베네핏 1~2문장","coupons":[{{"tag":"...","desc":"..."}}],
 "category":"대표 상품·카테고리","feat":"프로모션 특징","util":"B마트 활용방안"}}
[수집 텍스트]
{raw}
"""

_GENAI = None      # 모듈 캐시
_MODEL_NAME = None

def _pick_model(genai):
    """이 API 키로 generateContent 가능한 모델을 조회해 자동 선택(flash 우선)."""
    global _MODEL_NAME
    if _MODEL_NAME:
        return _MODEL_NAME
    avail = []
    for m in genai.list_models():
        methods = getattr(m, "supported_generation_methods", []) or []
        if "generateContent" in methods:
            avail.append(m.name)   # 예: "models/gemini-1.5-flash"
    if not avail:
        raise RuntimeError("generateContent 지원 모델 없음")
    # flash(빠르고 저렴) 우선, 없으면 첫 번째
    flash = [n for n in avail if "flash" in n.lower() and "vision" not in n.lower()]
    _MODEL_NAME = (flash or avail)[0]
    print(f"    [Gemini] 사용 모델: {_MODEL_NAME} (가용 {len(avail)}개)")
    return _MODEL_NAME

def gemini_refine(site_name, title, raw_text):
    global _GENAI
    key = os.environ.get("GEMINI_API_KEY")
    if not key: return None
    try:
        if _GENAI is None:
            import google.generativeai as genai
            genai.configure(api_key=key)
            _GENAI = genai
        genai = _GENAI
        mname = _pick_model(genai)
        model = genai.GenerativeModel(mname, generation_config={"response_mime_type": "application/json"})
        prompt = PROMPT.format(site=site_name, title=title or "", raw=(raw_text or "")[:6000])
        data = json.loads(model.generate_content(prompt).text)
        if not isinstance(data.get("coupons"), list): data["coupons"] = []
        return data
    except Exception as e:
        print(f"    [Gemini 실패] {site_name}/{title}: {e}")
        return None

def fallback_refine(title, raw_text):
    snip = re.sub(r"\s+", " ", (raw_text or "")).strip()[:240]
    return {"label": title or "프로모션", "benefit": snip or "정보 없음",
            "coupons": [], "category": "정보 없음", "feat": "정보 없음",
            "util": "정보 없음 (Gemini 미적용 — 폴백)"}

# ---------- 이미지(주차별 폴더) ----------
def prep_images(weekkey, site, idx, src_dir):
    out = {"thumb": "", "full": "", "banner": ""}
    wdir = os.path.join(IMG, weekkey); os.makedirs(wdir, exist_ok=True)
    rel = f"img/{weekkey}/"
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        full = os.path.join(src_dir, f"promo_{idx:02d}_full.png")
        kv = os.path.join(src_dir, f"promo_{idx:02d}_kv.png")
        src = full if (os.path.exists(full) and os.path.getsize(full) > 1000) else kv
        if os.path.exists(src):
            im = Image.open(src).convert("RGB"); w, h = im.size
            t = f"{site}_promo_{idx:02d}_top.jpg"
            im.crop((0, 0, w, min(760, h))).save(os.path.join(wdir, t), "JPEG", quality=82)
            out["thumb"] = rel + t
            f = f"{site}_promo_{idx:02d}_full.jpg"
            im.save(os.path.join(wdir, f), "JPEG", quality=80); out["full"] = rel + f
    except Exception as e:
        print(f"    [thumb 실패] {site}/{idx}: {e}")
    for b in glob.glob(os.path.join(src_dir, f"promo_{idx:02d}_banner.*")):
        try:
            from PIL import Image
            nm = f"{site}_promo_{idx:02d}_banner.jpg"
            Image.open(b).convert("RGB").save(os.path.join(wdir, nm), "JPEG", quality=82)
            out["banner"] = rel + nm
        except Exception:
            ext = b.rsplit(".", 1)[-1]; nm = f"{site}_promo_{idx:02d}_banner.{ext}"
            shutil.copy(b, os.path.join(wdir, nm)); out["banner"] = rel + nm
        break
    return out

# ---------- weeks.json (누적 목록) ----------
def load_weeks():
    # 1) 발행 사이트에서 기존 목록 가져오기(누적)
    try:
        import requests
        r = requests.get(BASE_URL + "weeks.json", timeout=8)
        if r.ok: return r.json()
    except Exception as e:
        print(f"    [weeks.json fetch 실패 → 폴백] {e}")
    # 2) 로컬 폴백
    p = os.path.join(DEPLOY, "weeks.json")
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: pass
    return []

# ---------- HTML ----------
def esc(s):
    import html as h
    return h.escape(s or "")

def render(weekkey, weeklabel, date, sites, weeks):
    css = open(os.path.join(ROOT, "_report_style.css"), encoding="utf-8").read()
    rp = os.path.join(ROOT, "_reference.html")
    ref = open(rp, encoding="utf-8").read() if os.path.exists(rp) else ""

    # 좌측 주차 인덱스
    nav = ""
    for w in weeks:
        cur = " cur" if w["key"] == weekkey else ""
        href = "index.html" if w["key"] == weekkey else f'{esc(w["key"])}.html'
        nav += f'<a class="wk{cur}" href="{href}">{esc(w["label"])}</a>'

    tabs, panels = [], []
    for i, s in enumerate(sites):
        ac = s["accent"]; act = " active" if i == 0 else ""
        tabs.append(f'<button class="tab{act}" data-t="{s["key"]}" style="--ac:{ac}">{esc(s["name"])}</button>')
        cards = ""
        for idx, p in enumerate(s["promos"]):
            def fig(cap, thumb, fullimg, with_btn=False):
                if not thumb: return ""
                full = fullimg or thumb
                btn = (f'<button class="fullbtn" data-full="{esc(full)}">이벤트 페이지 전체보기 ↗</button>'
                       if with_btn and fullimg else "")
                return (f'<figure class="zoom" data-full="{esc(full)}"><figcaption>{cap}</figcaption>'
                        f'<div class="imgwrap"><img loading="lazy" src="{esc(thumb)}">'
                        f'<span class="zoombadge">🔍 크게 보기</span></div></figure>{btn}')
            media = ""
            if p.get("banner"): media += fig("진입 배너", p.get("banner"), p.get("banner"))
            if p.get("thumb"):  media += fig("기획전 첫 화면", p.get("thumb"), p.get("full"), with_btn=True)
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
<title>경쟁사 프로모션 브리핑 — {esc(weeklabel)}</title><style>{css}</style></head>
<body>
<aside class="sidenav"><div class="sn-title">주차별 브리핑</div>{nav or '<div class="sn-empty">이번 주만 표시</div>'}</aside>
<div class="main">
<header class="top"><div class="wrap">
<div class="weekbadge">{esc(weeklabel)}</div>
<h1>경쟁사 프로모션 브리핑</h1>
<div class="meta">수집일 {date} · 대상 3개 사이트(쿠팡 제외) · Gemini 자동 정제 · 작성 B마트마케팅팀 김예인</div>
</div></header>
<div class="wrap"><div class="tabs">{''.join(tabs)}</div>{''.join(panels)}{ref}
<footer>경쟁사 프로모션 모니터링 · GitLab CI → Gemini 정제 → Songbird 배포 (자동)</footer>
</div></div>
<script>
document.querySelectorAll(".tab").forEach(function(b){{b.addEventListener("click",function(){{
document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
document.querySelectorAll(".panel").forEach(x=>x.classList.remove("active"));
b.classList.add("active");document.getElementById("p-"+b.dataset.t).classList.add("active");
window.scrollTo({{top:0,behavior:"smooth"}});}});}});
(function(){{var lb=document.createElement("div");lb.id="lightbox";
lb.innerHTML='<span id="lbclose">&times;</span><img id="lbimg">';
document.body.appendChild(lb);var lbimg=lb.querySelector("#lbimg");
function open(src){{if(!src)return;lbimg.src=src;lb.classList.add("on");}}
document.querySelectorAll(".zoom").forEach(function(f){{f.addEventListener("click",function(){{open(f.getAttribute("data-full"));}});}});
document.querySelectorAll(".fullbtn").forEach(function(b){{b.addEventListener("click",function(e){{e.stopPropagation();open(b.getAttribute("data-full"));}});}});
lb.addEventListener("click",function(){{lb.classList.remove("on");lbimg.src="";}});}})();
</script></body></html>"""
    return html

def main():
    jsons = sorted(glob.glob(os.path.join(DATA_DIR, "20*.json")))
    if not jsons: print("data/*.json 없음 — 종료"); sys.exit(1)
    data_path = jsons[-1]; date = os.path.basename(data_path)[:-5]
    raw = json.load(open(data_path, encoding="utf-8"))
    weekkey, weeklabel = week_info(date)
    os.makedirs(IMG, exist_ok=True)
    print(f"[build] data={data_path} week={weekkey}({weeklabel}) gemini={'ON' if os.environ.get('GEMINI_API_KEY') else 'OFF(폴백)'}")

    sites = []
    for key, name, accent in SITES_ORDER:
        promos = []
        src_dir = os.path.join(DATA_DIR, date, key)
        for idx, pr in enumerate((raw.get(key) or {}).get("promotions", [])[:3]):
            if pr.get("error"): continue
            refined = gemini_refine(name, pr.get("title"), pr.get("page_text")) or fallback_refine(pr.get("title"), pr.get("page_text"))
            imgs = prep_images(weekkey, key, idx, src_dir)
            refined.update({"url": pr.get("url", "#"), **imgs})
            promos.append(refined)
        if promos: sites.append({"key": key, "name": name, "accent": accent, "promos": promos})

    # weeks 목록 갱신(누적)
    weeks = load_weeks()
    weeks = [w for w in weeks if w.get("key") != weekkey]
    weeks.append({"key": weekkey, "label": weeklabel, "date": date})
    weeks.sort(key=lambda w: w["key"], reverse=True)

    html = render(weekkey, weeklabel, date, sites, weeks)
    os.makedirs(DEPLOY, exist_ok=True)
    open(os.path.join(DEPLOY, "index.html"), "w", encoding="utf-8").write(html)       # 최신
    open(os.path.join(DEPLOY, f"{weekkey}.html"), "w", encoding="utf-8").write(html)  # 주차 아카이브
    json.dump(weeks, open(os.path.join(DEPLOY, "weeks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[build] _deploy/index.html + {weekkey}.html 생성 ({len(sites)}사, 주차 {len(weeks)}개)")

if __name__ == "__main__":
    main()