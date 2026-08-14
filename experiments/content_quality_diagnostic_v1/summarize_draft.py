import json
from collections import Counter
from pathlib import Path

p=Path(r"D:\python_projects\tsinghua_ai\data_second\content_quality_diagnostic_v1\diagnostic_draft.json")
rows=json.loads(p.read_text(encoding="utf-8"))

print("LOADING",Counter((r["loading_marker"],r["content_quality_class"]) for r in rows))
for cls in ["content_missing","navigation_only","template_polluted","mixed_or_uncertain","thin_content"]:
    subset=[r for r in rows if r["content_quality_class"]==cls]
    print(f"\n### {cls} {len(subset)}")
    for r in subset:
        print(f'{r["id"]}\t{r["existing_action"]}\t{r["source_domain"]}\tL{r["total_text_length"]}/N{r["navigation_like_ratio"]}/M{r["main_paragraph_count"]}/K{r["loading_marker"]}\t{r["title"]}')
print("\n### list counts",Counter(r["list_page_type"] for r in rows if r["content_quality_class"]=="list_page"))
for r in [r for r in rows if r["content_quality_class"]=="list_page"]:
    print(f'{r["id"]}\t{r["existing_action"]}\t{r["list_page_type"]}\t{r["should_follow_links"]}\tL{r["total_text_length"]}/N{r["navigation_like_ratio"]}/M{r["main_paragraph_count"]}\t{r["title"]}')
print("\n### detail")
for r in [r for r in rows if r["content_quality_class"]=="detail_content"]:
    print(f'{r["id"]}\t{r["existing_action"]}\tL{r["total_text_length"]}/N{r["navigation_like_ratio"]}/M{r["main_paragraph_count"]}\t{r["title"]}')
