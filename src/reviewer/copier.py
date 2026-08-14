import json,shutil
from pathlib import Path
from utils.paths import SOURCE_ROOT,PROJECT_ROOT,KNOWLEDGE_DIR,assert_destination

def save_review(candidate,result,kind):
    out=KNOWLEDGE_DIR/"02_ai_reviewed"/kind/f"{candidate['id']}.json";assert_destination(out)
    payload={**result,"source_markdown_path":candidate["source_markdown_path"],"access_level":candidate["access_level"],"source_mode":candidate["source_mode"],"dataset_origin":candidate["dataset_origin"]}
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")

def copy_by_action(candidate,action,portal=False):
    src=SOURCE_ROOT/candidate["source_markdown_path"]
    if portal:
        dest=(KNOWLEDGE_DIR/"05_rejected"/"portal_candidates" if action=="reject" else KNOWLEDGE_DIR/"03_needs_review"/"portal")/src.name
    else:
        base={"approve":KNOWLEDGE_DIR/"04_approved"/"public","review":KNOWLEDGE_DIR/"03_needs_review"/"public","reject":KNOWLEDGE_DIR/"05_rejected"/"public"}[action];dest=base/src.name
    assert_destination(dest);shutil.copy2(src,dest);return dest.relative_to(PROJECT_ROOT).as_posix()

