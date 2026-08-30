from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2 import CampusFileService, FilePlan, SectionSpec


OUTPUT_DIR = ROOT / "data" / "04_kb_expansion_candidate" / "trusted_campus_v2" / "generated_files"


def build_plan(fmt: str) -> FilePlan:
    return FilePlan(
        title="清问·TsingAsk 文件能力验收样例",
        output_format=fmt,  # type: ignore[arg-type]
        template_key="course_report",
        subtitle="可信校园事务智能体 V2 · 本地候选版",
        author="清问·TsingAsk V2",
        metadata={"template_name": "文件能力说明", "department": "本地开发候选", "date": "2026-08-30"},
        sections=[
            SectionSpec(
                "已支持能力",
                ["系统将自然语言需求转成结构化 FilePlan，再由 Python 工具创建真实文件。"],
                ["DOCX：创建、回读、局部替换、套用用户模板", "XLSX：创建、回读、单元格更新、保留公式与样式", "PPTX：创建、回读、文本替换、保留原演示文稿", "PDF：创建、回读、文本重排修改"],
            ),
            SectionSpec(
                "校园模板",
                table=[
                    ["模板", "典型用途", "关键结构"],
                    ["社会实践报告", "实践总结", "背景、过程、成果、反思"],
                    ["活动策划书", "社团与院系活动", "目标、流程、分工、预算、风险"],
                    ["奖学金申请材料", "奖项申请", "学业、实践、科研、证明"],
                    ["会议纪要", "会议留痕", "议题、决议、责任人、截止时间"],
                    ["课程报告", "课程作业", "问题、方法、分析、结论、参考资料"],
                ],
            ),
            SectionSpec(
                "可信生成链路",
                ["涉及学校要求时，先运行 RAG 与 Evidence Gate。SUPPORTED/PARTIAL 才生成已获支持的内容；CONFLICT/NOT_SUPPORTED 拒绝生成权威结论。"],
                ["普通问答继续走原 RAG", "文件意图自动路由至对应工具", "生成结果返回绝对下载路径", "所有输出保留 candidate_only=true、published=false"],
            ),
        ],
        workbook_sheets=[
            {
                "name": "能力矩阵",
                "rows": [
                    ["格式", "创建", "读取", "修改", "模板保留", "当前限制"],
                    ["DOCX", "是", "是", "是", "尽量保留", "跨多个复杂文本框的替换有限"],
                    ["XLSX", "是", "是", "是", "保留", "不主动计算 Excel 专有公式"],
                    ["PPTX", "是", "是", "是", "尽量保留", "复杂母版占位符需专项适配"],
                    ["PDF", "是", "是", "文本重排", "否", "扫描件与复杂版式不能原样编辑"],
                ],
            },
            {
                "name": "校园模板",
                "rows": [["模板", "英文键"]] + [
                    ["社会实践报告", "social_practice_report"],
                    ["活动策划书", "event_plan"],
                    ["奖学金申请材料", "scholarship_application"],
                    ["会议纪要", "meeting_minutes"],
                    ["课程报告", "course_report"],
                ],
            },
        ],
        slides=[
            {"title": "从问答到文件交付", "bullets": ["自然语言理解与工具路由", "结构化 FilePlan", "Python 创建真实文件", "返回可下载路径"]},
            {"title": "四种格式完整闭环", "bullets": ["Word：优先完整跑通", "Excel：单元格级编辑", "PPT：保留源文件后另存", "PDF：创建与文本重排修改"]},
            {"title": "与可信 RAG 联动", "bullets": ["先检索最新有效官方来源", "Evidence Gate 判断支持度", "只写入被证据支持的要求", "冲突或无证据时拒绝猜测"]},
            {"title": "安全边界", "bullets": ["只在 V2 独立候选目录开发", "不修改 V1", "不提交、不发布", "输出均标记 candidate_only"]},
        ],
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    service = CampusFileService(output_dir=OUTPUT_DIR)
    outputs = []
    for fmt in ("docx", "xlsx", "pptx", "pdf"):
        result = service.execute(
            f"生成{fmt}验收样例",
            action="create",
            output_format=fmt,
            structured_content=build_plan(fmt),
            output_path=OUTPUT_DIR / f"tsingask_v2_file_capability_demo_final.{fmt}",
            use_rag=False,
        )
        artifact = result["artifact"]
        artifact["readback"] = service.read(artifact["path"])
        outputs.append(artifact)
    manifest = OUTPUT_DIR / "demo_manifest.json"
    manifest.write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"outputs": [item["path"] for item in outputs], "manifest": str(manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
