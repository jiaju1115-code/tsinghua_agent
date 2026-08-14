from dataclasses import dataclass

CATEGORIES={"校园办事","校园生活","新生入校","规章制度","校园通知","其他"}
CONTENT_TYPES={"办事指南","服务指南","FAQ","规章制度","正式通知","临时通知","活动通知","新闻","人物宣传","科研信息","部门介绍","系统入口","其他"}
AUTHORITY={"high","medium","low","unknown"};FRESHNESS={"current","possibly_outdated","outdated","unknown"}
TIME_SENSITIVITY={"low","medium","high"};RISK={"none","low","medium","high"};ACTIONS={"approve","review","reject"}
REQUIRED=("id","relevance_score","knowledge_value","category","subcategory","content_type","authority","freshness","time_sensitivity","contains_actionable_information","personal_data_risk","possible_duplicate","possible_conflict","recommended_action","reason")

def validate_review(value:dict,expected_id:str|None=None)->dict:
    missing=[k for k in REQUIRED if k not in value]
    if missing:raise ValueError(f"缺少字段: {missing}")
    if expected_id and value["id"]!=expected_id:raise ValueError("审核ID不匹配")
    for name in ("relevance_score","knowledge_value"):
        if isinstance(value[name],bool) or not isinstance(value[name],int) or not 0<=value[name]<=100:raise ValueError(f"{name}必须是0-100整数")
    allowed={"category":CATEGORIES,"content_type":CONTENT_TYPES,"authority":AUTHORITY,"freshness":FRESHNESS,"time_sensitivity":TIME_SENSITIVITY,"personal_data_risk":RISK,"recommended_action":ACTIONS}
    for name,values in allowed.items():
        if value[name] not in values:raise ValueError(f"{name}非法: {value[name]}")
    for name in ("contains_actionable_information","possible_duplicate","possible_conflict"):
        if not isinstance(value[name],bool):raise ValueError(f"{name}必须是布尔值")
    if not isinstance(value["reason"],str) or not value["reason"].strip():raise ValueError("reason不能为空")
    if not isinstance(value["subcategory"],str) or not value["subcategory"].strip():raise ValueError("subcategory不能为空")
    return value
