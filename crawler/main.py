"""
경쟁사 프로모션 크롤러 진입점.

각 사이트의 이벤트 목록 → 개별 프로모션 상세 페이지를 순회해
사이트별 promotions 배열로 저장합니다.

실행:
    cd competitor-monitor
    python crawler/main.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

sys.path.insert(0, str(Path(__file__).parent))

from sites.coupang import CoupangCrawler
from sites.kurly import KurlyCrawler
from sites.naver_kurly import NaverKurlyCrawler
from sites.ssg import SSGCrawler

CRAWLERS = [CoupangCrawler, KurlyCrawler, SSGCrawler, NaverKurlyCrawler]


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = Path("data") / f"{today}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_results = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            # 실제 사용자처럼 보이게: HTTP 헤더 추가
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            },
        )

        for CrawlerClass in CRAWLERS:
            crawler = CrawlerClass()
            print(f"\n[{crawler.site_name}] 시작...")
            page = context.new_page()
            try:
                # 봇 감지 우회: stealth 적용
                stealth_sync(page)
                result = crawler.crawl(page)
                all_results[crawler.site_key] = result
                count = len(result.get("promotions", []))
                print(f"[{crawler.site_name}] 완료 ✓ ({count}개 프로모션 수집)")
            except Exception as e:
                print(f"[{crawler.site_name}] 오류: {e}")
                all_results[crawler.site_key] = {
                    "site": crawler.site_key,
                    "site_name": crawler.site_name,
                    "crawled_at": today,
                    "promotions": [],
                    "error": str(e),
                }
            finally:
                page.close()

        browser.close()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 저장 완료: {output_path}")


if __name__ == "__main__":
    main()
