import csv
from pathlib import Path
from utils.paths import SOURCE_ROOT

def duplicate_ids():
    path=SOURCE_ROOT/"logs"/"possible_duplicates.csv";result=set()
    if path.exists():
        with path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):result.update((r.get("id_1",""),r.get("id_2","")))
    result.discard("");return result

