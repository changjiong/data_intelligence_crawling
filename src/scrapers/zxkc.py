from __future__ import annotations

import logging
import mimetypes
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from storage.models import Attachment, Policy

logger = logging.getLogger(__name__)

BASE_URL = "http://www.zxkc.org.cn"
CATEGORY_ID = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
    "DNT": "1",
}
ATTACHMENT_PATTERN = re.compile(r"\.(pdf|docx?|wps|jpe?g|png|gif|bmp)$", re.IGNORECASE)


@dataclass
class ListItem:
    article_id: str
    title: str
    url: str
    publish_date: Optional[date]


class ZxkcPoliciesClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, headers=HEADERS, timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "ZxkcPoliciesClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(), reraise=True)
    def _get(self, url: str) -> httpx.Response:
        logger.debug("GET %s", url)
        response = self.client.get(url)
        response.raise_for_status()
        return response

    def fetch_list_page(self, page: int = 1) -> str:
        url = f"/index.php?c=category&id={CATEGORY_ID}&page={page}"
        return self._get(url).text

    def fetch_detail_page(self, url: str) -> str:
        return self._get(url).text

    def crawl(
        self,
        since: Optional[date] = None,
        max_pages: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Iterable[Policy]:
        collected = 0
        page = 1
        stop = False
        while True:
            if max_pages and page > max_pages:
                break
            html = self.fetch_list_page(page)
            items = self.parse_list(html)
            if not items:
                break
            for item in items:
                if since and item.publish_date and item.publish_date < since:
                    stop = True
                    continue
                detail_html = self.fetch_detail_page(item.url)
                detail = self.parse_detail(detail_html, fallback_title=item.title, fallback_date=item.publish_date, url=item.url)
                policy = Policy(
                    id=f"zxkc-{item.article_id}",
                    title=detail["title"],
                    publish_date=detail["publish_date"],
                    region_level=self.infer_region_level(detail["title"]),
                    site="zxkc",
                    source_url=item.url,
                    content_html=detail["content_html"],
                    content_text=detail["content_text"],
                    attachments=detail["attachments"],
                )
                collected += 1
                yield policy
                if limit and collected >= limit:
                    return
            if stop:
                break
            page += 1

    def parse_list(self, html: str) -> List[ListItem]:
        soup = BeautifulSoup(html, "lxml")
        links = soup.select("div.lsrw a.newa")
        items: List[ListItem] = []
        for link in links:
            href = link.get("href")
            if not href:
                continue
            absolute_url = urljoin(self.base_url, href)
            qs = parse_qs(urlparse(absolute_url).query)
            article_id = qs.get("id", [""])[0]
            title = link.get_text(strip=True)
            date_text = None
            date_span = link.find("span")
            if date_span:
                date_text = date_span.get_text(strip=True)
            publish_date = self._parse_date(date_text)
            items.append(ListItem(article_id=article_id, title=title, url=absolute_url, publish_date=publish_date))
        return items

    def parse_detail(self, html: str, fallback_title: str, fallback_date: Optional[date], url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        title_node = soup.select_one("div.xw_xq div.b_t")
        title = title_node.get_text(strip=True) if title_node else fallback_title
        meta_node = soup.select_one("div.xw_xq div.z_c")
        publish_date = fallback_date
        if meta_node:
            for span in meta_node.select("span"):
                text = span.get_text(strip=True)
                if text.startswith("时间："):
                    publish_date = self._parse_date(text.split("时间：")[-1].strip()) or publish_date
                    break
        article_node = soup.select_one("div.article_con") or soup.select_one("div.n_r")
        content_html = str(article_node) if article_node else ""
        content_text = article_node.get_text("\n", strip=True) if article_node else ""
        attachments = self._extract_attachments(article_node, url)
        if not content_text and any(self._is_image_attachment(att) for att in attachments):
            content_text = "正文以图片形式呈现，详情见附件中的图片文件。"
        return {
            "title": title,
            "publish_date": publish_date,
            "content_html": content_html,
            "content_text": content_text,
            "attachments": attachments,
        }

    def _extract_attachments(self, container, page_url: str) -> List[Attachment]:
        attachments: List[Attachment] = []
        if not container:
            return attachments
        for link in container.select("a[href]"):
            href = link.get("href")
            if not href:
                continue
            if not ATTACHMENT_PATTERN.search(href):
                continue
            absolute_url = urljoin(page_url, href)
            name = link.get_text(strip=True) or Path(urlparse(absolute_url).path).name
            attachments.append(Attachment(name=name, url=absolute_url))
        for img in container.select("img[src]"):
            src = img.get("src")
            if not src:
                continue
            absolute_url = urljoin(page_url, src)
            name = img.get("alt") or Path(urlparse(absolute_url).path).name or "image_from_article"
            attachments.append(Attachment(name=name, url=absolute_url))
        return attachments

    def download_attachment(self, attachment: Attachment, download_dir: Path) -> Attachment:
        download_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(urlparse(attachment.url).path).name or f"{attachment.name}.bin"
        target = download_dir / filename
        if target.exists():
            logger.debug("Attachment already exists, skipping download: %s", target)
            attachment.mime_type = attachment.mime_type or mimetypes.guess_type(target.name)[0]
        else:
            with self.client.stream("GET", attachment.url) as response:
                response.raise_for_status()
                with target.open("wb") as fh:
                    for chunk in response.iter_bytes():
                        fh.write(chunk)
                attachment.mime_type = response.headers.get("content-type")
        attachment.local_path = str(target)
        return attachment

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def infer_region_level(title: str) -> str:
        municipal_keywords = ["北京市", "上海市", "天津市", "重庆市", "广州市", "深圳市", "杭州市", "南京市", "武汉市", "成都市"]
        provincial_markers = ["省", "自治区", "兵团"]
        if any(keyword in title for keyword in municipal_keywords):
            return "municipal"
        if any(marker in title for marker in provincial_markers):
            return "provincial"
        return "national"

    @staticmethod
    def _is_image_attachment(attachment: Attachment) -> bool:
        return bool(re.search(r"\.(jpe?g|png|gif|bmp)$", attachment.url, re.IGNORECASE))
