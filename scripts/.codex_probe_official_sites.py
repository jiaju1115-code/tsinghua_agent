import re, subprocess
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup, UnicodeDammit

URLS = [
    "https://its.tsinghua.edu.cn/",
    "https://www.is.tsinghua.edu.cn/",
    "https://www.is.tsinghua.edu.cn/IS/Student_Services.htm",
    "https://www.is.tsinghua.edu.cn/GettingStarted.htm",
    "https://www.thsports.tsinghua.edu.cn/",
    "https://www.thsports.tsinghua.edu.cn/cgfw.htm",
    "https://peace.tsinghua.edu.cn/",
    "https://peace.tsinghua.edu.cn/bmfw.htm",
    "https://career.tsinghua.edu.cn/",
    "https://career.tsinghua.edu.cn/js/tzgg.htm",
    "https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww.htm",
    "https://www.tsinghua.edu.cn/yjsy/yjspy/pyyqygd.htm",
    "https://www.tsinghua.edu.cn/jwc/index.htm",
    "https://www.tsinghua.edu.cn/xsb/",
    "https://www.med.tsinghua.edu.cn/",
    "https://www.med.tsinghua.edu.cn/xwdt/tzgg.htm",
    "https://www.med.tsinghua.edu.cn/xyfw.htm",
    "https://www.tsinghua.edu.cn/jwc/dfasdf/ywbl.htm",
    "https://www.thsports.tsinghua.edu.cn/tyss.htm",
    "https://peace.tsinghua.edu.cn/bszn/xyjt.htm",
    "https://peace.tsinghua.edu.cn/bszn/xycg.htm",
    "https://career.tsinghua.edu.cn/xs/zyfd.htm",
    "https://career.tsinghua.edu.cn/xy/zyfz.htm",
]
KEY = re.compile(r"签证|居留|保险|住宿|服务|指南|手续|注册|课程|考试|成绩|学籍|培养|资助|奖学金|助学|就业|职业|档案|户籍|体育|场馆|游泳|预约|交通|停车|通行|校门|医疗|体检|食堂|餐饮|规定|办法|政策|流程|FAQ|Guide|Visa|Residence|Insurance|Accommodation|Service|Scholarship|Career|Employment|Sport|Venue", re.I)

for u in URLS:
    z = subprocess.run(["curl.exe", "-k", "-L", "--http1.1", "--compressed", "--max-time", "30", "-sS", u], capture_output=True)
    h = UnicodeDammit(z.stdout, is_html=True).unicode_markup or z.stdout.decode(errors="replace")
    s = BeautifulSoup(h, "lxml")
    print("\n###", u, "bytes", len(z.stdout), "title", s.title.get_text(" ", strip=True) if s.title else "")
    seen = set()
    for a in s.find_all("a", href=True):
        t = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()
        v = urljoin(u, a["href"])
        if not t or (t, v) in seen or not KEY.search(t):
            continue
        seen.add((t, v))
        print(t[:100], "=>", v[:220])
