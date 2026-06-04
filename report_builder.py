# -*- coding: utf-8 -*-
"""경쟁사 프로모션 브리핑 HTML 생성기 v2 (가독성 개선 + 상세 분석).
사용법: python report_builder.py <analysis.json> <thumbs_dir> <YYYY-MM-DD> <out.html>
analysis 항목: key,name,accent,tag,promos[{label,thumb,banner,url,benefit,coupon,category,feat,util}]
"""
import base64, os, sys, json, html as _h

def b64(thumbs_dir, name):
    if not name: return ""
    p = os.path.join(thumbs_dir, name)
    if not os.path.exists(p): return ""
    ext = name.rsplit(".",1)[-1].lower()
    mime = "image/jpeg" if ext in ("jpg","jpeg") else ("image/webp" if ext=="webp" else "image/png")
    return f"data:{mime};base64," + base64.b64encode(open(p,"rb").read()).decode()

def esc(s): return _h.escape(s or "")

def build(analysis_path, thumbs_dir, date, out_path):
    SITES = json.load(open(analysis_path, encoding="utf-8"))
    here = os.path.dirname(os.path.abspath(__file__))
    CSS = open(os.path.join(here, "_report_style.css"), encoding="utf-8").read()
    rp = os.path.join(here, "_reference.html")
    REF = open(rp, encoding="utf-8").read() if os.path.exists(rp) else ""

    tabs, panels = [], []
    for i, s in enumerate(SITES):
        ac = s.get("accent", "#7c3aed")
        active = " active" if i == 0 else ""
        tabs.append(f'<button class="tab{active}" data-t="{s["key"]}" style="--ac:{ac}">{esc(s["name"])}</button>')
        cards = ""
        for idx, p in enumerate(s["promos"]):
            banner = b64(thumbs_dir, p.get("banner",""))
            kv = b64(thumbs_dir, p.get("thumb",""))
            media = ""
            if banner:
                media += f'<figure><figcaption>진입 배너</figcaption><img loading="lazy" src="{banner}"></figure>'
            if kv:
                media += f'<figure><figcaption>기획전 첫 화면</figcaption><img loading="lazy" src="{kv}"></figure>'
            url = p.get("url", "#")
            open_btn = f'<a class="open" href="{esc(url)}" target="_blank" rel="noopener">프로모션 페이지 열기 ↗</a>'
            def row(label, val, cls=""):
                if not val: return ""
                return f'<div class="row {cls}"><h4>{label}</h4><p>{esc(val)}</p></div>'
            info = (row("메인 베네핏", p.get("benefit"), "hl-b")
                    + row("쿠폰 스킴", p.get("coupon"), "hl-c")
                    + row("대표 상품·카테고리", p.get("category"))
                    + row("프로모션 특징", p.get("feat"))
                    + row("B마트 활용방안", p.get("util"), "hl-u"))
            cards += (f'<article class="pc">'
                      f'<div class="pc-head"><span class="ix">PROMO {idx+1:02d}</span><h3>{esc(p["label"])}</h3></div>'
                      f'<div class="pc-body"><div class="pc-media">{media}{open_btn}</div>'
                      f'<div class="pc-info">{info}</div></div></article>')
        panels.append(f'<section class="panel{active}" id="p-{s["key"]}" style="--ac:{ac}">'
                      f'<div class="shead"><span class="dot"></span><h2>{esc(s["name"])}</h2>'
                      f'<span class="tagb">{esc(s.get("tag",""))}</span>'
                      f'<span class="cnt">상위 노출 {len(s["promos"])}건</span></div>{cards}</section>')

    htmldoc = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>이번 주 경쟁사 프로모션 브리핑 — {date}</title><style>{CSS}</style></head>
<body><header class="top"><div class="wrap">
<div class="ey">COMPETITOR PROMOTION BRIEFING</div>
<h1>이번 주 경쟁사 프로모션 브리핑</h1>
<div class="meta">수집일 {date} · 대상 3개 사이트(쿠팡 제외) · 사이트별 상위 노출 3건 · 작성 B마트마케팅팀 김예인</div>
</div></header>
<div class="wrap"><div class="tabs">{''.join(tabs)}</div>{''.join(panels)}
{REF}
<footer>경쟁사 프로모션 모니터링 · 각 카드: 진입 배너 / 기획전 첫 화면 / 상세 분석 · 데이터 출처: GitLab CI Artifacts({date})</footer>
</div>
<script>
document.querySelectorAll(".tab").forEach(function(b){{b.addEventListener("click",function(){{
document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
document.querySelectorAll(".panel").forEach(x=>x.classList.remove("active"));
b.classList.add("active");document.getElementById("p-"+b.dataset.t).classList.add("active");
window.scrollTo({{top:0,behavior:"smooth"}});
}});}});
</script></body></html>"""
    open(out_path, "w", encoding="utf-8").write(htmldoc)
    print("written", out_path, os.path.getsize(out_path), "bytes")

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
