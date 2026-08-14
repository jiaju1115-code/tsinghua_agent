from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = PROJECT_ROOT / "knowledge" / "01_raw"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
LOG_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "crawl_state.db"

def ensure_directories() -> None:
    for path in (DATA_DIR, RAW_DIR, KNOWLEDGE_DIR, LOG_DIR, KNOWLEDGE_DIR/"01_raw_public", KNOWLEDGE_DIR/"01_raw_portal", DATA_DIR/"auth"):
        path.mkdir(parents=True, exist_ok=True)
