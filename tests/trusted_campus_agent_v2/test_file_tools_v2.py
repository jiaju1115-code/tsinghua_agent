from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.trusted_campus_agent_v2.file_tools import (
    CampusFileService,
    CampusToolRouter,
    FilePlan,
    FileToolCall,
    LLMToolConfig,
    OpenAICompatibleFileToolPlanner,
    SectionSpec,
    ToolCallingError,
)
from src.trusted_campus_agent_v2.file_tools.service import InsufficientFileEvidenceError


def sample_plan(fmt: str) -> FilePlan:
    return FilePlan(
        title="校园活动执行方案",
        output_format=fmt,  # type: ignore[arg-type]
        template_key="event_plan",
        subtitle="学生社团活动示例",
        author="测试用户",
        metadata={"template_name": "活动策划书", "department": "某院系", "date": "2026-08-30"},
        sections=[
            SectionSpec("活动概述", ["本活动用于验证文件工具端到端能力。"], ["面向全校学生", "遵循场地管理要求"]),
            SectionSpec("行动项", table=[["事项", "负责人", "截止时间"], ["提交申请", "张同学", "2026-09-01"]]),
        ],
        sources=[{"title": "官方入口", "url": "https://www.tsinghua.edu.cn/"}],
        workbook_sheets=[
            {"name": "任务清单", "rows": [["事项", "负责人", "状态"], ["提交申请", "张同学", "待办理"]]},
        ],
    )


def test_router_separates_qa_and_file_tools() -> None:
    router = CampusToolRouter()
    assert router.route("校园卡在哪里补办？").route == "rag_qa"
    route = router.route("请生成一个活动策划书Word")
    assert route.route == "file_tool"
    assert route.output_format == "docx"
    assert route.template_key == "event_plan"
    modified = router.route("请修改这个表格", ["upload.xlsx"])
    assert modified.action == "modify"
    assert modified.output_format == "xlsx"


@pytest.mark.parametrize("fmt", ["docx", "xlsx", "pptx", "pdf"])
def test_create_read_modify_roundtrip(tmp_path: Path, fmt: str) -> None:
    service = CampusFileService(output_dir=tmp_path)
    created = service.execute(
        f"生成{fmt}文件",
        action="create",
        output_format=fmt,
        structured_content=sample_plan(fmt),
        output_path=tmp_path / f"created.{fmt}",
        use_rag=False,
    )
    created_path = Path(created["artifact"]["download_path"])
    assert created_path.is_file() and created_path.stat().st_size > 500
    content = service.read(created_path)
    assert content["format"] == fmt
    if fmt in {"docx", "xlsx", "pptx"}:
        assert zipfile.is_zipfile(created_path)

    kwargs = {"replacements": {"提交申请": "提交审批"}}
    if fmt == "xlsx":
        kwargs["cell_updates"] = {"任务清单!C2": "已完成"}
    modified = service.execute(
        f"修改这个{fmt}文件",
        action="modify",
        output_format=fmt,
        input_path=created_path,
        output_path=tmp_path / f"modified.{fmt}",
        use_rag=False,
        **kwargs,
    )
    modified_path = Path(modified["artifact"]["download_path"])
    assert modified_path.is_file() and modified_path != created_path
    assert modified["artifact"]["preserved_template"]


class FakeRagAgent:
    def __init__(self, status: str = "SUPPORTED") -> None:
        self.status = status

    def ask(self, request: str) -> dict:
        return {
            "evidence_status": self.status,
            "response": {
                "confirmed_facts": [{"text": "申请人应提交实践报告。"}],
                "action_plan": {"materials": ["实践报告"], "steps": ["在线提交"]},
                "citations": [{"source_id": "S1", "title": "实践要求", "url": "https://example.tsinghua.edu.cn"}],
            },
        }


def test_rag_grounded_plan_includes_evidence_and_sources() -> None:
    plan, result = CampusFileService(rag_agent=FakeRagAgent()).plan_with_rag(
        "根据学校最新要求生成实践报告", "docx", "social_practice_report"
    )
    assert result["evidence_status"] == "SUPPORTED"
    assert plan.sections[0].heading == "学校要求（SUPPORTED）"
    assert plan.sources[0]["url"].endswith("tsinghua.edu.cn")


def test_rag_grounded_file_fails_closed_on_conflict() -> None:
    with pytest.raises(InsufficientFileEvidenceError):
        CampusFileService(rag_agent=FakeRagAgent("CONFLICT")).plan_with_rag(
            "根据学校最新要求生成实践报告", "docx"
        )


def test_openai_compatible_planner_emits_strict_tool_payload() -> None:
    captured: dict = {}

    def completion(payload: dict) -> dict:
        captured.update(payload)
        return {
            "model": "test-model",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "create_or_modify_campus_file",
                                    "arguments": """{
                                      \"action\": \"create\",
                                      \"output_format\": \"docx\",
                                      \"template_key\": \"social_practice_report\",
                                      \"use_rag\": true,
                                      \"structured_content\": {
                                        \"title\": \"社会实践报告\",
                                        \"sections\": [{\"heading\": \"实践概述\", \"paragraphs\": [\"内容\"]}],
                                        \"sources\": [{\"title\": \"伪造来源\", \"url\": \"https://invalid.example\"}]
                                      }
                                    }""",
                                },
                            }
                        ]
                    }
                }
            ],
        }

    planner = OpenAICompatibleFileToolPlanner(
        LLMToolConfig(api_base="https://api.example/v1", api_key="secret", model="test-model"),
        completion=completion,
    )
    route = CampusToolRouter().route("根据最新要求生成社会实践报告Word")
    call = planner.plan(
        "根据最新要求生成社会实践报告Word",
        route,
        evidence_context=[{"evidence_status": "SUPPORTED", "access_level": "public"}],
    )

    assert captured["tool_choice"]["function"]["name"] == "create_or_modify_campus_file"
    assert call.action == "create"
    assert call.output_format == "docx"
    assert call.plan is not None and call.plan.sources == []
    assert call.model == "test-model"


def test_llm_tool_call_fails_on_trusted_route_conflict() -> None:
    def completion(_: dict) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "create_or_modify_campus_file",
                                    "arguments": "{\"action\":\"create\",\"output_format\":\"pdf\",\"structured_content\":{\"title\":\"错误格式\"}}",
                                }
                            }
                        ]
                    }
                }
            ]
        }

    planner = OpenAICompatibleFileToolPlanner(
        LLMToolConfig(api_base="https://api.example/v1", api_key="secret", model="test-model"),
        completion=completion,
    )
    route = CampusToolRouter().route("生成一份Word会议纪要")
    with pytest.raises(ToolCallingError):
        planner.plan("生成一份Word会议纪要", route)


def test_external_planner_rejects_restricted_evidence_before_request() -> None:
    called = False

    def completion(_: dict) -> dict:
        nonlocal called
        called = True
        return {}

    planner = OpenAICompatibleFileToolPlanner(
        LLMToolConfig(api_base="https://api.example/v1", api_key="secret", model="test-model"),
        completion=completion,
    )
    route = CampusToolRouter().route("根据学校最新要求生成社会实践报告Word")
    with pytest.raises(PermissionError):
        planner.plan(
            "根据学校最新要求生成社会实践报告Word",
            route,
            evidence_context=[{"access_level": "campus_authenticated"}],
        )
    assert called is False


class RecordingPlanner:
    external = False

    def __init__(self) -> None:
        self.evidence: dict | None = None

    def plan(
        self,
        request: str,
        route: object,
        *,
        evidence_context: list[dict] | None = None,
        uploaded_content: dict | None = None,
    ) -> FileToolCall:
        self.evidence = evidence_context[0] if evidence_context else None
        return FileToolCall(
            action="create",
            output_format="docx",
            template_key="social_practice_report",
            use_rag=True,
            plan=FilePlan(
                title="社会实践报告",
                output_format="docx",
                sections=[SectionSpec("实践内容", ["依据学校要求填写。"])],
            ),
            model="recording-planner",
        )


def test_execute_with_llm_runs_rag_gate_then_creates_download(tmp_path: Path) -> None:
    planner = RecordingPlanner()
    service = CampusFileService(rag_agent=FakeRagAgent(), output_dir=tmp_path)
    result = service.execute_with_llm(
        "根据学校最新要求生成社会实践报告Word",
        planner,
        output_path=tmp_path / "practice.docx",
    )

    assert Path(result["artifact"]["download_path"]).is_file()
    assert result["evidence"]["evidence_status"] == "SUPPORTED"
    assert result["llm_tool_call"]["model"] == "recording-planner"
    assert result["llm_tool_call"]["model_paths_accepted"] is False
    assert planner.evidence and planner.evidence["citations"][0]["source_id"] == "S1"


def test_external_planner_cannot_receive_upload_without_opt_in(tmp_path: Path) -> None:
    upload = tmp_path / "upload.docx"
    upload.write_bytes(b"not-a-real-docx")

    class ExternalPlanner(RecordingPlanner):
        external = True

    with pytest.raises(PermissionError):
        CampusFileService(output_dir=tmp_path).execute_with_llm(
            "修改这个Word文件",
            ExternalPlanner(),
            uploaded_files=[upload],
            input_path=upload,
            include_uploaded_content=True,
        )
