import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

headers = {"User-Agent": "Mozilla/5.0 (compatible; OpenSpecBot/0.1)"}

@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter())
def fetch(url: str) -> str:
    with httpx.Client(timeout=20) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        return r.text

def parse_list(html: str):
    soup = BeautifulSoup(html, "lxml")
    # TODO: 解析页面结构，返回 item 列表
    return []

def parse_detail(html: str):
    soup = BeautifulSoup(html, "lxml")
    # TODO: 提取标题/时间/正文
    return {"title":"", "publish_date":None, "content_html":""}
