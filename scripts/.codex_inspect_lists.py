import subprocess,re
from bs4 import BeautifulSoup,UnicodeDammit
urls=[
"https://learning.tsinghua.edu.cn/xwgg/tzgg.htm",
"https://www.tsinghua.edu.cn/xsb/",
"https://www.tsinghua.edu.cn/xssqglfwzx/",
"https://www.tsinghua.edu.cn/ysfwzx/",
"https://career.tsinghua.edu.cn/",
"https://www.tsinghua.edu.cn/yjsy/yjspy/pyyqygd.htm",
"https://www.tsinghua.edu.cn/zjqh/xxgk1/gksxx/xsglfww/xsjxj_zxj_xfjm_zxdk.htm"]
for i,u in enumerate(urls):
 p=subprocess.run(["curl.exe","-k","-L","--max-time","30","-sS",u],capture_output=True)
 h=UnicodeDammit(p.stdout,is_html=True).unicode_markup or p.stdout.decode(errors="ignore");s=BeautifulSoup(h,"lxml")
 print("\n###",u,"title=",s.title.get_text(" ",strip=True) if s.title else "")
 seen=set()
 for a in s.find_all("a",href=True):
  t=re.sub(r"\s+"," ",a.get_text(" ",strip=True));v=a["href"]
  if (t,v) in seen:continue
  seen.add((t,v))
  if re.search(r"下一页|尾页|通知|规定|办法|指南|手续|服务|住宿|食堂|奖|助|就业|档案|课程|学籍|培养",t) or re.search(r"/\d+\.htm|/[1-9]\d*\.htm",v): print(t[:80],"=>",v[:180])
