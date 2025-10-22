from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class Policy(BaseModel):
    id: str
    title: str
    region_level: Optional[str] = None
    publish_date: Optional[date] = None
    site: Optional[str] = None
    source_url: str
    content_html: Optional[str] = None
    keywords: Optional[List[str]] = None

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
