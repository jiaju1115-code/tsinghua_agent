import tempfile
import unittest
from pathlib import Path
from utils.url_utils import normalize_url,is_allowed
from crawler.state import CrawlState
from crawler.parser import content_quality_gate,detect_page,parse_html
from crawler.prioritizer import priority_score
from crawler.similarity import simhash,similarity
from portal.safety import private_reason,portal_priority

class CoreTests(unittest.TestCase):
    def test_url_normalization(self):
        self.assertEqual(normalize_url("/a/?utm_source=x#top","https://WWW.TSINGHUA.EDU.CN/",{"utm_source"}),"https://www.tsinghua.edu.cn/a")
        self.assertTrue(is_allowed("https://lib.tsinghua.edu.cn/a","tsinghua.edu.cn"))
        self.assertFalse(is_allowed("https://eviltsinghua.edu.cn/a","tsinghua.edu.cn"))
    def test_parser(self):
        html="<html><head><title>服务指南</title></head><body><nav>菜单</nav><article><h1>服务指南</h1><p>"+("办理材料和服务时间。"*30)+"</p><a href='/a.pdf'>表格</a></article></body></html>"
        page=parse_html(html,"https://www.tsinghua.edu.cn/x",set())
        self.assertIn("服务指南",page.markdown); self.assertEqual(page.attachments[0][2],"pdf")
        self.assertEqual(page.links,[])
    def test_unknown_widget_uses_trafilatura_not_body_fallback(self):
        html="<html><body><div class='unknown-widget'>"+("校园服务办理材料、时间和地点。"*40)+"</div></body></html>"
        page=parse_html(html,"https://info.tsinghua.edu.cn/x",set())
        self.assertTrue(page.quality.passed)
        self.assertEqual(page.extraction_method,"trafilatura")
    def test_site_selector_beats_navigation(self):
        html="<html><head><title>安全检查</title></head><body><nav>"+("学校概况 教育教学 科学研究 联系我们 "*30)+"</nav><div id='vsb_content'><div class='v_news_content'><p>"+("信息化技术中心开展安全检查，覆盖办公室和机房等重点区域。"*8)+"</p></div></div></body></html>"
        page=parse_html(html,"https://www.itc.tsinghua.edu.cn/info/1004/2206.htm",set())
        self.assertTrue(page.quality.passed)
        self.assertEqual(page.extraction_method,"site_selector")
        self.assertEqual(page.selector_used,"#vsb_content .v_news_content")
        self.assertNotIn("学校概况",page.plain_text)
    def test_list_page_is_not_detail(self):
        html="<html><head><title>招聘信息</title></head><body><main><h1>招聘信息</h1><ul>"+"".join(f"<li><a href='/job/{i}'>岗位{i}招聘</a></li>" for i in range(12))+"</ul><p>共12条 首页 上页 下页 尾页</p></main></body></html>"
        page=parse_html(html,"https://www.itc.tsinghua.edu.cn/zpxx.htm",set())
        self.assertEqual(page.quality.content_quality_class,"list_page")
        self.assertFalse(page.quality.passed)
        self.assertEqual(len(page.links),12)
    def test_loading_placeholder_fails_gate(self):
        q=content_quality_gate("# 新闻详情\n\n读取内容中，请等待...","新闻详情","https://lib.tsinghua.edu.cn/info/1/2.htm")
        self.assertFalse(q.passed);self.assertEqual(q.content_quality_class,"extraction_failed")
    def test_auth(self): self.assertEqual(detect_page("<title>统一身份认证</title><form>账号密码</form>","https://id.tsinghua.edu.cn/login"),"login_required")
    def test_state_resume(self):
        with tempfile.TemporaryDirectory() as d:
            s=CrawlState(Path(d)/"x.db"); s.add_url("https://www.tsinghua.edu.cn/",0,None,"t"); self.assertIsNotNone(s.claim()); s.close()
            s=CrawlState(Path(d)/"x.db"); s.recover(); self.assertIsNotNone(s.claim()); s.close()
    def test_priority(self):
        self.assertGreater(priority_score("https://x.tsinghua.edu.cn/新生/校园卡"),priority_score("https://x.tsinghua.edu.cn/科研/论文"))
    def test_similarity(self):
        a=simhash("校园卡办理服务指南，办理地点在服务大厅。"*10);b=simhash("校园卡办理服务指南，办理地点在服务大厅。"*10)
        self.assertEqual(similarity(a,b),1.0)
    def test_portal_private_deny(self):
        self.assertIsNotNone(private_reason("https://info.tsinghua.edu.cn/my","我的成绩"))
        self.assertLess(portal_priority("https://info.tsinghua.edu.cn/my","个人中心"),0)
        self.assertLess(portal_priority("https://info.tsinghua.edu.cn/x","科研项目采购通知"),portal_priority("https://info.tsinghua.edu.cn/x","校园卡服务指南"))
        self.assertIsNotNone(private_reason(title="普通页面",text="姓名：张三 学号：2026123456"))
        self.assertIsNotNone(private_reason(title="普通页面",text="我的课表"))

if __name__=="__main__": unittest.main()
