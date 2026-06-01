"""
경쟁사 프로모션 크롤러 진입점.

실행 방법:
    cd competitor-monitor
    python crawler/main.py

출력:
    data/YYYY-MM-DD.json  — 4개 사이트 수집 결과 JSON
    data/YYYY-MM-DD/<site>/*.png  — 스크린샷 (GitLab Artifacts로 보관)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

from sites.coupang import CoupangCrawler
from sites.kurly import KurlyCrawler
from sites.naver_kurly import NaverKurlyCrawler
from sites.ssg import SSGCrawler

CRAWLERS = [
    CoupangCrawler,
    KurlyCrawler,
    SSGCrawler,
    NaverKurlyCrawler,
]


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
        )

        for CrawlerClass in CRAWLERS:
            crawler = CrawlerClass()
            print(f"[{crawler.site_name}] 크롤링 시작...")
            page = context.new_page()
            try:
                result = crawler.crawl(page)
                all_results[crawler.site_key] = result
                print(f"[{crawler.site_name}] 완료 ✓")
            except Exception as e:
                print(f"[{crawler.site_name}] 오류: {e}")
                all_results[crawler.site_key] = {
                    "site": crawler.site_key,
                    "site_name": crawler.site_name,
                    "crawled_at": today,
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
