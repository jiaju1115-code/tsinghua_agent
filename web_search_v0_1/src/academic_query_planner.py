from __future__ import annotations
from dataclasses import asdict, dataclass
from .router_v0_1 import TERMS

@dataclass(frozen=True)
class AcademicPlan:
    original_problem:str; subject:str; topic:str; subtopics:list[str]; problem_type:str; knowledge_needs:list[str]; formula_needs:list[str]; theorem_needs:list[str]; method_needs:list[str]; condition_needs:list[str]; knowledge_queries:list[str]; knowledge_atoms:list[dict]
    def to_dict(self): return asdict(self)

RULES=[
 (("泊松","poisson"),"概率统计","泊松分布","moment_calculation",["泊松分布期望","泊松分布方差","二阶矩与方差关系"],["E(X)=λ","Var(X)=λ","E(X²)=Var(X)+[E(X)]²"],[],["使用矩与方差关系"],["参数λ"],["泊松分布 期望 方差 二阶矩 公式","Poisson distribution expectation variance second moment formula"]),
 (("积分","∫"),"高等数学","积分方法","integration",["积分定义","分部积分法","换元积分法"],["分部积分公式","换元积分公式"],[],["识别被积函数并选择方法"],["可积性条件"],["积分 分部积分 换元 方法 公式","integration methods integration by parts substitution formula"]),
 (("矩阵","特征值","对角化"),"线性代数","矩阵与特征理论","matrix_analysis",["特征值定义","特征向量定义","可对角化条件"],["特征多项式"],["可对角化定理"],["求特征值与特征向量"],["代数重数与几何重数"],["矩阵 特征值 特征向量 可对角化 定理","matrix eigenvalue eigenvector diagonalizable theorem"]),
 (("力","加速度","牛顿","斜面"),"大学物理","经典力学","force_analysis",["牛顿第二定律","受力分析","加速度关系"],["F=ma"],["牛顿运动定律"],["画受力图并列方程"],["约束与摩擦条件"],["牛顿第二定律 受力分析 加速度 方法","Newton second law free body diagram acceleration method"]),
 (("ols","回归","异方差","内生性"),"经济学/计量","计量回归","regression_analysis",["OLS假设","无偏性","估计量性质"],["OLS估计式"],["Gauss-Markov定理"],["回归估计与检验"],["外生性及同方差条件"],["OLS assumptions unbiasedness Gauss Markov theorem","OLS 假设 无偏性 高斯马尔可夫 定理"]),
 (("复杂度","算法","排序","递归","动态规划"),"计算机/算法","算法分析","algorithm_analysis",["渐近记号","递推关系","复杂度分析方法"],["T(n)递推式"],["主定理"],["递推展开或主定理分析"],["输入规模与基例"],["算法 时间复杂度 递推式 主定理","algorithm time complexity recurrence master theorem"]),
 (("级数","收敛"),"高等数学","极限与级数","calculus_analysis",["收敛定义","判别法","极限性质"],["比值判别法公式","根值判别法公式"],["比较判别法"],["选择收敛判别法"],["正项或交错级数条件"],["级数 收敛 判别法 比值 根值 比较","series convergence tests ratio root comparison"]),
 (("拉格朗日",),"高等数学","约束极值","constrained_optimization",["拉格朗日函数","一阶条件","约束极值条件"],["拉格朗日乘数方程"],["拉格朗日乘数法"],["构造拉格朗日函数并求驻点"],["约束函数可微"],["拉格朗日乘数法 约束极值 一阶条件","Lagrange multipliers constrained optimization first order conditions"]),
 (("弹性","效用","边际","生产函数"),"经济学/计量","微观经济学","economic_analysis",["弹性定义","边际分析","导数解释"],["弹性公式"],[],["比例变化分析"],["函数可微及变量范围"],["经济学 弹性 边际 分析 定义 公式","economics elasticity marginal analysis definition formula"])
]

def plan_academic(problem:str)->AcademicPlan:
    q=problem.lower()
    for triggers,subject,topic,ptype,needs,formulas,theorems,methods,conditions,queries in RULES:
        if any(t in q for t in triggers):
            atoms=[{"knowledge_atom_id":f"K{i+1}","description":x,"type":"FORMULA" if i<len(formulas) else ("THEOREM" if theorems else "METHOD"),"core":True} for i,x in enumerate(needs)]
            return AcademicPlan(problem,subject,topic,[topic],ptype,needs,formulas,theorems,methods,conditions,queries[:2],atoms)
    hits=[(s,w) for s,ws in TERMS["subjects"].items() for w in ws if w.lower() in q]
    subject,topic=hits[0] if hits else ("未确定","课程概念")
    needs=[f"{topic} 定义",f"{topic} 方法",f"{topic} 条件或公式"]
    atoms=[{"knowledge_atom_id":f"K{i+1}","description":x,"type":t,"core":True} for i,(x,t) in enumerate(zip(needs,["DEFINITION","METHOD","CONDITION"]))]
    return AcademicPlan(problem,subject,topic,[topic],"concept_or_method",needs,[],[],[f"{topic} 通用处理方法"],[],[f"{topic} definition theorem formula method",f"{topic} 定义 定理 公式 方法"],atoms)
