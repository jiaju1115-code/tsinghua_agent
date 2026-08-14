from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag
import trafilatura
from markdownify import markdownify

from utils.url_utils import ATTACHMENT_EXTENSIONS, extension, normalize_url


AUTH_PATTERNS = re.compile(r"统一身份认证|账号密码|验证码|access denied|\bCAS\b|\bSSO\b|oauth|请登录|用户登录", re.I)
SOFT_404 = re.compile(r"页面不存在|内容已删除|您访问的页面不存在|404\s*(?:not found)?", re.I)
PRIVATE = re.compile(r"个人成绩|个人课表|个人借阅记录|个人财务|身份证号码|个人档案|私人申请状态|个人住宿信息|个人医疗记录|账号凭证", re.I)
LOAD_PLACEHOLDER = re.compile(r"读取内容中|请等待|(?:正在|数据)?加载中|\bloading\b", re.I)
LIST_MARKERS = re.compile(r"(?:首页|上页|下页|尾页).*第\s*/?\s*\d+\s*页|共\s*\d+\s*条", re.I)
LIST_TITLE = re.compile(r"(?:通知公告|新闻动态|动态新闻|招聘信息|政策文件|法律法规|规章制度|服务通知|站点地图|热门排序|默认排序|目录|列表)(?:[-—|_].*)?$", re.I)
DETAIL_URL = re.compile(r"/(?:info|article|news|content|detail)/[^?#]*\d+[^/?#]*\.(?:htm|html)$", re.I)
REMOVE = "script,style,noscript,nav,footer,header,aside,form,.nav,.navbar,.footer,.header,.sidebar,.breadcrumb,.share,.search,.qrcode,.ewm,.print"
NAV_WORDS = {
    "首页", "学校概况", "教育教学", "科学研究", "招生就业", "人才招聘", "合作交流", "校园生活",
    "借阅", "资源", "空间", "学习支持", "科研支持", "概况", "联系我们", "网站地图", "通知公告",
    "上一页", "下一页", "上页", "下页", "尾页", "打印", "关闭", "分享", "友情链接",
}
SITE_SELECTORS = {
    "lib.tsinghua.edu.cn": (
        "#vsb_content .v_news_content", "#vsb_content", ".v_news_content", ".concon .v_news_content",
        "#vsb_content_2", ".m-txt2", ".ar_article", ".n_zhichi", ".libser",
        ".main .content", ".main-content", ".article-content",
    ),
    "www.itc.tsinghua.edu.cn": (
        "#vsb_content .v_news_content", "#vsb_content", ".v_news_content", ".txt .v_news_content",
        ".article-content", ".news_content",
    ),
}
GENERIC_SELECTORS = (
    "article", "main article", "main .content", "[role=main]", ".article-content", ".news_content",
    ".v_news_content", "#vsb_content", ".detail-content", ".detail", "#content", "main",
)


@dataclass
class ContentQuality:
    content_quality_class: str
    passed: bool
    reason: str
    total_text_length: int
    line_count: int
    short_line_ratio: float
    navigation_like_ratio: float
    main_paragraph_count: int
    long_paragraph_count: int
    list_item_count: int
    title_match_ratio: float
    loading_placeholder: bool


@dataclass
class ParsedPage:
    soup: BeautifulSoup
    markdown: str
    plain_text: str
    links: list[tuple[str, str]]
    attachments: list[tuple[str, str, str]]
    images: list[tuple[str, str]]
    extraction_method: str = "extraction_failed"
    selector_used: str = ""
    template_removed: bool = False
    quality: ContentQuality | None = None


def detect_page(html: str, final_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    sample = title + " " + soup.get_text(" ", strip=True)[:3000] + " " + final_url
    if AUTH_PATTERNS.search(sample) and ("login" in final_url.lower() or len(soup.get_text(strip=True)) < 2500): return "login_required"
    if SOFT_404.search(sample[:1000]): return "soft_404"
    if PRIVATE.search(sample[:1500]): return "private_or_sensitive"
    return None


def _visible(line: str) -> str:
    line = re.sub(r"!\[[^]]*]\([^)]*\)", "", line)
    line = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", line)
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"^[\s#>*:+\-|\d.()（）]+", "", line)
    return re.sub(r"\s+", " ", line).strip()


def _is_nav_line(raw: str, text: str) -> bool:
    if not text: return False
    if text in NAV_WORDS: return True
    if len(text) <= 12 and (raw.lstrip().startswith(("- [", ":   [", "[")) or "](" in raw): return True
    if len(text) <= 8 and not re.search(r"[。！？；：.!?;]|\d{4}|电话|邮箱|时间|地点", text): return True
    return bool(LIST_MARKERS.search(text))


def _title_terms(title: str) -> set[str]:
    title = re.sub(r"[-—|_](?:清华大学.*|Tsinghua.*)$", "", title, flags=re.I)
    return {x for x in re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", title.lower()) if x not in {"清华大学", "图书馆", "信息化技术中心"}}


def content_quality_gate(markdown: str, title: str, url: str, *, selector_used: str = "") -> ContentQuality:
    raw_lines = [x.strip() for x in markdown.splitlines() if x.strip()]
    pairs = [(r, _visible(r)) for r in raw_lines]
    pairs = [(r, t) for r, t in pairs if t]
    lines = [t for _, t in pairs]
    total = sum(len(x) for x in lines)
    count = len(lines)
    short = sum(len(x) <= 12 for x in lines)
    nav = sum(_is_nav_line(r, t) for r, t in pairs)
    main = sum(len(t) >= 40 and bool(re.search(r"[。！？；：.!?;]", t)) and not _is_nav_line(r, t) for r, t in pairs)
    longp = sum(len(t) >= 100 and not _is_nav_line(r, t) for r, t in pairs)
    list_items = sum(r.lstrip().startswith(("- ", "* ", "+ ", ":   ")) for r, _ in pairs)
    plain = " ".join(lines)
    loading = bool(LOAD_PLACEHOLDER.search(plain))
    terms = _title_terms(title)
    matched = sum(term in plain.lower() for term in terms)
    title_match = matched / len(terms) if terms else 1.0
    short_ratio = short / count if count else 0.0
    nav_ratio = nav / count if count else 0.0
    list_page = bool(LIST_MARKERS.search(plain)) or bool(LIST_TITLE.search(title)) or (list_items >= 8 and main <= 1)

    if list_page and not (DETAIL_URL.search(url) and not LIST_TITLE.search(title)):
        cls, passed, reason = "list_page", False, "页面呈现多条索引、分页或目录，不是单一详情正文"
    elif loading and main == 0:
        cls, passed, reason = "extraction_failed", False, "仅发现动态加载占位，缺少真实正文"
    elif nav_ratio >= 0.72 and main == 0:
        cls, passed, reason = "navigation_only", False, "导航样式行占比过高且没有连续正文"
    elif total < 120 and main == 0:
        cls, passed, reason = "extraction_failed", False, "抽取文本过短且没有连续自然语言段落"
    elif DETAIL_URL.search(url) and main == 0 and longp == 0 and title_match < 0.35:
        cls, passed, reason = "extraction_failed", False, "详情页缺少连续正文且标题与内容关联不足"
    elif nav_ratio >= 0.45 and main >= 1:
        cls, passed, reason = "template_polluted", True, "主体存在，但仍混入较多导航/模板"
    elif total < 280 and (main >= 1 or longp >= 1):
        cls, passed, reason = "thin_content", True, "正文较短但包含与页面功能一致的实质信息"
    elif main >= 1 or longp >= 1 or (selector_used and total >= 220 and title_match >= 0.25):
        cls, passed, reason = "detail_content", True, "存在可信正文容器和连续主体内容"
    else:
        cls, passed, reason = "extraction_failed", False, "未达到正文质量闸门"
    return ContentQuality(cls, passed, reason, total, count, short_ratio, nav_ratio, main, longp, list_items, title_match, loading)


def _clean_fragment(node: Tag | BeautifulSoup) -> tuple[BeautifulSoup, bool]:
    fragment = BeautifulSoup(str(node), "lxml")
    removed = False
    for child in list(fragment.select(REMOVE)):
        child.decompose(); removed = True
    for child in list(fragment.select(".relatenews,.related,.recommend,.xgyd,.page,.pages,.pagination,.prev-next,.tools,.source,.views")):
        child.decompose(); removed = True
    for text in list(fragment.find_all(string=re.compile(r"^(?:上一篇|下一篇|打印|关闭|分享|访问量)[：:]?\s*$"))):
        if text.parent: text.parent.decompose(); removed = True
    return fragment, removed


def _candidate(soup: BeautifulSoup, selector: str) -> BeautifulSoup | None:
    node = soup.select_one(selector)
    if not node: return None
    fragment, _ = _clean_fragment(node)
    if len(fragment.get_text(" ", strip=True)) < 30: return None
    return fragment


def _to_markdown(body: BeautifulSoup) -> tuple[str, str]:
    plain = re.sub(r"\s+", " ", body.get_text(" ", strip=True)).strip()
    md = markdownify(str(body), heading_style="ATX", bullets="-").strip()
    md = re.sub(r"[\ue000-\uf8ff]", "", md)
    md = re.sub(r"(?<!\d)(\d{2,}(?:[,.]\d+)?)\1(?!\d)", r"\1", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md, plain


def parse_html(html: str, base_url: str, tracking: set[str]) -> ParsedPage:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else base_url
    links, attachments, images = [], [], []
    for a in soup.find_all("a", href=True):
        u = normalize_url(a["href"], base_url, tracking)
        if not u: continue
        ext = extension(u)
        if ext in ATTACHMENT_EXTENSIONS: attachments.append((a.get_text(" ", strip=True) or u.rsplit("/", 1)[-1], u, ext.lstrip(".")))
        else: links.append((u, a.get_text(" ", strip=True)[:300]))
    for img in soup.find_all("img", src=True):
        alt = img.get("alt", "").strip()
        if re.search(r"流程|地图|步骤|操作|信息图", alt): images.append((alt, urljoin(base_url, img["src"])))

    host = (urlsplit(base_url).hostname or "").lower()
    candidates: list[tuple[str, str, BeautifulSoup, bool]] = []
    for selector in SITE_SELECTORS.get(host, ()):
        body = _candidate(soup, selector)
        if body: candidates.append(("site_selector", selector, body, True))
    for selector in GENERIC_SELECTORS:
        body = _candidate(soup, selector)
        if body: candidates.append(("generic_selector", selector, body, True))

    cleaned, removed = _clean_fragment(soup)
    extracted = trafilatura.extract(str(cleaned), url=base_url, output_format="html", include_links=True, include_tables=True, favor_recall=True)
    if extracted:
        candidates.append(("trafilatura", "", BeautifulSoup(extracted, "lxml"), removed))

    best = None
    rank = {"detail_content": 5, "thin_content": 4, "template_polluted": 3, "list_page": 2, "navigation_only": 1, "extraction_failed": 0}
    for method, selector, body, was_removed in candidates:
        md, plain = _to_markdown(body)
        quality = content_quality_gate(md, title, base_url, selector_used=selector)
        score = (rank[quality.content_quality_class], quality.main_paragraph_count, -quality.navigation_like_ratio, quality.total_text_length)
        if best is None or score > best[0]: best = (score, method, selector, md, plain, was_removed, quality)

    if best:
        _, method, selector, md, plain, was_removed, quality = best
    else:
        method, selector, md, plain, was_removed = "extraction_failed", "", "", "", removed
        quality = content_quality_gate("", title, base_url)
    return ParsedPage(soup, md, plain, list(dict.fromkeys(links)), list(dict.fromkeys(attachments)), list(dict.fromkeys(images)), method, selector, was_removed, quality)
