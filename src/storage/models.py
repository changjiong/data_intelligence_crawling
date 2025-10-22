from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    name: str
    url: str
    local_path: Optional[str] = None
    mime_type: Optional[str] = None
    drive_file_id: Optional[str] = None
    drive_view_url: Optional[str] = None
    drive_download_url: Optional[str] = None


class Policy(BaseModel):
    id: str
    title: str
    region_level: Optional[str] = None
    publish_date: Optional[date] = None
    site: Optional[str] = None
    source_url: str
    content_html: Optional[str] = None
    content_text: Optional[str] = None
    keywords: Optional[List[str]] = None
    attachments: List[Attachment] = Field(default_factory=list)
    google_doc_id: Optional[str] = None
    google_doc_url: Optional[str] = None


class BankMetric(BaseModel):
    bank: str
    metric: str
    year: int
    value: float
    unit: str
    evidence_url: str
    snippet: Optional[str] = None

class Product(BaseModel):
    org: str
    product_name: str
    category: Optional[str] = None
    rate_range: Optional[str] = None
    limit_range: Optional[str] = None
    term_range: Optional[str] = None
    apply_link: Optional[str] = None
    source_url: Optional[str] = None
