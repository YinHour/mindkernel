#!/usr/bin/env python3
"""
Feishu Document Memory Scanner — B 外部记忆大脑

扫描飞书云文档，提取有意义的文档内容写入 MindKernel。

功能：
- 搜索用户可访问的云文档
- 获取文档摘要/内容
- 过滤低价值文档（空文档、模板、系统文档）
- 调用 MindKernel /retain API

Usage:
  python tools/external_brain/feishu_doc_scanner.py --days 30 --dry
  python tools/external_brain/feishu_doc_scanner.py --days 7
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
API_BASE = "http://localhost:18793"
API_KEY = "mk_IsQ2BrHQCmKx6vqDU0wv5JceElh4hjE7zjQks2YdxTM"

# 低价值文档类型/名称黑名单
SKIP_TYPES = ["TEMPLATE", "EMPTY"]
SKIP_KEYWORDS = [
    "模板", "template", "空白", "未命名",
    "系统文档", "默认", "草稿",
]


def api_retain(content: str, source: str, tags: list, event_date: str | None = None) -> dict | None:
    """调用 MindKernel /retain 接口。"""
    import urllib.request

    payload = {
        "content": content,
        "source": source,
        "confidence": 0.80,
        "tags": tags,
    }
    if event_date:
        payload["event_date"] = event_date

    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/retain",
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "X-MindKernel-Key": API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  [WARN] retain failed: {e}")
        return None


def run_lark_cli(args: list) -> dict:
    """执行 lark-cli 命令，返回 JSON 结果。"""
    cmd = ["lark-cli"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  [WARN] lark-cli failed: {result.stderr[:200]}")
            return {}
        return json.loads(result.stdout)
    except Exception as e:
        print(f"  [WARN] lark-cli exception: {e}")
        return {}


def search_docs(query: str = "", page_size: int = 10) -> list[dict]:
    """搜索飞书文档。"""
    result = run_lark_cli([
        "docs", "+search",
        "--as", "user",
        "--query", query,
        "--page-size", str(page_size),
        "--format", "json",
    ])
    if not result.get("ok"):
        return []
    return result.get("data", {}).get("results", [])


def get_doc_title(meta: dict) -> str:
    """从搜索结果获取文档标题。"""
    title = meta.get("title_highlighted", "")
    if not title:
        result_data = meta.get("result_meta", {})
        title = result_data.get("title", "")
    return title.strip()


def get_doc_token(meta: dict) -> str:
    """从搜索结果获取文档 token。"""
    result_meta = meta.get("result_meta", {})
    url = result_meta.get("url", "")
    # https://tcngiwe8dudk.feishu.cn/base/W6ywb9P5faxAvesKr4FcnRsfnbe
    # or /docx/doxcn...
    if "/base/" in url:
        return url.split("/base/")[-1].split("?")[0]
    elif "/docx/" in url:
        return url.split("/docx/")[-1].split("?")[0]
    return ""


def get_doc_type(meta: dict) -> str:
    """从搜索结果获取文档类型。"""
    result_meta = meta.get("result_meta", {})
    return result_meta.get("doc_types", "UNKNOWN")


def fetch_doc_content(token: str, doc_type: str) -> str:
    """获取文档内容摘要。"""
    try:
        if doc_type == "DOCX":
            result = run_lark_cli([
                "docs", "+fetch",
                "--as", "user",
                "--format", "json",
                "--doc", token,
            ])
            if not result.get("ok"):
                return ""
            data = result.get("data", {})
            # DOCX content is in markdown field
            doc_content = data.get("markdown") or data.get("content") or ""
            return doc_content[:1000] if doc_content else ""
        elif doc_type == "BITABLE":
            return "[BITABLE文档，lark-cli暂不支持]"
        elif doc_type == "WIKI":
            return "[WIKI文档，需单独处理]"
        elif doc_type == "FILE":
            return "[文件类型，无法提取文本]"
        else:
            return ""
    except Exception as e:
        return ""


def should_skip_doc(title: str, doc_type: str, content: str) -> tuple[bool, str]:
    """
    判断文档是否应跳过。
    返回 (skip, reason)。
    """
    # Type skip
    for t in SKIP_TYPES:
        if t in doc_type.upper():
            return True, f"type={doc_type}"

    # Keyword skip
    lower_title = title.lower()
    for kw in SKIP_KEYWORDS:
        if kw.lower() in lower_title:
            return True, f"keyword={kw}"

    # Placeholder content
    if content.strip().startswith("[") and content.strip().endswith("]"):
        return True, f"placeholder={content.strip()[:30]}"

    # Empty content
    if len(content.strip()) < 20:
        return True, "empty"

    return False, ""


def scan_feishu_docs(days: int = 30, dry_run: bool = True) -> dict:
    """主扫描逻辑。返回统计。"""
    print(f"[*] Scanning Feishu docs updated in last {days} days...")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_ts = cutoff.timestamp()

    results = search_docs(page_size=20)
    print(f"    Found {len(results)} documents")

    retained = 0
    skipped = 0

    for item in results:
        meta = item.get("result_meta", {})
        update_ts = meta.get("update_time", 0)
        update_iso = meta.get("update_time_iso", "")

        # Filter by date
        if update_ts and update_ts < cutoff_ts:
            continue

        title = get_doc_title(item)
        token = get_doc_token(item)
        doc_type = get_doc_type(item)

        if not token or not title:
            skipped += 1
            continue

        # Skip tokens that are too short (Feishu DOCX tokens are 32 chars)
        if len(token) < 25:
            skipped += 1
            print(f"    [SKIP] {title[:50]} (token too short: {len(token)})")
            continue

        # Get content
        content = fetch_doc_content(token, doc_type)
        skip, reason = should_skip_doc(title, doc_type, content)

        if skip:
            skipped += 1
            print(f"    [SKIP] {title[:50]} ({reason})")
            continue

        # Build memory content
        owner = meta.get("owner_name", "未知")
        update_date = update_iso[:10] if update_iso else ""
        create_date = meta.get("create_time_iso", "")[:10]

        memory_content = (
            f"[飞书文档] {title}\n"
            f"类型：{doc_type}\n"
            f"创建：{create_date} | 更新：{update_date}\n"
            f"负责人：{owner}\n"
            f"链接：{meta.get('url', '')}\n"
            f"内容摘要：{content[:800]}"
        )

        tags = ["feishu", "document", f"type:{doc_type.lower()}"]

        if dry_run:
            print(f"    [DRY] Would retain: {title[:50]}")
            retained += 1
            continue

        result = api_retain(
            memory_content,
            f"feishu:doc:{token}",
            tags,
            f"{update_date}T00:00:00Z" if update_date else None,
        )
        if result and result.get("ok"):
            retained += 1
            print(f"    [RETAINED] {title[:50]}")
        else:
            print(f"    [FAIL] {title[:50]}")

    return {"retained": retained, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description="MindKernel Feishu Doc Memory Scanner")
    parser.add_argument("--days", type=int, default=30, help="look back days")
    parser.add_argument("--dry", dest="dry_run", action="store_true", help="dry-run (no API write)")
    args = parser.parse_args()

    print(f"[Feishu Scanner] Starting... dry={args.dry_run}")

    r = scan_feishu_docs(days=args.days, dry_run=args.dry_run)
    print(f"\n[Feishu Scanner] Done. retained={r['retained']}, skipped={r['skipped']}")


if __name__ == "__main__":
    main()
