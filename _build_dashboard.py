# -*- coding: utf-8 -*-
import json, base64, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DATE = "2026-06-01"
d = json.load(open(os.path.join(BASE, "_unzipped/data/%s.json" % DATA_DATE), encoding="utf-8"))
IMG_DIR = os.path.join(BASE, "_unzipped/data", DATA_DATE)

def b64(site, name):
    p = os.path.join(IMG_DIR, site, name)
    if not os.path.exists(p):
        return ""
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

# 분석 콘텐츠 (수집 JSON + KV 스크린샷 직접 판독 기반)
ANALYSIS = {
    "kurly": {
        "name": "마켓컬리", "status": "ok",
        "url": d["kurly"]["url"],
        "kv": "상단 고정 바 '지금 가입하고 최대 1만 2천원 할인 쿠폰' + 메인 KV 2단: ①'오늘 식단 분석하고 컬리 5천원 쿠폰 받기'(루희 AI 식단분석) ②'뷰티컬리 첫 구매 20% 쿠폰'",
        "corner": "베스트 · 세일 · 패션 · 리빙 · 신상 · 특가/혜택 (상단 GNB) / '나의 보유 쿠폰'·'이달의 결제 혜택' 개인화 진입 블록",
        "benefit": "신규가입 최대 1.2만원 쿠폰 · 뷰티컬리 첫구매 20% 쿠폰 · 식단분석 참여 5천원 쿠폰",
        "features": [
            "쿠폰을 '가입 → 첫구매 → 카테고리(뷰티)'로 단계별 분리해 신규 퍼널 전체를 쿠폰으로 설계",
            "'AI 식단분석'이라는 기능형 콘텐츠를 쿠폰 보상과 결합 → 단순 할인이 아닌 참여형 후킹",
            "개인화 블록(보유 쿠폰·결제 혜택)을 KV 바로 아래 배치해 재방문 고객 전환 유도",
        ],
        "util": [
            "B마트도 '신규가입→첫구매→카테고리 확장' 쿠폰을 단계별로 쪼개는 퍼널형 쿠폰 설계 검토",
            "푸드 활성·B마트 비유입 타깃에게 '기능형 참여 콘텐츠(레시피/식단)+쿠폰' 결합 배너 테스트",
        ],
    },
    "naver_kurly": {
        "name": "네이버 컬리N마트", "status": "ok",
        "url": d["naver_kurly"]["url"],
        "kv": "KV 3종 롤링: ①'첫 장보기는 쿠폰팩으로 시작! 최대 2만원 적립' ②'컬리N마트 네불엠 특가 — 대상 제품 10% 할인'(06.01~06.07) ③'단 7일, 최대 알뜰 미식 단독'",
        "corner": "오늘끝딜 · 컬리N마트 · 베스트 · 슈퍼적립 · 쇼핑라이브 · 지금배달 · 선물샵 / '실시간 인기 랭킹' + '지금 많이 담는 특가'(최대 55% OFF)",
        "benefit": "첫 장보기 쿠폰팩 최대 2만원 적립 · 네불엠 특가 10% · 알뜰 미식 7일 단독 · 슈퍼적립",
        "features": [
            "그로서리 직매입 상품을 '실시간 랭킹'으로 노출(깐마늘·우삼겹·훈제오리·닭가슴살 등) — 회전 빠른 신선/간편식 중심",
            "할인율(10~33%)과 '원가→할인가'를 상품마다 명시해 가격 매력도를 직접 비교시킴",
            "네이버 적립(슈퍼적립·2만원 적립)을 첫 구매 후킹의 핵심 레버로 사용 — 쿠폰보다 '적립' 프레이밍",
        ],
        "util": [
            "B마트 직매입 강점 품목(신선·정육·간편식)을 '실시간 랭킹/많이 담는 특가' 형태로 재구성해 회전감 강조",
            "'할인율+원가 대비' 가격 표기 방식을 B마트 그로서리 구좌 배너 카피에 차용 (CTR/CVR A/B 테스트)",
            "직접 경쟁(같은 컬리 소싱) 채널이므로 네불엠 특가 주기·품목을 주간 모니터링 1순위로",
        ],
    },
    "ssg": {
        "name": "SSG", "status": "ok",
        "url": d["ssg"]["url"],
        "kv": "메인 KV '강력한 혜택 SSG.COM 상품권' (상품권 증정형 프로모션) + '이벤트 & 쿠폰' 허브 페이지 구조",
        "corner": "진행중인 이벤트 전체 51개 (이벤트 36 · 구매사은 15) / 쓱닷컴 썸머 페스티벌, 쓱7클럽, 쓱머니 등 멤버십·머니 연계",
        "benefit": "SSG.COM 상품권 · 썸머 페스티벌(최대 3만원 혜택) · 쓱7클럽 친구초대 5천원 · 다수 무료체험단/구매사은",
        "features": [
            "체험단·구매사은 이벤트를 대량(51개)으로 운영 — 브랜드사 제휴/체험 물량으로 페이지를 채우는 방식",
            "'쓱머니·쓱7클럽' 등 자사 머니/멤버십과 프로모션을 강하게 결합",
            "그로서리 단독보다 뷰티·생활·백화점 등 종합몰 성격이 강함 (B마트와 직접 경쟁도는 상대적으로 낮음)",
        ],
        "util": [
            "체험단/구매사은형 이벤트의 '브랜드사 제휴 소싱' 방식은 B마트 제휴 프로모션 기획 시 벤치마크",
            "자사 머니(쓱머니)처럼 배민포인트·배민클럽과 프로모션을 묶는 결합 혜택 설계 참고",
        ],
    },
    "coupang": {
        "name": "쿠팡", "status": "fail",
        "url": d["coupang"]["url"],
        "kv": "수집 실패 — 봇 차단(Access Denied). 쿠팡이 자동화 접근을 차단함.",
        "corner": "-", "benefit": "-",
        "features": ["크롤러가 'Access Denied'(엣지 차단) 응답을 받아 콘텐츠 미수집",
                     "다음 수집 주기 전까지 우회 방법(헤더/세션, 또는 수동 캡처) 보완 필요"],
        "util": ["쿠팡은 봇 차단이 강해 자동 크롤링 한계 → 수동 스크린샷 또는 별도 수집 전략 검토 필요"],
    },
}

ORDER = ["naver_kurly", "kurly", "ssg", "coupang"]

def li(items):
    return "".join("<li>%s</li>" % x for x in items)

tabs, panels = [], []
for i, key in enumerate(ORDER):
    a = ANALYSIS[key]
    active = " active" if i == 0 else ""
    badge = '<span class="ok">수집 완료</span>' if a["status"] == "ok" else '<span class="fail">수집 실패</span>'
    tabs.append('<button class="tab%s" data-t="%s">%s</button>' % (active, key, a["name"]))
    kv_img = b64(key, "kv.png")
    full_img = b64(key, "full.png")
    img_block = ('<div class="shot"><img src="%s" alt="KV"/><div class="cap">KV 영역 (상단 첫 화면)</div></div>' % kv_img) if kv_img else ""
    full_block = ('<details class="full"><summary>전체 페이지 스크린샷 보기</summary><img src="%s" alt="full"/></details>' % full_img) if full_img else ""
    cards = """
      <div class="grid">
        <div class="card"><h4>🖼️ KV / 메인 비주얼</h4><p>%s</p></div>
        <div class="card"><h4>🧩 코너 구성</h4><p>%s</p></div>
        <div class="card"><h4>🎁 주요 혜택 · 쿠폰</h4><p>%s</p></div>
        <div class="card feat"><h4>🔍 특징</h4><ul>%s</ul></div>
        <div class="card util"><h4>💡 B마트 활용 포인트</h4><ul>%s</ul></div>
      </div>""" % (a["kv"], a["corner"], a["benefit"], li(a["features"]), li(a["util"]))
    panels.append("""<section class="panel%s" id="p-%s">
      <div class="phead"><h2>%s %s</h2><a href="%s" target="_blank" rel="noopener">%s ↗</a></div>
      %s%s%s
    </section>""" % (active, key, a["name"], badge, a["url"], a["url"], img_block, full_block, cards))

html = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>경쟁사 프로모션 모니터링 — %s</title>
<style>
:root{color-scheme:light}
*{box-sizing:border-box}
body{margin:0;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#f4f5f7;color:#1a1a2e;line-height:1.6}
.wrap{max-width:1080px;margin:0 auto;padding:28px 20px 60px}
header.top h1{font-size:22px;margin:0 0 4px}
header.top .meta{color:#6b7280;font-size:13px}
.summary{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px 20px;margin:18px 0 8px}
.summary h3{margin:0 0 8px;font-size:15px;color:#5b21b6}
.summary p{margin:6px 0;font-size:14px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:22px 0 0;position:sticky;top:0;background:#f4f5f7;padding:8px 0;z-index:5}
.tab{border:1px solid #d1d5db;background:#fff;border-radius:999px;padding:8px 16px;font-size:14px;cursor:pointer;color:#374151}
.tab.active{background:#5b21b6;border-color:#5b21b6;color:#fff;font-weight:600}
.panel{display:none;animation:f .2s ease}
.panel.active{display:block}
@keyframes f{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
.phead{display:flex;align-items:center;gap:12px;margin:18px 0 12px;flex-wrap:wrap}
.phead h2{font-size:19px;margin:0}
.phead a{font-size:12px;color:#6b7280;text-decoration:none;word-break:break-all}
.ok{font-size:11px;background:#dcfce7;color:#166534;padding:3px 9px;border-radius:999px}
.fail{font-size:11px;background:#fee2e2;color:#991b1b;padding:3px 9px;border-radius:999px}
.shot{border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;background:#fff;margin-bottom:12px}
.shot img{width:100%%;display:block}
.cap{font-size:12px;color:#6b7280;padding:8px 12px;background:#fafafa;border-top:1px solid #f0f0f0}
.full{margin:0 0 16px}
.full summary{cursor:pointer;font-size:13px;color:#5b21b6;padding:8px 0}
.full img{width:100%%;border:1px solid #e5e7eb;border-radius:12px;margin-top:8px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px}
.card h4{margin:0 0 8px;font-size:14px}
.card p{margin:0;font-size:13.5px;color:#374151}
.card ul{margin:0;padding-left:18px;font-size:13.5px;color:#374151}
.card li{margin-bottom:6px}
.card.feat{grid-column:1/2}
.card.util{grid-column:2/3;background:#faf5ff;border-color:#e9d5ff}
.card.util h4{color:#6d28d9}
@media(max-width:720px){.grid{grid-template-columns:1fr}.card.feat,.card.util{grid-column:auto}}
footer{margin-top:34px;font-size:12px;color:#9ca3af;text-align:center}
</style></head>
<body><div class="wrap">
<header class="top"><h1>경쟁사 프로모션 모니터링 리포트</h1>
<div class="meta">수집일 %s · 대상 4개 사이트 · 작성: B마트마케팅팀 김예인</div></header>

<div class="summary">
<h3>📌 이번 주 한눈에 보기</h3>
<p><b>공통 흐름</b> — 3개 사이트 모두 <b>신규·첫구매 후킹</b>을 KV 최상단에 배치(컬리 가입 1.2만원 쿠폰 / 네이버 컬리N마트 첫 장보기 2만원 적립 / SSG 상품권). 신규 유입 경쟁이 프로모션의 1순위.</p>
<p><b>가장 주목</b> — <b>네이버 컬리N마트</b>는 B마트와 가장 직접 경쟁하는 그로서리 채널. '실시간 랭킹 + 할인율 명시 + 적립 프레이밍'으로 직매입 상품 회전을 강조 → 주간 모니터링 1순위.</p>
<p><b>차별 포인트</b> — 컬리는 'AI 식단분석' 같은 <b>기능형 참여 콘텐츠 + 쿠폰</b> 결합, SSG는 <b>체험단·구매사은 51개</b> 물량 + 자사 머니 연계.</p>
<p><b>수집 이슈</b> — 쿠팡은 봇 차단(Access Denied)으로 미수집. 다음 주기 전 수집 방식 보완 필요.</p>
</div>

<div class="tabs">%s</div>
%s

<footer>경쟁사 프로모션 모니터링 PoC · 데이터 출처: GitLab CI Artifacts(%s) · B마트마케팅팀</footer>
</div>
<script>
document.querySelectorAll('.tab').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active')});
    document.querySelectorAll('.panel').forEach(function(x){x.classList.remove('active')});
    b.classList.add('active');
    document.getElementById('p-'+b.dataset.t).classList.add('active');
    window.scrollTo({top:0,behavior:'smooth'});
  });
});
</script>
</body></html>""" % (DATA_DATE, DATA_DATE, "".join(tabs), "".join(panels), DATA_DATE)

out = os.path.join(BASE, "경쟁사_프로모션_리포트_%s.html" % DATA_DATE)
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("written:", out, os.path.getsize(out), "bytes")
