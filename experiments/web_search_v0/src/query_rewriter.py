from __future__ import annotations

import re
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class AcademicRewrite:
    original_problem: str
    subject: str
    topics: list[str]
    needed_knowledge: list[str]
    knowledge_queries: list[str]

RULES = [
    (("泊松", "poisson"), "概率论", ["泊松分布"], ["泊松分布期望", "泊松分布方差", "二阶矩与方差关系"], ["泊松分布 期望 方差 二阶矩 公式", "Poisson distribution expectation variance second moment formula"]),
    (("积分", "∫"), "高等数学", ["积分方法"], ["积分定义", "分部积分法", "换元积分法"], ["积分 方法 公式 分部积分 换元 定义", "integration methods formula integration by parts substitution"]),
    (("矩阵", "特征值", "行列式"), "线性代数", ["矩阵理论"], ["矩阵定义", "特征值定理", "线性方程组方法"], ["linear algebra matrix eigenvalue determinant theorem method"]),
    (("牛顿", "力", "加速度"), "大学物理", ["经典力学"], ["牛顿第二定律", "受力分析", "运动学关系"], ["Newton second law force acceleration derivation method"]),
    (("复杂度", "算法", "排序"), "计算机科学", ["算法分析"], ["时间复杂度", "渐近记号", "算法设计方法"], ["algorithm time complexity asymptotic notation analysis method"]),
    (("边际", "成本", "需求", "供给", "ols"), "经济学", ["微观经济学/计量经济学"], ["边际分析", "OLS 假设", "一阶条件"], ["economics marginal analysis OLS assumptions first order condition"]),
]

def rewrite_academic_query(original_problem: str) -> AcademicRewrite:
    q = original_problem.lower()
    for triggers, subject, topics, knowledge, queries in RULES:
        if any(trigger in q for trigger in triggers):
            return AcademicRewrite(original_problem, subject, topics, knowledge, queries)
    stripped = re.sub(r"\b\d+(?:\.\d+)?\b", "", original_problem)
    words = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", stripped)[:5]
    topic = " ".join(words) or "大学课程概念"
    return AcademicRewrite(original_problem, "未确定", [topic], ["definition", "formula", "theorem", "method"], [f"{topic} definition formula theorem method"])

def direct_answer_search_guard(original_problem: str, candidate_title: str, candidate_text: str) -> bool:
    """Flag likely copies of a submitted exercise; never use as preferred evidence."""
    source = (candidate_title + " " + candidate_text).lower()
    normalized_problem = re.sub(r"\d+(?:\.\d+)?", "", original_problem.lower())
    normalized_source = re.sub(r"\d+(?:\.\d+)?", "", source)
    # Character-level similarity covers compact Chinese exercises, where word tokenization
    # would otherwise produce too few tokens for a reliable overlap threshold.
    if len(normalized_problem) >= 12 and SequenceMatcher(None, normalized_problem, normalized_source).ratio() >= 0.70:
        return True
    tokens = [t for t in re.findall(r"[\u4e00-\u9fff]{2,}|[a-z]{3,}", normalized_problem)]
    return bool(tokens) and sum(token in normalized_source for token in tokens) / len(tokens) >= 0.75
