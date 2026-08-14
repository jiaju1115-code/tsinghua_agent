HIGH = ("新生","报到","入学","迎新","校园卡","一卡通","校园网","vpn","邮箱","统一身份认证","图书馆","借阅","校医院","后勤","食堂","宿舍","快递","学生事务","办事","服务","指南","faq","常见问题","体育馆","场馆","预约","校园交通","校车","报修","失物招领","证明","学籍","注册","安全","保卫")
LOW = ("科研","论文","实验室","学术会议","科研成果","人物采访","教授新闻","校友新闻")

def priority_score(url: str, text: str = "") -> int:
    hay=(url+" "+text).lower()
    service_hosts=("its.tsinghua.edu.cn","itc.tsinghua.edu.cn","lib.tsinghua.edu.cn","xyy.tsinghua.edu.cn","thsports.tsinghua.edu.cn","peace.tsinghua.edu.cn")
    host_bonus=30 if any(h in hay for h in service_hosts) else 0
    return host_bonus+10*sum(k.lower() in hay for k in HIGH)-4*sum(k.lower() in hay for k in LOW)
