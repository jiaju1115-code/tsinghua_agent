"""Safely download and text-extract official attachments for V2 review."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import multiprocessing
import re
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "01_public_baseline"
V2_ROOT = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2"
RAW_DIR = V2_ROOT / "attachment_crawl_v1" / "data" / "files"
TEXT_DIR = V2_ROOT / "attachment_crawl_v1" / "knowledge" / "02_extracted_attachments"
INDEX = V2_ROOT / "attachment_crawl_v1" / "knowledge" / "attachment_index.jsonl"
MANIFEST = V2_ROOT / "attachment_candidate_manifest.jsonl"
REPORT = V2_ROOT / "attachment_quality_report.json"
CHECKPOINT = V2_ROOT / "attachment_crawl_v1" / "knowledge" / "attachment_checkpoint.jsonl"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if str(BASELINE) not in sys.path:
    sys.path.insert(0, str(BASELINE))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crawler.fetcher import Fetcher
from src.trusted_campus_agent_v2.metadata import (
    authority_level, infer_audience, infer_content_type, infer_department, infer_topics,
    normalize_source_date, policy_key,
)


ALLOWED_TYPES = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"}
ZIP_TYPES = {"docx", "xlsx", "pptx"}
OLE_TYPES = {"doc", "xls", "ppt"}
HIGH_VALUE_ATTACHMENT = re.compile(r"(?:申请|办理|表格|模板|证明|同意函|材料|指南|手册|办法|规定|细则|签证|实习|交换|就业|奖学金|资助|学籍|毕业|新生|校园卡|校园网|VPN)", re.I)


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle))


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def safe_name(value: str, fallback: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" ._")
    return (value[:100] or fallback)


def valid_signature(kind: str, content: bytes) -> bool:
    if kind == "pdf":
        return content.startswith(b"%PDF-")
    if kind in ZIP_TYPES:
        return content.startswith(b"PK\x03\x04")
    if kind in OLE_TYPES:
        return content.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    return False


def xml_text(content: bytes, prefix: str) -> str:
    values: list[str] = []
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith(prefix) or not name.endswith(".xml"):
                continue
            try:
                root = ElementTree.fromstring(archive.read(name))
            except ElementTree.ParseError:
                continue
            values.extend(node.text.strip() for node in root.iter() if node.text and node.text.strip())
    return "\n".join(values)


def extract_text(kind: str, content: bytes) -> str:
    if kind == "pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n\n".join((page.extract_text() or "") for page in pdf.pages[:300])[:2_000_000]
        except Exception:
            return ""
    if kind == "docx":
        return xml_text(content, "word/")[:2_000_000]
    if kind == "pptx":
        return xml_text(content, "ppt/slides/")[:2_000_000]
    if kind == "xlsx":
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            lines = []
            for sheet in workbook.worksheets:
                lines.append(f"## {sheet.title}")
                for row in sheet.iter_rows(values_only=True):
                    values = [str(value).strip() for value in row if value not in (None, "")]
                    if values:
                        lines.append(" | ".join(values))
                    if sum(len(line) for line in lines) >= 2_000_000:
                        break
            workbook.close()
            return "\n".join(lines)[:2_000_000]
        except Exception:
            return ""
    return ""


def _extract_worker(kind: str, content: bytes, output_path: str, error_path: str) -> None:
    try:
        Path(output_path).write_text(extract_text(kind, content), encoding="utf-8")
    except BaseException as exc:
        Path(error_path).write_text(f"{type(exc).__name__}: {exc}", encoding="utf-8")


def extract_text_bounded(kind: str, content: bytes, timeout_seconds: int = 45) -> tuple[str, str | None]:
    context = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory(prefix="tsingask-attachment-") as temporary:
        output_path = Path(temporary) / "output.txt"
        error_path = Path(temporary) / "error.txt"
        process = context.Process(target=_extract_worker, args=(kind, content, str(output_path), str(error_path)))
        process.start()
        process.join(timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(5)
            return "", "extraction_timeout"
        if error_path.is_file():
            return "", error_path.read_text(encoding="utf-8", errors="replace")
        if not output_path.is_file():
            return "", f"extractor_exit_{process.exitcode}"
        return output_path.read_text(encoding="utf-8", errors="replace"), None


def parent_metadata() -> dict[str, dict[str, Any]]:
    result = {}
    for row in jsonl(V2_ROOT / "crawl_candidate_manifest.jsonl"):
        source_id = row.get("source_id", "")
        if source_id.startswith("CRAWL_"):
            result[source_id.removeprefix("CRAWL_")] = row
        if row.get("source"):
            result[row["source"]] = row
    return result


def normalize_explicit_candidate(
    candidate: dict[str, Any], index_row: dict[str, Any], explicit_seed_map: dict[str, dict[str, str]],
) -> dict[str, Any]:
    seed = explicit_seed_map.get(str(candidate.get("source", "")))
    if not seed:
        return candidate
    text_path = ROOT / str(index_row.get("text_file") or "")
    body = text_path.read_text(encoding="utf-8-sig", errors="replace") if text_path.is_file() else ""
    title = str(seed.get("filename") or candidate.get("title") or index_row.get("title") or "官方附件")
    value = dict(candidate)
    value.update({
        "title": title,
        "department": infer_department(str(candidate.get("source", "")), title),
        "publish_date": normalize_source_date(title), "effective_date": None, "expiry_date": None,
        "audience": infer_audience(title, body), "topics": infer_topics("", title, body),
        "category": "官方附件", "time_status": "unknown", "access_level": "public",
    })
    value["topic"] = value["topics"][0]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--refresh-explicit-seeds", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_files <= 2000:
        raise SystemExit("--max-files must be between 1 and 2000")
    if not args.force and (INDEX.exists() or MANIFEST.exists() or REPORT.exists()):
        raise SystemExit("refusing to overwrite generated attachment artifacts; pass --force")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    parents = parent_metadata()
    explicit_seed_rows = csv_rows(ROOT / "configs" / "trusted_campus_agent_v2" / "official_attachment_seeds.csv")
    explicit_seed_map = {row.get("file_url", ""): row for row in explicit_seed_rows if row.get("file_url")}
    explicit_seed_urls = set(explicit_seed_map)
    discovered = (
        csv_rows(V2_ROOT / "public_crawl_v1" / "knowledge" / "attachments.csv")
        + csv_rows(V2_ROOT / "portal_crawl_v1" / "knowledge" / "portal_attachments.csv")
        + explicit_seed_rows
    )
    unique: list[dict[str, str]] = []
    seen = set()
    for row in discovered:
        url = row.get("file_url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(row)
    unique.sort(key=lambda row: (
        row.get("file_url", "") in explicit_seed_urls,
        bool(HIGH_VALUE_ATTACHMENT.search(row.get("filename", ""))),
        (parents.get(row.get("parent_page_id", "")) or parents.get(row.get("parent_page_url", "")) or {}).get("content_type") in {"policy", "procedure_guide", "faq"},
    ), reverse=True)
    fetcher = Fetcher({
        "user_agent": "TsingAskTrustedCampusV2/1.0 (official-attachment-review)",
        "request_delay_seconds": 1.0,
        "timeout_seconds": 15,
        "max_retries": 1,
        "max_response_bytes": 20_971_520,
    })
    latest_checkpoints: dict[str, dict[str, Any]] = {}
    for checkpoint in jsonl(CHECKPOINT):
        url = checkpoint.get("url")
        if not url:
            continue
        current = latest_checkpoints.get(url)
        checkpoint_success = bool(checkpoint.get("index_row")) and not (checkpoint.get("index_row") or {}).get("extraction_error")
        current_success = bool((current or {}).get("index_row")) and not ((current or {}).get("index_row") or {}).get("extraction_error")
        if checkpoint_success or not current_success:
            latest_checkpoints[url] = checkpoint
    usable_checkpoints = [
        row for url, row in latest_checkpoints.items()
        if not (args.refresh_explicit_seeds and url in explicit_seed_urls)
        and (row.get("terminal_status") or not (row.get("index_row") or {}).get("extraction_error"))
    ]
    completed_urls = {row["url"] for row in usable_checkpoints}
    index_rows: list[dict[str, Any]] = [row["index_row"] for row in usable_checkpoints if row.get("index_row")]
    candidates: list[dict[str, Any]] = [
        normalize_explicit_candidate(row["candidate"], row.get("index_row") or {}, explicit_seed_map)
        for row in usable_checkpoints if row.get("candidate")
    ]
    counts = Counter()
    for row in unique[: args.max_files]:
        url = row.get("file_url", "")
        if url in completed_urls:
            counts["resumed_from_checkpoint"] += 1
            continue
        kind = (row.get("file_type") or Path(urlsplit(url).path).suffix.lstrip(".")).lower()
        parent = parents.get(row.get("parent_page_id", "")) or parents.get(row.get("parent_page_url", "")) or {}
        is_explicit_seed = url in explicit_seed_urls
        if parent.get("admission_status") == "rejected_quality" and not HIGH_VALUE_ATTACHMENT.search(row.get("filename", "")):
            counts["skipped_low_value_parent"] += 1
            continue
        if kind not in ALLOWED_TYPES or not urlsplit(url).hostname or not urlsplit(url).hostname.endswith("tsinghua.edu.cn"):
            counts["rejected_type_or_domain"] += 1
            continue
        if not fetcher.allowed_by_robots(url):
            counts["robots_disallowed"] += 1
            print(f"[附件跳过] robots {url}")
            continue
        try:
            fetched = fetcher.fetch(url)
        except Exception as exc:
            counts["download_exception"] += 1
            error = f"{type(exc).__name__}: {exc}"[:500]
            print(f"[附件失败] {error} {url}")
            CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            with CHECKPOINT.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"url": url, "terminal_status": "download_failed", "error": error}, ensure_ascii=False, sort_keys=True) + "\n")
            completed_urls.add(url)
            continue
        if not fetched.response or fetched.response.status_code != 200:
            counts["download_failed"] += 1
            print(f"[附件失败] {url}")
            CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            with CHECKPOINT.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"url": url, "terminal_status": "download_failed"}, ensure_ascii=False, sort_keys=True) + "\n")
            completed_urls.add(url)
            continue
        content = fetched.response.content
        if not valid_signature(kind, content):
            counts["signature_rejected"] += 1
            print(f"[附件拒绝] 文件签名不符 {url}")
            continue
        digest = hashlib.sha256(content).hexdigest()
        filename = f"{digest[:16]}_{safe_name(row.get('filename', ''), 'attachment')}.{kind}"
        raw_path = RAW_DIR / filename
        raw_path.write_bytes(content)
        extracted, extraction_error = extract_text_bounded(kind, content)
        text_value = re.sub(r"\n{3,}", "\n\n", extracted).strip()
        text_path = None
        if text_value:
            text_path = TEXT_DIR / f"ATT_{digest[:16]}_{safe_name(row.get('filename', ''), 'attachment')}.md"
            text_path.write_text(f"# {row.get('filename') or filename}\n\n{text_value}\n", encoding="utf-8")
        title = row.get("filename") or filename
        topics = infer_topics("", title, text_value) if is_explicit_seed else parent.get("topics") or infer_topics("", title, text_value)
        index_row = {
            "id": f"ATT_{digest[:16]}", "title": title, "source": url,
            "parent_page_id": row.get("parent_page_id"), "parent_page_url": row.get("parent_page_url"),
            "file_type": kind, "size_bytes": len(content), "content_hash": digest,
            "raw_file": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "text_file": str(text_path.relative_to(ROOT)).replace("\\", "/") if text_path else None,
            "extracted_chars": len(text_value),
        }
        index_row["extraction_error"] = extraction_error
        index_rows.append(index_row)
        counts["downloaded"] += 1
        print(f"[附件成功] {kind} {title[:60]}")
        candidate = None
        if len(text_value) >= 200:
            candidate = {
                "source_id": index_row["id"], "title": title, "source": url,
                "department": infer_department(url, title) if is_explicit_seed else parent.get("department", "清华大学相关部门"),
                "publish_date": normalize_source_date(title) if is_explicit_seed else parent.get("publish_date"),
                "effective_date": None if is_explicit_seed else parent.get("effective_date"),
                "expiry_date": None if is_explicit_seed else parent.get("expiry_date"),
                "audience": infer_audience(title, text_value) if is_explicit_seed else parent.get("audience", ["全校学生"]),
                "authority_level": authority_level(url), "topic": topics[0], "topics": topics,
                "category": "官方附件" if is_explicit_seed else parent.get("category", "官方附件"),
                "content_type": infer_content_type(title, text_value),
                "time_status": "unknown" if is_explicit_seed else parent.get("time_status", "unknown"),
                "access_level": "public" if is_explicit_seed else parent.get("access_level", "public"),
                "admission_status": "auto_review_candidate", "review_status": "pending_automated_review",
                "policy_key": policy_key(title), "source_version": "TRUSTED_CAMPUS_V2_ATTACHMENT_CRAWL_V1",
                "candidate_content_file": index_row["text_file"], "content_hash": digest,
                "content_length": len(text_value), "quality_score": 0.75,
                "quality_reasons": [], "candidate_reason": "official attachment extracted; strict automated trust review required before serving",
            }
            candidates.append(candidate)
            counts["text_candidates"] += 1
        else:
            counts["download_only_no_text"] += 1
            if extraction_error:
                counts[extraction_error] += 1
                print(f"[附件提取跳过] {extraction_error} {title[:60]}")
        CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        with CHECKPOINT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"url": url, "index_row": index_row, "candidate": candidate}, ensure_ascii=False, sort_keys=True) + "\n")
        completed_urls.add(url)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in index_rows), encoding="utf-8")
    MANIFEST.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in candidates), encoding="utf-8")
    report = {"version": "TRUSTED_CAMPUS_V2_ATTACHMENT_QUALITY_REPORT_V1", "candidate_only": True, "discovered_rows": len(discovered), "unique_urls": len(unique), "stats": dict(sorted(counts.items()))}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
