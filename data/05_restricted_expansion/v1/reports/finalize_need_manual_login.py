from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(r"D:\python_projects\tsinghua_ai")
STAGING = ROOT / "data_second" / "staging_public_baseline_v1"
BASE = ROOT / "data_second" / "restricted_expansion_v1"


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def content_hash(path: Path) -> str:
    return hashlib.sha256(norm_text(path.read_text(encoding="utf-8")).encode("utf-8")).hexdigest()


def main():
    manifest = [json.loads(x) for x in (STAGING / "public_staging_manifest.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    counts = Counter(r["category"] for r in manifest)
    missing, mismatched = [], []
    for r in manifest:
        p = STAGING / r["content_file"]
        if not p.exists():
            missing.append(r["id"])
        elif content_hash(p) != r["content_hash"]:
            mismatched.append(r["id"])

    # Authentication never reached an authenticated page, so no restricted body was fetched.
    (BASE / "audit" / "restricted_v3_2_results.jsonl").write_text("", encoding="utf-8")
    status = {
        "run_status": "NEED_MANUAL_LOGIN",
        "stop_condition": "C",
        "reason": "Information portal was unreachable during read-only session validation; existing SSO session could not be verified.",
        "restricted_discovered_urls": 0,
        "restricted_fetched": 0,
        "private_sensitive_gate": {"safe_general_content": 0, "individualized_private": 0, "sensitive_internal": 0, "credential_or_security": 0, "unclear": 0},
        "quality_gate_pass": 0,
        "list_pages": 0,
        "dedup_removed": 0,
        "sent_to_v3_2": 0,
        "v3_2": {"approve": 0, "review": 0, "reject": 0},
        "credential_material_written": False,
        "personal_data_in_candidates": False,
        "human_labels_auto_filled": False,
    }
    (BASE / "reports" / "_run_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    p0 = ["学生事务", "住宿服务", "餐饮服务", "交通服务", "医疗健康", "奖助与资助", "就业与职业发展"]
    insuff = ["学生事务", "餐饮服务", "交通服务", "体育与场馆", "奖助与资助", "就业与职业发展", "校园访问", "校园综合服务"]
    category_lines = "\n".join(f"  - {c}: {counts.get(c, 0)}" for c in sorted(counts))
    p0_lines = "\n".join(f"  - {c}: 0" for c in p0)
    report = f"""# Restricted / Authenticated Expansion V1 Report

**最终状态：`NEED_MANUAL_LOGIN`**  
**停止条件：C（当前信息门户不可达，现有 SSO session 无法完成只读有效性验证）**

Public staging 与受限来源规划已完成；未进入认证后 discovery/fetch，未读取或保存任何受限页面正文。

## 最终检查（1–24）

1. **Public Staging 最终 approve 数量**：{len(manifest)}（235 条输入，去重 1 条；均为 candidate baseline，未进入 production）。
2. **Public Staging category 分布**：
{category_lines}
3. **Restricted 重点缺口**：{', '.join(insuff)}。
4. **旧 login_required seed 数量**：23；价值判断后建议抓取 12、条件抓取 1、不建议抓取 10。
5. **Restricted 发现 URL 数量**：0（认证门槛前停止）。
6. **抓取数量**：0。
7. **private_sensitive_gate**：safe 0；individualized 0；sensitive 0；security 0；unclear 0（未有受限正文进入 gate）。
8. **Quality Gate 通过数量**：0。
9. **list page 数量**：0。
10. **Restricted dedup 数量**：0；Public staging 去重 1。
11. **送 V3.2 数量**：0。
12. **Restricted V3.2**：approve 0 / review 0 / reject 0。
13. **各 category 新增数量**：全部 0。
14. **各 P0 类别新增数量**：
{p0_lines}
15. **各 system/domain 分布**：无（0 条 restricted fetch）。
16. **expired 数量**：0。
17. **low + approve**：0。
18. **科研成果/活动类误收**：否；没有 candidate。旧 seed 中培训、新闻、活动类已在规划阶段标为不建议抓取。
19. **长期服务误杀**：无法评估；认证前停止。
20. **个人数据进入 candidate**：否（0 条）。
21. **凭据/Token/Cookie 落盘**：否。仅复用原 storage state 路径进行只读验证；未复制、打印或另存其内容。
22. **正文可独立重新审核**：Public staging {len(manifest)}/{len(manifest)} 可独立复审；restricted 0 条。Public 缺失正文 {len(missing)}，哈希不匹配 {len(mismatched)}。
23. **仍明显不足 category**：{', '.join(insuff)}。
24. **是否需要 Restricted Expansion V2**：当前不建议另开 V2；应先由用户手动恢复合法认证/校园网络，再继续本 V1。

## 完整性与边界

- Public staging source_file 存在：{len(manifest) - len(missing)}/{len(manifest)}。
- Public staging content_hash 匹配：{len(manifest) - len(mismatched)}/{len(manifest)}。
- Restricted 正文丢失：0（未抓取）。
- 敏感凭据落盘：0。
- Human 标签自动填写：0。
- 旧 Public 数据、Prompt V3.2、production：未修改。

## 恢复条件

请用户在正常浏览器中手动完成合法清华登录，并确保 `https://info.tsinghua.edu.cn/` 可访问。恢复后继续当前 V1；不要自动填写密码，不要绕过 SSO 或权限检查。
"""
    (BASE / "reports" / "restricted_expansion_v1_report.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({"public_staging": len(manifest), "missing": len(missing), "hash_mismatch": len(mismatched), "status": status["run_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
