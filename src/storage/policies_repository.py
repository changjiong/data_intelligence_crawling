from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

from .models import Policy


class PolicyRepository:
    """Persist policies to JSONL storage and handle deduplication."""

    def __init__(self, root: str | Path = "data/policies_npc") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.data_path = self.root / "policies.jsonl"

    def _make_key(self, title: str, publish_date: str | None, site: str | None) -> Tuple[str, str | None, str | None]:
        return title.strip(), publish_date, site or "zxkc"

    def load_index(self) -> Dict[Tuple[str, str | None, str | None], Policy]:
        index: Dict[Tuple[str, str | None, str | None], Policy] = {}
        if not self.data_path.exists():
            return index
        with self.data_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                policy = Policy(**data)
                key = self._make_key(policy.title, policy.publish_date.isoformat() if policy.publish_date else None, policy.site)
                index[key] = policy
        return index

    def upsert_many(self, policies: Iterable[Policy]) -> Dict[Tuple[str, str | None, str | None], Policy]:
        index = self.load_index()
        for policy in policies:
            publish_date = policy.publish_date.isoformat() if policy.publish_date else None
            key = self._make_key(policy.title, publish_date, policy.site)
            index[key] = policy
        self._write(index)
        return index

    def contains(self, title: str, publish_date: str | None, site: str | None = None) -> bool:
        key = self._make_key(title, publish_date, site)
        return key in self.load_index()

    def _write(self, index: Dict[Tuple[str, str | None, str | None], Policy]) -> None:
        with self.data_path.open("w", encoding="utf-8") as fh:
            for policy in index.values():
                fh.write(policy.model_dump_json())
                fh.write("\n")
