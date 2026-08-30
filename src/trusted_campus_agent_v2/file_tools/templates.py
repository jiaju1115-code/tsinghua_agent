from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from .models import FilePlan, SectionSpec


@dataclass(frozen=True)
class CampusTemplate:
    key: str
    name: str
    description: str
    sections: tuple[str, ...]


TEMPLATES: dict[str, CampusTemplate] = {
    "social_practice_report": CampusTemplate(
        "social_practice_report", "社会实践报告", "实践背景、过程、成果、反思与附件清单",
        ("摘要", "实践背景与目标", "实践过程", "主要成果", "问题与反思", "结论与建议", "附件清单"),
    ),
    "event_plan": CampusTemplate(
        "event_plan", "活动策划书", "目标、对象、分工、日程、预算、风险与复盘指标",
        ("活动概述", "目标与受众", "时间地点", "流程与分工", "物资与预算", "宣传方案", "风险预案", "复盘指标"),
    ),
    "scholarship_application": CampusTemplate(
        "scholarship_application", "奖学金申请材料", "申请依据、个人情况、事迹、证明与承诺",
        ("申请说明", "基本情况", "学业表现", "实践与服务", "科研与创新", "证明材料清单", "真实性承诺"),
    ),
    "meeting_minutes": CampusTemplate(
        "meeting_minutes", "会议纪要", "会议信息、议题、结论、责任人与截止时间",
        ("会议信息", "议题与讨论", "决议事项", "行动项", "待确认事项"),
    ),
    "course_report": CampusTemplate(
        "course_report", "课程报告", "摘要、问题、方法、分析、结论和参考资料",
        ("摘要", "研究问题", "背景与相关工作", "方法", "分析与结果", "结论", "参考资料"),
    ),
}

TEMPLATE_ALIASES = {
    "社会实践": "social_practice_report", "实践报告": "social_practice_report",
    "活动策划": "event_plan", "策划书": "event_plan",
    "奖学金": "scholarship_application", "申请材料": "scholarship_application",
    "会议纪要": "meeting_minutes", "纪要": "meeting_minutes",
    "课程报告": "course_report", "报告": "course_report",
}


def infer_template_key(request: str, explicit: str | None = None) -> str:
    if explicit in TEMPLATES:
        return str(explicit)
    for marker, key in TEMPLATE_ALIASES.items():
        if marker in request:
            return key
    return "course_report"


def scaffold_plan(
    request: str,
    output_format: str,
    *,
    template_key: str | None = None,
    title: str | None = None,
) -> FilePlan:
    key = infer_template_key(request, template_key)
    template = TEMPLATES[key]
    sections = [
        SectionSpec(heading=heading, paragraphs=["[请根据实际情况补充]"])
        for heading in template.sections
    ]
    return FilePlan(
        title=title or template.name,
        output_format=output_format,  # type: ignore[arg-type]
        template_key=key,
        subtitle="清问·TsingAsk 可信校园事务智能体生成",
        sections=deepcopy(sections),
        metadata={"request": request, "template_name": template.name},
    )
