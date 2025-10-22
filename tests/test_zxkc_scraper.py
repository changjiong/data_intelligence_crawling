from datetime import date
from pathlib import Path

import httpx

from scrapers.zxkc import ZxkcPoliciesClient


def fixture_path(name: str) -> Path:
    return Path("tests/fixtures/policies_npc") / name


def read_fixture(name: str) -> str:
    return fixture_path(name).read_text(encoding="utf-8")


def test_parse_list_extracts_articles():
    client = ZxkcPoliciesClient()
    html = read_fixture("list_page.html")
    items = client.parse_list(html)
    client.close()

    assert len(items) == 2
    assert items[0].article_id == "2703"
    assert items[0].publish_date.isoformat() == "2025-08-11"
    assert items[0].title.startswith("金融监管总局")


def test_parse_detail_returns_content_and_attachments():
    client = ZxkcPoliciesClient()
    html = read_fixture("detail_page.html")
    detail = client.parse_detail(html, fallback_title="fallback", fallback_date=date(2025, 8, 11), url="http://www.zxkc.org.cn/index.php?c=show&id=2703")
    client.close()

    assert detail["title"] == "金融监管总局关于废止部分规章的决定"
    assert "国家金融监督管理总局" in detail["content_text"]
    attachments = detail["attachments"]
    assert len(attachments) == 2
    urls = {att.url for att in attachments}
    assert "https://www.example.com/decision.pdf" in urls
    assert "http://www.zxkc.org.cn/static/images/policy-image.jpg" in urls


def test_download_attachment_uses_local_cache(tmp_path):
    client = ZxkcPoliciesClient()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"PDFDATA", headers={"content-type": "application/pdf"}))
    headers = dict(client.client.headers)
    timeout = client.client.timeout
    client.client.close()
    client.client = httpx.Client(transport=transport, headers=headers, base_url=client.base_url, timeout=timeout)  # type: ignore[arg-type]
    from storage.models import Attachment as PolicyAttachment  # local import to avoid circular during test

    attachment = PolicyAttachment(name="decision.pdf", url="https://example.com/decision.pdf")
    downloaded = client.download_attachment(attachment, tmp_path)
    client.close()

    assert Path(downloaded.local_path).exists()
    assert Path(downloaded.local_path).read_bytes() == b"PDFDATA"
