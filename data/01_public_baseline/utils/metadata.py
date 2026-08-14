from __future__ import annotations

import json
import re
from bs4 import BeautifulSoup

DATE_RE = re.compile(r"(?<!\d)(20\d{2})[年./-](0?[1-9]|1[0-2])[月./-](0?[1-9]|[12]\d|3[01])日?")

def extract_metadata(soup: BeautifulSoup) -> dict:
    title = ""
    for selector in ('meta[property="og:title"]', 'meta[name="ArticleTitle"]'):
        tag = soup.select_one(selector)
        if tag and tag.get("content"): title = tag["content"].strip(); break
    if not title and soup.find("h1"): title = soup.find("h1").get_text(" ", strip=True)
    if not title and soup.title: title = soup.title.get_text(" ", strip=True)
    published = updated = ""
    meta_names = {"article:published_time": "published", "pubdate": "published", "publishdate": "published", "article:modified_time": "updated", "last-modified": "updated"}
    for tag in soup.find_all("meta"):
        key = (tag.get("property") or tag.get("name") or "").lower()
        content = (tag.get("content") or "").strip()
        if key in meta_names and content:
            m = DATE_RE.search(content)
            value = f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
            if meta_names[key] == "published": published = value
            else: updated = value
    if not published:
        head_text = soup.get_text(" ", strip=True)[:1500]
        labels = re.search(r"(?:发布时间|发布日期|发布于|时间)\s*[：:]?\s*" + DATE_RE.pattern, head_text)
        if labels:
            nums = re.findall(r"\d+", labels.group(0))[-3:]
            published = f"{int(nums[0]):04d}-{int(nums[1]):02d}-{int(nums[2]):02d}"
    department = ""
    for key in ("author", "source", "department"):
        tag = soup.find("meta", attrs={"name": re.compile(f"^{key}$", re.I)})
        if tag and tag.get("content") and 2 <= len(tag["content"].strip()) <= 50:
            department = tag["content"].strip(); break
    return {"title": title[:300], "published_at": published, "updated_at": updated, "department": department}

def category_hint(text: str) -> str:
    groups = {"新生入校": "新生|报到|入学|迎新", "校园办事": "校园卡|网络|证明|学籍|注册|选课|办事|服务指南|FAQ", "校园生活": "食堂|宿舍|校医院|体育馆|校车|地图|后勤", "规章制度": "规定|办法|制度|条例", "校园通知": "通知|公告|开放时间|营业时间|服务调整"}
    scores = {name: len(re.findall(pattern, text, re.I)) for name, pattern in groups.items()}
    name, score = max(scores.items(), key=lambda x: x[1])
    return name if score else "校园相关"
