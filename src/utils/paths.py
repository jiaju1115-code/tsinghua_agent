from pathlib import Path

SOURCE_ROOT = Path(r"D:\python_projects\tsinghua_ai\data_first")
PROJECT_ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second")

DATA_DIR=PROJECT_ROOT/"data"
REVIEWS_DIR=PROJECT_ROOT/"reviews"
RAW_OUTPUT_DIR=REVIEWS_DIR/"raw_model_outputs"
KNOWLEDGE_DIR=PROJECT_ROOT/"knowledge"
REPORT_DIR=PROJECT_ROOT/"reports"
LOG_DIR=PROJECT_ROOT/"logs"

def ensure_dirs():
    for p in (DATA_DIR,REVIEWS_DIR,RAW_OUTPUT_DIR,REPORT_DIR,LOG_DIR,
              KNOWLEDGE_DIR/"02_ai_reviewed"/"public",KNOWLEDGE_DIR/"02_ai_reviewed"/"portal",
              KNOWLEDGE_DIR/"03_needs_review"/"public",KNOWLEDGE_DIR/"03_needs_review"/"portal",
              KNOWLEDGE_DIR/"04_approved"/"public",KNOWLEDGE_DIR/"05_rejected"/"public",
              KNOWLEDGE_DIR/"05_rejected"/"portal_candidates"):
        p.mkdir(parents=True,exist_ok=True)

def assert_destination(path:Path):
    resolved=path.resolve();source=SOURCE_ROOT.resolve()
    if resolved==source or source in resolved.parents:raise PermissionError("禁止写入 data_first 原始证据层")

