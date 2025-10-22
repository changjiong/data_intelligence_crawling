from datetime import date
from pathlib import Path

import pytest

from scrapers import policies_npc
from storage.models import Attachment, Policy


class DummyRepo:
    def __init__(self):
        self.saved = []
        self.index = {}

    def load_index(self):
        return dict(self.index)

    def upsert_many(self, policies):
        self.saved.extend(policies)
        return {}


class DummyClient:
    def __init__(self, policies):
        self.policies = policies
        self.downloaded = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def crawl(self, **kwargs):
        yield from self.policies

    def download_attachment(self, attachment, download_dir):
        path = Path(download_dir) / attachment.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"data")
        attachment.local_path = str(path)
        self.downloaded.append(attachment)
        return attachment


class DummyExporter:
    def __init__(self):
        self.calls = []

    def export(self, policy):
        self.calls.append(policy)


@pytest.fixture
def sample_policy():
    return Policy(
        id="zxkc-2703",
        title="金融监管总局关于废止部分规章的决定",
        publish_date=date(2025, 8, 11),
        region_level="national",
        site="zxkc",
        source_url="http://www.zxkc.org.cn/index.php?c=show&id=2703",
        content_html="<p>content</p>",
        content_text="content",
        attachments=[Attachment(name="decision.pdf", url="https://example.com/decision.pdf")],
    )


def test_run_dry_run_skips_side_effects(monkeypatch, tmp_path, sample_policy):
    repo = DummyRepo()
    client = DummyClient([sample_policy])
    monkeypatch.setattr(policies_npc, "PolicyRepository", lambda: repo)
    monkeypatch.setattr(policies_npc, "ZxkcPoliciesClient", lambda: client)

    policies_npc.run(dry_run=True, skip_google_docs=True, download_dir=tmp_path)

    assert repo.saved == []
    assert not client.downloaded


def test_run_persists_and_exports(monkeypatch, tmp_path, sample_policy):
    repo = DummyRepo()
    client = DummyClient([sample_policy])
    exporter = DummyExporter()
    monkeypatch.setattr(policies_npc, "PolicyRepository", lambda: repo)
    monkeypatch.setattr(policies_npc, "ZxkcPoliciesClient", lambda: client)

    policies_npc.run(dry_run=False, skip_google_docs=False, download_dir=tmp_path, exporter=exporter)

    assert repo.saved, "Policy should be persisted"
    assert exporter.calls, "Exporter should be invoked"
    assert Path(repo.saved[0].attachments[0].local_path).exists()
