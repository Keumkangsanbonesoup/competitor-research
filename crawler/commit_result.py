"""
GitLab API로 수집 결과 JSON을 'data' 브랜치에 커밋.
shell에서 base64를 인수로 넘기면 ARG_MAX 초과 → Python으로 처리.

사용:
    python crawler/commit_result.py data/2026-06-01.json
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request


def commit_file(file_path: str):
    server_url = os.environ.get("CI_SERVER_URL", "")
    project_id = os.environ.get("CI_PROJECT_ID", "")
    token      = os.environ.get("CI_PUSH_TOKEN", "")
    branch     = "data"

    if not all([server_url, project_id, token]):
        print("⚠️  CI 환경변수 미설정 — 커밋 건너뜀")
        return

    with open(file_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    today = os.path.splitext(os.path.basename(file_path))[0]  # 2026-06-01
    api_url = f"{server_url}/api/v4/projects/{project_id}/repository/commits"
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
    }

    for action in ("create", "update"):
        payload = json.dumps({
            "branch": branch,
            "commit_message": f"chore: weekly competitor data {today}",
            "actions": [{
                "action": action,
                "file_path": file_path,
                "content": content_b64,
                "encoding": "base64",
            }],
        }).encode()

        req = urllib.request.Request(api_url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                print(f"✅ data 브랜치 커밋 성공 ({action}): {file_path}")
                return
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            print(f"  {action} 실패 ({e.code}): {body[:200]}")

    print("⚠️  커밋 실패 — Artifacts에서 수동 다운로드 필요")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python commit_result.py <json_file_path>")
        sys.exit(1)
    commit_file(sys.argv[1])
