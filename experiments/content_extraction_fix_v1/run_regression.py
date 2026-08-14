from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai")
RUN = ROOT / "data_second" / "public_expansion_v1" / "run_6"
DIAG = ROOT / "data_second" / "content_quality_diagnostic_v1"
OUT = ROOT / "data_second" / "content_extraction_fix_v1"
HTML = OUT / "diagnostics" / "html"
REG_OUT = OUT / "regression_outputs"
SAMPLES = OUT / "regression_samples"
for p in (HTML, REG_OUT, SAMPLES, OUT / "reports"): p.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "data_first"))

from crawler.parser import parse_html


SAMPLE_GROUPS = {
    "content_missing": ["PUBEXP000013", "PUBEXP000015", "PUBEXP000036", "PUBEXP000038", "PUBEXP000053", "PUBEXP000076", "PUBEXP000113", "PUBEXP000166", "PUBEXP000224", "PUBEXP000231"],
    "navigation_only": ["PUBEXP000020", "PUBEXP000032", "PUBEXP000092", "PUBEXP000160", "PUBEXP000242"],
    "template_polluted": ["PUBEXP000010", "PUBEXP000029", "PUBEXP000057", "PUBEXP000153", "PUBEXP000245"],
    "detail_content": ["PUBEXP000003", "PUBEXP000021", "PUBEXP000067", "PUBEXP000141", "PUBEXP000247"],
    "list_page": ["PUBEXP000012", "PUBEXP000039", "PUBEXP000096", "PUBEXP000097"],
}
LEGACY_ID_MAP = {
    "PUBEXP000015 (附件旧轮次：端午安全检查)": "PUBEXP000038",
    "PUBEXP000016 (附件旧轮次：招聘信息)": "PUBEXP000039",
    "PUBEXP000026 (附件旧轮次：法律法规)": "PUBEXP000096",
    "PUBEXP000027 (附件旧轮次：政策文件)": "PUBEXP000097",
}

all_old = {r["id"]: r for r in json.loads((DIAG / "final_records.json").read_text(encoding="utf-8"))}
sample_ids = [x for group in SAMPLE_GROUPS.values() for x in group]
assert len(sample_ids) == 29 and len(set(sample_ids)) == 29
samples = []
for group, ids in SAMPLE_GROUPS.items():
    for doc_id in ids:
        old = all_old[doc_id]
        samples.append({
            "id": doc_id, "title": old["title"], "url": old["url"], "old_content_quality_class": group,
            "diagnostic_class": old["content_quality_class"], "old_text_length": old["total_text_length"],
            "sample_role": group, "source_domain": old["source_domain"],
            "legacy_required_reference": "; ".join(k for k,v in LEGACY_ID_MAP.items() if v == doc_id),
        })
(SAMPLES / "regression_test_set.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_name(doc_id: str, title: str, ext: str) -> Path:
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" ._")[:70]
    return Path(f"{doc_id}_{title}.{ext}")


def fetch_with_curl(url: str, target: Path) -> tuple[bool, str]:
    if target.exists() and target.stat().st_size > 100:
        return True, f"cached\t{url}\t{target.stat().st_size}"
    cmd = [
        "curl.exe", "-k", "-L", "--http1.1", "--connect-timeout", "15", "--max-time", "45",
        "--retry", "1", "--retry-delay", "1", "-A",
        "TsinghuaCampusKnowledgeCollector/1.0 (public academic project; fixed regression test)",
        "-o", str(target), "-w", "%{http_code}\t%{url_effective}\t%{size_download}", url,
    ]
    done = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    status = done.stdout.strip()
    ok = done.returncode == 0 and status.startswith("200\t") and target.exists() and target.stat().st_size > 100
    return ok, status or done.stderr[-500:]


def result_for(sample: dict, page, fetch_status: str) -> tuple[str, str]:
    old = sample["old_content_quality_class"]
    q = page.quality
    if old == "detail_content":
        if not q.passed or q.content_quality_class not in {"detail_content", "thin_content", "template_polluted"}:
            return "REGRESSION", "原正常详情未通过新质量闸门"
        if len(page.plain_text) < max(120, sample["old_text_length"] * 0.45):
            return "REGRESSION", "原正常详情正文长度显著下降"
        return "PASS", "原正常详情仍保留连续主体正文"
    if old == "list_page":
        return ("PASS", "列表页被稳定识别且不会作为详情正文保存") if q.content_quality_class == "list_page" and not q.passed else ("FAIL", "列表页仍可能被误当详情正文")
    if old == "navigation_only":
        if not q.passed and q.content_quality_class in {"navigation_only", "extraction_failed", "list_page"}:
            return "PASS", "坏页面被质量闸门拦截，不再保存导航为正文"
        if q.passed and q.main_paragraph_count >= 1:
            return "PASS", "站点 selector 获得原先遗漏的主体内容"
        return "FAIL", "导航内容仍可能通过质量闸门"
    if old == "template_polluted":
        if not q.passed: return "FAIL", "模板清洗后未保留可信主体"
        old_nav = all_old[sample["id"]]["navigation_like_ratio"]
        if q.navigation_like_ratio <= max(0.20, old_nav * 0.55): return "PASS", "站点容器显著降低模板污染且保留主体"
        if q.navigation_like_ratio < old_nav: return "PARTIAL", "模板污染下降但仍偏高"
        return "FAIL", "模板污染未明显改善"
    if q.passed and q.content_quality_class in {"detail_content", "thin_content", "template_polluted"}:
        return "PASS", "原缺失详情已取得可靠连续主体正文"
    if len(page.plain_text) > sample["old_text_length"] * 1.5 and q.main_paragraph_count >= 1:
        return "PARTIAL", "正文明显增加，但质量闸门仍未完全通过"
    return "FAIL", "仍未获得可靠主体正文"


results = []
for index, sample in enumerate(samples, 1):
    html_path = HTML / safe_name(sample["id"], sample["title"], "html")
    ok, fetch_status = fetch_with_curl(sample["url"], html_path)
    if not ok:
        results.append({**sample, "new_extraction_method": "fetch_failed", "new_text_length": 0, "new_content_quality_class": "extraction_failed", "selector_used": "", "dynamic_fetch_used": False, "template_removed": False, "quality_gate_pass": False, "regression_result": "REGRESSION" if sample["sample_role"] == "detail_content" else "FAIL", "diagnostic_note": f"固定样本请求失败：{fetch_status}"})
        continue
    raw = html_path.read_bytes()
    try: html = raw.decode("utf-8-sig")
    except UnicodeDecodeError: html = raw.decode("gb18030", errors="replace")
    page = parse_html(html, sample["url"], {"utm_source","utm_medium","utm_campaign","from"})
    q = page.quality
    regression_result, note = result_for(sample, page, fetch_status)
    md_path = REG_OUT / safe_name(sample["id"], sample["title"], "md")
    md_path.write_text(page.markdown, encoding="utf-8")
    results.append({
        **sample, "new_extraction_method": page.extraction_method, "new_text_length": len(page.plain_text),
        "new_content_quality_class": q.content_quality_class, "selector_used": page.selector_used,
        "dynamic_fetch_used": False, "template_removed": page.template_removed,
        "quality_gate_pass": q.passed, "regression_result": regression_result,
        "diagnostic_note": note + f"；gate={q.reason}；fetch={fetch_status}",
        "new_short_line_ratio": round(q.short_line_ratio, 4), "new_navigation_like_ratio": round(q.navigation_like_ratio, 4),
        "new_main_paragraph_count": q.main_paragraph_count, "new_long_paragraph_count": q.long_paragraph_count,
        "title_match_ratio": round(q.title_match_ratio, 4), "output_markdown": str(md_path),
    })
    print(f"[{index:02d}/29] {sample['id']} {regression_result} {q.content_quality_class} {len(page.plain_text)} {page.extraction_method} {page.selector_used}", flush=True)
    time.sleep(0.75)

(OUT / "regression_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
summary = {
    "total": len(results), "results": dict(Counter(r["regression_result"] for r in results)),
    "by_old_class": {c: dict(Counter(r["regression_result"] for r in results if r["old_content_quality_class"] == c)) for c in SAMPLE_GROUPS},
    "gate_blocked": sum(not r["quality_gate_pass"] for r in results),
    "bad_navigation_passed": sum(r["old_content_quality_class"] == "navigation_only" and r["quality_gate_pass"] and r["new_main_paragraph_count"] == 0 for r in results),
    "detail_regressions": [r["id"] for r in results if r["regression_result"] == "REGRESSION"],
    "legacy_id_map": LEGACY_ID_MAP,
}
(OUT / "regression_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
