from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

from dotenv import load_dotenv

from services.google_docs import GoogleDocsExporter
from storage.policies_repository import PolicyRepository
from scrapers.zxkc import ZxkcPoliciesClient

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl ZXKC policies and export to Google Docs.")
    parser.add_argument("--since", type=_parse_date, help="仅抓取该日期（含）之后的政策，格式 YYYY-MM-DD")
    parser.add_argument("--max-pages", type=int, default=None, help="最多抓取前 N 页")
    parser.add_argument("--limit", type=int, default=None, help="限制抓取记录数量")
    parser.add_argument("--download-dir", default="data/policies_npc/attachments", help="附件保存目录")
    parser.add_argument("--skip-google-docs", action="store_true", help="跳过 Google Docs 导出")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将要处理的记录，不落地数据")
    parser.add_argument("--log-level", default="INFO", help="日志级别，例如 INFO/DEBUG")
    return parser.parse_args()


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def run(
    since: Optional[date] = None,
    max_pages: Optional[int] = None,
    limit: Optional[int] = None,
    download_dir: str | Path = "data/policies_npc/attachments",
    skip_google_docs: bool = False,
    dry_run: bool = False,
    exporter: GoogleDocsExporter | None = None,
) -> None:
    load_dotenv()
    repo = PolicyRepository()
    existing_index = repo.load_index()
    attachments_dir = Path(download_dir)
    attachments_dir.mkdir(parents=True, exist_ok=True)

    docs_exporter = exporter
    if not docs_exporter and not skip_google_docs and not dry_run:
        docs_exporter = GoogleDocsExporter()

    new_policies = []
    discovered = 0

    with ZxkcPoliciesClient() as client:
        for policy in client.crawl(since=since, max_pages=max_pages, limit=limit):
            key = _policy_key(policy.title, policy.publish_date, policy.site)
            if key in existing_index:
                logger.debug("Skip existing policy: %s", policy.title)
                continue
            discovered += 1
            if dry_run:
                logger.info("[DRY RUN] %s %s -> %s", policy.publish_date, policy.title, policy.source_url)
                continue
            downloaded = [client.download_attachment(att, attachments_dir) for att in policy.attachments]
            policy.attachments = downloaded
            if docs_exporter:
                docs_exporter.export(policy)
            new_policies.append(policy)
            existing_index[key] = policy

    if dry_run:
        logger.info("Dry run完成，发现 %d 条潜在新政策。", discovered)
        return

    if new_policies:
        repo.upsert_many(new_policies)
        logger.info("入库 %d 条新政策。", len(new_policies))
    else:
        logger.info("没有发现新的政策记录。")


def _policy_key(title: str, publish_date: Optional[date], site: Optional[str]) -> Tuple[str, Optional[str], Optional[str]]:
    return title.strip(), publish_date.isoformat() if publish_date else None, site or "zxkc"


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(
        since=args.since,
        max_pages=args.max_pages,
        limit=args.limit,
        download_dir=args.download_dir,
        skip_google_docs=args.skip_google_docs,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
