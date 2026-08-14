from __future__ import annotations

import csv
import logging
from pathlib import Path
from threading import Lock

CSV_SCHEMAS = {
    "success.csv": ["id", "url", "title", "markdown_path", "timestamp"],
    "failed.csv": ["url", "error_type", "error_message", "retry_count", "timestamp"],
    "skipped.csv": ["url", "reason", "timestamp"],
    "auth_required.csv": ["url", "final_url", "detected_reason", "timestamp"],
    "duplicates.csv": ["duplicate_url", "canonical_url", "content_hash", "detected_at"],
    "possible_duplicates.csv": ["id_1", "id_2", "url_1", "url_2", "similarity", "detected_at"],
}

class CrawlLogger:
    def __init__(self, log_dir: Path):
        self.log_dir, self.lock = log_dir, Lock()
        self.logger = logging.getLogger("crawler")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh = logging.FileHandler(log_dir / "crawl.log", encoding="utf-8")
        fh.setFormatter(fmt); self.logger.addHandler(fh)
        for name, fields in CSV_SCHEMAS.items():
            path = log_dir / name
            if not path.exists():
                with path.open("w", newline="", encoding="utf-8-sig") as f:
                    csv.DictWriter(f, fieldnames=fields).writeheader()

    def csv(self, name: str, row: dict) -> None:
        with self.lock, (self.log_dir / name).open("a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_SCHEMAS[name], extrasaction="ignore").writerow(row)
        self.logger.info("%s %s", name, row)
