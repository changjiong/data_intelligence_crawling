#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from rich import print

from scrapers import policies_npc


def parse_date(value: Optional[str]):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def run_pipeline(args) -> None:
    tasks = [
        {"name": "policies_npc", "runner": lambda: policies_npc.run(since=parse_date(args.policies_since), skip_google_docs=args.policies_skip_google, dry_run=False)},
        {"name": "finreg", "runner": None},
        {"name": "bank_tech_finance", "runner": None},
        {"name": "peer_products", "runner": None},
        {"name": "investment_itjuzi", "runner": None},
    ]

    if args.dry_run:
        print("[bold cyan]计划任务：[/]")
        for task in tasks:
            status = "✅ ready" if task["runner"] else "⏳ TODO"
            print(f" - {task['name']} [{status}]")
        return

    for task in tasks:
        if not task["runner"]:
            print(f"[yellow]跳过 {task['name']}：尚未实现[/]")
            continue
        print(f"[bold green]执行 {task['name']}[/]")
        task["runner"]()


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Data Intelligence pipeline executor")
    parser.add_argument("--dry-run", action="store_true", help="仅查看任务，不执行")
    parser.add_argument("--policies-since", help="policies_npc 任务的最早日期，格式 YYYY-MM-DD")
    parser.add_argument("--policies-skip-google", action="store_true", help="跳过 Google Docs 导出")
    args = parser.parse_args()
    try:
        run_pipeline(args)
    except Exception as exc:
        print(f"[red]Pipeline 失败：{exc}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
