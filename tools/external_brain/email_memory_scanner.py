#!/usr/bin/env python3
"""
Email Memory Scanner — B 外部记忆大脑

定期扫描邮箱，提取有意义的内容写入 MindKernel。

过滤策略（不保留）：
- 营销邮件（LinkedIn营销、Steam促销 newsletters）
- 系统通知类（Cloudflare激活邮件等）
- 纯系统消息（无实际内容）

保留策略：
- 真实联系人发来的、有内容深度的邮件
- 包含决策、计划、反馈的邮件

Usage:
  python tools/external_brain/email_memory_scanner.py --account longwind --days 3 --dry
  python tools/external_brain/email_memory_scanner.py --account gmail --days 7
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

API_BASE = "http://localhost:18793"
API_KEY = "mk_IsQ2BrHQCmKx6vqDU0wv5JceElh4hjE7zjQks2YdxTM"

# 黑名单：不过滤完整内容但降低优先级
MARKETING_SENDERS = [
    "linkedin.com",
    "steamcommunity.com",
    "steampowered.com",
    "amazon.com",
    "newsletter",
    "no-reply",
    "noreply@",
    "notifications@",
    "cloudflare.discoursemail.com",
    "dreamstime.com",
]

# 高价值关键词：邮件含这些提升保留优先级
HIGH_VALUE_KEYWORDS = [
    "决策", "计划", "安排", "反馈",
    "meeting", "schedule", "review",
    "proposal", "contract", "agreement",
    "报告", "总结", "分析",
]


def api_retain(content: str, source: str, tags: list, event_date: str | None = None) -> dict | None:
    """调用 MindKernel /retain 接口。"""
    import urllib.request

    payload = {
        "content": content,
        "source": source,
        "confidence": 0.75,
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


def list_emails(account: str, days: int = 3, page_size: int = 20) -> list[dict]:
    """通过 himalaya 列出近 N 天的邮件。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    cmd = [
        "himalaya", "envelope", "list",
        "-a", account,
        "--output", "json",
        "--page-size", str(page_size),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  [WARN] himalaya failed: {result.stderr[:200]}")
            return []
    except Exception as e:
        print(f"  [WARN] himalaya exception: {e}")
        return []

    emails = []
    # himalaya outputs one line per page: a JSON array
    try:
        emails = json.loads(result.stdout)
        if not isinstance(emails, list):
            emails = []
    except Exception:
        emails = []

    # Filter to recent emails
    recent = []
    for em in emails:
        date_str = em.get("date", "")
        try:
            # Parse: "2026-05-10 15:20+00:00"
            date_str = date_str.replace("+00:00", "Z").replace(" ", "T")
            if date_str.endswith("Z"):
                email_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                email_date = datetime.fromisoformat(date_str)
            if email_date >= cutoff:
                recent.append(em)
        except Exception:
            recent.append(em)  # Keep if can't parse date

    return recent


def read_email_body(account: str, email_id: str) -> str:
    """读取邮件正文（前2000字符）。"""
    cmd = ["himalaya", "message", "read", "-a", account, email_id]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            return ""
        # Skip headers (up to blank line)
        body = result.stdout
        # Find first blank line (end of headers)
        header_end = body.find("\n\n")
        if header_end >= 0:
            body = body[header_end + 2:]
        return body.strip()[:2000]
    except Exception:
        return ""


def is_marketing_email(email: dict, body: str) -> bool:
    """判断是否为营销/新闻邮件。"""
    sender_addr = email.get("from", {}).get("addr", "")
    subject = email.get("subject", "")

    # Sender 黑名单
    for m in MARKETING_SENDERS:
        if m in sender_addr.lower():
            return True

    # Subject 黑名单关键词
    marketing_subjects = ["特卖", "促销", "discount", "sale", "offer",
                          "新邀请", "成为好友", " appeared in",
                          "激活", "激活账户", "Confirm your"]
    for kw in marketing_subjects:
        if kw in subject:
            return True

    # 无正文
    if len(body.strip()) < 50:
        return True

    return False


def should_retain(email: dict, body: str) -> tuple[bool, list[str], float]:
    """
    判断邮件是否值得保留。返回 (should_retain, tags, confidence)。
    """
    if is_marketing_email(email, body):
        return False, [], 0.0

    subject = email.get("subject", "")
    sender_name = email.get("from", {}).get("name", "")
    sender_addr = email.get("from", {}).get("addr", "")

    tags = ["email", "external"]
    confidence = 0.75

    # 高价值关键词检测
    body_text = body.lower()
    for kw in HIGH_VALUE_KEYWORDS:
        if kw.lower() in subject.lower() or kw.lower() in body_text:
            tags.append("high-value")
            confidence = 0.85
            break

    # 真实人名（非公司）检测
    if sender_name and not any(
        c in sender_name for c in ["LinkedIn", "Steam", "Amazon", "Google", "Microsoft", "通知"]
    ):
        tags.append("personal")
        confidence = max(confidence, 0.80)

    return True, tags, confidence


def scan_account(account: str, days: int, dry_run: bool = True) -> dict:
    """扫描单个账号。返回统计。"""
    print(f"\n[*] Scanning {account}, last {days} days...")

    emails = list_emails(account, days=days)
    print(f"    {len(emails)} recent emails found")

    retained = 0
    skipped = 0

    for em in emails:
        em_id = em.get("id", "")
        subject = em.get("subject", "")
        date = em.get("date", "")[:10]

        body = read_email_body(account, em_id)
        should, tags, conf = should_retain(em, body)

        if not should:
            skipped += 1
            print(f"    [SKIP] {subject[:50]}")
            continue

        # 构建记忆内容
        from_addr = em.get("from", {}).get("addr", "")
        from_name = em.get("from", {}).get("name", "")
        sender = from_name or from_addr
        content = f"[邮件] 主题：{subject}\n发件人：{sender}\n日期：{date}\n摘要：{body[:500]}"

        if dry_run:
            print(f"    [DRY] Would retain: {subject[:50]} (conf={conf})")
            retained += 1
            continue

        result = api_retain(content, f"email:{account}:{em_id}", tags, f"{date}T00:00:00Z")
        if result and result.get("ok"):
            retained += 1
            print(f"    [RETAINED] {subject[:50]}")
        else:
            print(f"    [FAIL] {subject[:50]}")

    return {"account": account, "retained": retained, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description="MindKernel Email Memory Scanner")
    parser.add_argument("--account", default="longwind", help="himalaya account name")
    parser.add_argument("--days", type=int, default=3, help="look back days")
    parser.add_argument("--dry", dest="dry_run", action="store_true", help="dry-run (no API write)")
    parser.add_argument("--all", action="store_true", help="scan all accounts")
    args = parser.parse_args()

    print(f"[Email Scanner] Starting... dry={args.dry_run}")

    if args.all:
        # Scan all accounts
        result = subprocess.run(["himalaya", "account", "list"],
                                capture_output=True, text=True, timeout=10)
        accounts = []
        for line in result.stdout.splitlines()[1:]:  # Skip header
            parts = line.strip().split("|")
            if len(parts) >= 1:
                name = parts[0].strip()
                if name:
                    accounts.append(name)
    else:
        accounts = [args.account]

    total_retained = 0
    for acc in accounts:
        r = scan_account(acc, args.days, dry_run=args.dry_run)
        total_retained += r["retained"]

    print(f"\n[Email Scanner] Done. Total retained: {total_retained}")


if __name__ == "__main__":
    main()
