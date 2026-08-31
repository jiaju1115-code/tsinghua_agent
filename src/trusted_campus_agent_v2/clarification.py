from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


OFFICIAL_DIRECTIONS = {
    "教务": ("教务处办事指南或教学门户", "https://www.tsinghua.edu.cn/jwc/"),
    "学生事务": ("学生部及学生事务相关院系通知", "https://www.tsinghua.edu.cn/xsb/"),
    "校园生活": ("清华大学服务部门主页", "https://www.tsinghua.edu.cn/"),
    "科研实践": ("科研院、院系科研实践通知", "https://www.tsinghua.edu.cn/kyy/"),
    "国际交流": ("国际合作与交流处或国际学生学者中心", "https://www.is.tsinghua.edu.cn/"),
    "就业": ("学生职业发展指导中心办事指南", "https://career.tsinghua.edu.cn/"),
    "新生": ("招生与迎新官方通知", "https://www.join-tsinghua.edu.cn/"),
    "毕业": ("教务处、研究生院及就业中心离校指南", "https://career.tsinghua.edu.cn/"),
}

OFFICIAL_WECHAT = {
    "教务": "学在清华、清华大学本科教学、清华大学研究生教育",
    "学生事务": "清华大学小研在线、清华小五爷园",
    "校园生活": "清华紫荆之声、清华大学小研在线",
    "科研实践": "清华小五爷园及所在院系官方公众号",
    "国际交流": "清华大学国际学生学者中心",
    "就业": "清华就业、清华职业辅导",
    "新生": "清华招生、学在清华、清华研招",
    "毕业": "清华大学研究生教育、清华就业",
}


@dataclass(frozen=True)
class ClarificationDecision:
    needs_clarification: bool
    questions: tuple[str, ...]
    missing_slots: tuple[str, ...]
    search_guidance: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["questions"] = list(self.questions)
        value["missing_slots"] = list(self.missing_slots)
        value["search_guidance"] = list(self.search_guidance)
        return value


class ClarificationPolicy:
    """Turns an evidence boundary into useful questions and official lookup directions."""

    PROCEDURES = (
        "申请", "办理", "流程", "材料", "条件", "截止", "转系", "转专业", "交换", "奖学金",
        "离校", "报到", "补办", "挂失", "校园卡", "一卡通", "校园码",
    )

    @staticmethod
    def _known(query: str, context: dict[str, Any], key: str, markers: tuple[str, ...]) -> bool:
        return bool(context.get(key)) or any(marker in query for marker in markers)

    def assess(
        self,
        query: str,
        *,
        status: str,
        topics: list[str],
        context: dict[str, Any] | None = None,
        citations: list[dict[str, Any]] | None = None,
    ) -> ClarificationDecision:
        context = context or {}
        procedural = any(marker in query for marker in self.PROCEDURES)
        questions: list[str] = []
        missing: list[str] = []
        if procedural and not self._known(query, context, "audience", ("本科", "研究生", "博士", "国际学生", "毕业生", "新生")):
            missing.append("audience")
            questions.append("你目前是本科生、研究生、国际学生，还是其他身份？")
        if procedural and any(marker in query for marker in ("截止", "最新", "今年", "申请", "交换", "奖学金")) and not self._known(query, context, "term", ("春季", "秋季", "本学期", "下学期", "202", "今年", "明年")):
            missing.append("term")
            questions.append("你要办理的是哪个学年、学期或具体批次？")
        if any(marker in query for marker in ("转系", "转专业")) and not self._known(query, context, "target_department", ("转入", "目标院系", "目标专业", "转到")):
            missing.append("target_department")
            questions.append("你的当前院系和目标院系（或专业）分别是什么？")
        if "交换" in query and not self._known(query, context, "program", ("校级", "院系级", "院级", "指定项目")):
            missing.append("program")
            questions.append("你申请的是校级、院系级，还是某个指定交换项目？")
        if "奖学金" in query and not any(marker in query for marker in ("国家奖学金", "综合奖学金", "专项奖学金", "国际仲裁项目", "蒋南翔奖学金")):
            missing.append("scholarship_program")
            questions.append("你申请的具体奖学金或专项项目名称是什么？不同项目的材料和截止日期不能混用。")

        guidance = []
        if procedural or status != "SUPPORTED" or questions:
            guidance.append({
                "label": "清华大学信息门户（需校园身份登录）",
                "url": "https://info.tsinghua.edu.cn/",
                "how": "登录后搜索事项全称或主管部门，优先查看当前学期/当前批次通知、附件和联系人；不要直接套用往年截止日期。",
            })
            if any(term in query for term in ("校园卡", "一卡通", "校园码")):
                guidance.append({
                    "label": "“清华校园卡”小程序/公众号",
                    "url": "",
                    "how": "先在小程序查看挂失、余额和卡片服务；不同身份的补卡地点与材料可能不同，仍需在信息门户或注册中心当期说明中确认。",
                })
            for topic in topics or ["学生事务"]:
                label, url = OFFICIAL_DIRECTIONS.get(topic, OFFICIAL_DIRECTIONS["学生事务"])
                item = {"label": label, "url": url, "how": "在官网搜索事项名称，核对适用对象、发布日期、有效期、附件和咨询方式。"}
                if item not in guidance:
                    guidance.append(item)
                account = OFFICIAL_WECHAT.get(topic)
                if account:
                    guidance.append({
                        "label": f"官方微信公众号：{account}", "url": "",
                        "how": "微信内搜索事项关键词并优先看当年推送；公众号用于发现通知，最终仍以主管部门正式文件或信息门户为准。",
                    })
            for citation in citations or []:
                if citation.get("url"):
                    guidance.append({"label": f"本次检索到的来源：{citation.get('title', '已检索来源')}", "url": citation["url"], "how": "检查正文日期、附件和主管部门联系方式；若是历史通知，不直接沿用其中日期。"})
                    break
            if status == "CONFLICT":
                guidance.append({"label": "向主管部门确认冲突版本", "url": "", "how": "提供两个来源标题、发布日期和具体冲突点，请对方确认当前执行口径。"})
        needs = bool(questions) and (procedural or status in {"PARTIAL", "NOT_SUPPORTED", "CONFLICT"})
        unique_guidance = list({(item["label"], item["url"]): item for item in guidance}.values())
        return ClarificationDecision(needs, tuple(questions[:3]), tuple(missing[:3]), tuple(unique_guidance[:6]))
