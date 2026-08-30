from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.trusted_campus_agent_v2 import (
    CampusFileService,
    OpenAICompatibleFileToolPlanner,
    TrustedCampusAgentV2,
)


def _json_file(path: str | None) -> dict | None:
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def main() -> None:
    parser = argparse.ArgumentParser(description="清问·TsingAsk V2 本地文件工具（不发布）")
    parser.add_argument("request", help="自然语言文件需求")
    parser.add_argument("--format", choices=("docx", "xlsx", "pptx", "pdf"))
    parser.add_argument("--input", help="要读取或修改的本地文件")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--template", help="用户原模板路径")
    parser.add_argument("--template-key", choices=("social_practice_report", "event_plan", "scholarship_application", "meeting_minutes", "course_report"))
    parser.add_argument("--plan-json", help="LLM 生成的结构化 FilePlan JSON")
    parser.add_argument("--replacements-json", help="文本替换映射 JSON")
    parser.add_argument("--cell-updates-json", help="Excel 单元格更新 JSON，键为 Sheet!A1")
    parser.add_argument("--rag", action="store_true", help="先通过 Evidence Gate 检索官方要求")
    parser.add_argument("--shadow", action="store_true", help="显式使用未发布 shadow 知识库")
    parser.add_argument("--llm-tool-calling", action="store_true", help="让 OpenAI-compatible LLM 生成结构化 FilePlan")
    parser.add_argument("--llm-env-prefix", default="MOMO", help="LLM 环境变量前缀，默认 MOMO")
    parser.add_argument("--include-uploaded-content", action="store_true", help="向文件规划模型提供上传文件的解析内容")
    parser.add_argument(
        "--allow-external-file-content",
        action="store_true",
        help="显式允许把上传文件解析内容发给外部 LLM；默认禁止",
    )
    args = parser.parse_args()

    if args.llm_tool_calling and any((args.plan_json, args.replacements_json, args.cell_updates_json)):
        parser.error("--llm-tool-calling 不能与手工 plan/replacements/cell-updates JSON 同时使用")

    agent = TrustedCampusAgentV2(use_shadow=args.shadow) if (args.rag or args.llm_tool_calling) else None
    service = CampusFileService(rag_agent=agent)
    if args.llm_tool_calling:
        planner = OpenAICompatibleFileToolPlanner.from_env(args.llm_env_prefix)
        result = service.execute_with_llm(
            args.request,
            planner,
            uploaded_files=[args.input] if args.input else None,
            input_path=args.input,
            output_path=args.output,
            output_format=args.format,
            template_path=args.template,
            template_key=args.template_key,
            use_rag=True if args.rag else None,
            include_uploaded_content=args.include_uploaded_content,
            allow_external_file_content=args.allow_external_file_content,
        )
    else:
        route = service.router.route(args.request, [args.input] if args.input else [])
        result = service.execute(
            args.request,
            route=route,
            output_format=args.format,
            input_path=args.input,
            output_path=args.output,
            template_path=args.template,
            template_key=args.template_key,
            structured_content=_json_file(args.plan_json),
            replacements=_json_file(args.replacements_json),
            cell_updates=_json_file(args.cell_updates_json),
            use_rag=args.rag,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
