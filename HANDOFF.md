# 경쟁사 프로모션 모니터링 — 인수인계 문서

> 코워크 모드에서 이 파일을 읽고 작업을 이어가세요.

---

## 1. 프로젝트 개요

경쟁사(쿠팡·마켓컬리·SSG·네이버 컬리N마트)의 프로모션 페이지를 매주 자동 크롤링해서
KV, 코너 구성, 혜택/쿠폰 스킴, 이미지 등을 수집하고 B마트 마케팅팀이 활용할 수 있는
인사이트를 도출하는 파이프라인이에요.

**PoC는 두 단계로 나뉘어요:**
- **PoC 1 (완료)**: 백엔드 크롤링 + GitLab CI 자동 스케줄
- **PoC 2 (진행 예정)**: 수집 데이터를 HTML 리포트로 시각화

---

## 2. GitLab 레포

```
https://git.baemin.in/yenkim/bmart-competitor-research
브랜치: main
```

---

## 3. 프로젝트 구조

```
competitor-monitor/
├── .gitlab-ci.yml          ← 매주 월요일 09:00 KST 자동 실행
├── .env.example
├── requirements.txt        ← playwright==1.44.0, python-dotenv==1.0.1
├── crawler/
│   ├── main.py             ← 진입점 (4개 사이트 순차 실행)
│   ├── base.py             ← 공통 크롤러 (스크린샷·이미지·텍스트 추출)
│   └── sites/
│       ├── coupang.py      ← https://www.coupang.com/np/campaigns/
│       ├── kurly.py        ← https://event.kurly.com/lego/event/... (URL 매주 변경 필요)
│       ├── ssg.py          ← https://www.ssg.com/event/eventMain.ssg
│       └── naver_kurly.py  ← https://shopping.naver.com/kurlynmart/home
└── data/
    └── 2026-06-01.json     ← 수집 결과 (Artifacts로 저장됨)
```

---

## 4. 수집 데이터 스키마

각 사이트별로 아래 필드를 수집해요.

```json
{
  "site": "coupang",
  "site_name": "쿠팡",
  "crawled_at": "2026-06-01",
  "url": "크롤링한 페이지 URL",
  "screenshot": "KV 영역 스크린샷 경로 (Artifacts)",
  "full_screenshot": "전체 페이지 스크린샷 경로 (Artifacts)",
  "page_images": ["이미지 URL 목록"],
  "page_text": "페이지 텍스트 (최대 3000자)"
}
```

> **미완성 필드**: `kv_description`, `corner_structure`, `target_categories`,
> `main_benefits`, `coupon_scheme`, `features`, `utilization_points`
> → 원래 Claude API로 자동 생성 예정이었으나 비용 문제로 보류.
> **코워크에서 GitLab MCP로 JSON 읽어와서 Claude가 직접 분석하는 방식으로 대체 가능.**

---

## 5. 현재 상태 (PoC 1 완료 기준)

| 항목 | 상태 | 비고 |
|------|------|------|
| 4개 사이트 Playwright 크롤링 | ✅ 작동 | 매주 자동 실행 |
| GitLab CI 스케줄 (매주 월 09:00) | ✅ 설정 완료 | |
| JSON 결과 저장 | ✅ Artifacts 저장 | 8주 보관 |
| 레포 자동 커밋 | ❌ 회사 정책 차단 | git push, API commit 모두 403 |
| AI 분석 (특징·활용방안) | ⏸ 보류 | 코워크에서 처리 예정 |

---

## 6. 코워크에서 할 일

### 단기 (지금 당장)
- [ ] **GitLab MCP로 Artifacts JSON 읽기 연결** — 코워크에 GitLab MCP가 연결되어 있으니,
  매주 파이프라인 실행 후 JSON을 MCP로 직접 읽어서 Claude가 분석 가능한지 확인
- [ ] **분석 자동화** — JSON 읽기 → KV/코너/혜택/특징 분석 → 결과 Confluence 또는 슬랙 전송

### 중기 (PoC 2)
- [ ] **HTML 리포트 생성** — 사이트별 탭 + 카드 형식으로 주간 리포트 페이지 제작
- [ ] **컬리 URL 자동 감지** — 컬리 이벤트 URL이 매주 바뀌므로, 목록 페이지에서 최신 URL 자동 추출 로직 추가

---

## 7. 파이프라인 수동 실행 방법

GitLab → Build → Pipelines → **Run pipeline** 버튼 클릭

결과 JSON 다운로드:
GitLab → Build → Pipelines → 해당 파이프라인 클릭 → **Download artifacts**

---

## 8. 로컬 테스트 방법

```bash
cd competitor-monitor
pip install -r requirements.txt
playwright install chromium
python crawler/main.py
# 결과: data/YYYY-MM-DD.json 생성
```
