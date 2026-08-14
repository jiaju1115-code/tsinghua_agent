from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ROOT = Path(r"D:\python_projects\tsinghua_ai\data_second")
OUT = ROOT / "prompt_v3_2_blind_test_v1" / "reports"


def normalize_url(url: str) -> str:
    parts = urlsplit(str(url or "").strip())
    host = (parts.hostname or "").lower()
    path = re.sub(r"/+", "/", parts.path or "/").rstrip("/") or "/"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith("utm_")))
    return urlunsplit((parts.scheme.lower(), host, path, query, ""))


audit = json.loads((ROOT / "public_rebuild_v1" / "audit" / "public_rebuild_v1_all_audited.json").read_text(encoding="utf-8"))
seen = json.loads((ROOT / "prompt_v3_test" / "audit" / "v3_inputs.json").read_text(encoding="utf-8"))
seen_ids = {x["id"] for x in seen}
seen_urls = {normalize_url(x["url"]) for x in seen}
pool = [x for x in audit if x["id"] not in seen_ids and normalize_url(x["url"]) not in seen_urls]

patterns = {
    "research_result": r"成果|突破|发表|论文|获奖|创新|项目启动|指南|战略合作",
    "person_award": r"获奖|荣誉|人物|专访|先进|教授|院士|团队|馆长致辞",
    "leader": r"领导|会见|访问|出席|讲话|调研|关怀|巡视",
    "cooperation": r"合作|签约|协议|共建|到访",
    "long_service": r"办法|须知|服务|网络|信息系统|开馆|借阅|自助|FAQ|联系我们|馆舍|预约",
    "research_resource": r"数据库|平台|实验室|研究中心|科研|资源|开放获取|OA|图书馆",
    "core_affairs": r"教务|学籍|学生|住宿|交通|医疗|医院|就业|奖助|资助|校园卡|迎新|毕业",
    "activity": r"活动|讲座|论坛|展览|工作坊|培训|通知|会议|开幕|举行|举办|报名",
    "medium": r"历史|沿革|概况|简介|文化|专题|专架|纪念|馆长致辞|机构设置|部门职能|科室职能",
}
result = {}
for tag, pattern in patterns.items():
    result[tag] = [
        {k: x.get(k, "") for k in ("id", "title", "url", "source_domain", "category", "content_type", "action", "source_file")}
        for x in pool if re.search(pattern, str(x.get("title", "")), re.I)
    ]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "candidate_type_scan.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: len(v) for k, v in result.items()}, ensure_ascii=False))
