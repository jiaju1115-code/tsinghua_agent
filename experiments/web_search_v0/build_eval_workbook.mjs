import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const rows = [
  ["A01","CAMPUS_PUBLIC","清华大学最新本科生奖助学金通知","官方清华来源","freshness; official"],
  ["A02","CAMPUS_PUBLIC","清华校车什么时候发车？","官方清华来源","source-gap transport"],
  ["A03","CAMPUS_PUBLIC","清华大学校园出入管理最新规定","官方清华来源","freshness"],
  ["A04","CAMPUS_PUBLIC","清华大学图书馆开放时间","官方清华来源","library"],
  ["A05","CAMPUS_PUBLIC","清华本科生选课通知","官方清华来源","academic affairs"],
  ["A06","CAMPUS_PUBLIC","清华大学学生医疗服务说明","官方清华来源","student service"],
  ["A07","CAMPUS_PUBLIC","清华大学近期校园活动通知","官方清华来源","events"],
  ["A08","CAMPUS_PUBLIC","清华大学校历","官方清华来源","calendar"],
  ["A09","CAMPUS_PUBLIC","清华大学宿舍服务联系方式","官方清华来源","student service"],
  ["A10","CAMPUS_PUBLIC","清华大学奖学金申请流程","官方清华来源","policy"],
  ["B01","ACADEMIC_RETRIEVAL","计算 ∫x e^x dx，需要哪些方法和公式？","分部积分法与公式","no direct answer"],
  ["B02","ACADEMIC_RETRIEVAL","设X服从参数λ的泊松分布，求E(X²)。","期望、方差和二阶矩公式","no direct answer"],
  ["B03","ACADEMIC_RETRIEVAL","如何判断矩阵是否可对角化？","特征值、特征向量与可对角化定理","linear algebra"],
  ["B04","ACADEMIC_RETRIEVAL","斜面上物体的受力和加速度如何分析？","牛顿第二定律和受力分析","physics"],
  ["B05","ACADEMIC_RETRIEVAL","证明级数收敛通常要用哪些判别法？","比较、比值、根值判别法","calculus"],
  ["B06","ACADEMIC_RETRIEVAL","OLS估计量无偏需要什么条件？","OLS假设与无偏性推导","econometrics"],
  ["B07","ACADEMIC_RETRIEVAL","归并排序的时间复杂度怎样推导？","递推式与渐近复杂度","algorithms"],
  ["B08","ACADEMIC_RETRIEVAL","如何求随机变量函数的分布？","变量变换法与CDF方法","probability"],
  ["B09","ACADEMIC_RETRIEVAL","需求弹性如何计算和解释？","弹性定义与微分方法","economics"],
  ["B10","ACADEMIC_RETRIEVAL","拉格朗日乘数法解决约束极值的步骤？","一阶条件、拉格朗日函数","math"],
  ["C01","GENERAL_WEB","2026年人工智能领域近期有哪些重要公开进展？","可信官方或主流来源","current"],
  ["C02","GENERAL_WEB","OpenAI 最新产品公告是什么？","官方公司来源","current"],
  ["C03","GENERAL_WEB","今天北京天气预报如何？","权威公共来源","current"],
  ["C04","GENERAL_WEB","当前国际空间站有哪些公开任务？","官方航天机构来源","current"],
  ["C05","GENERAL_WEB","最近有哪些重要网络安全漏洞公告？","官方安全公告","current"],
  ["C06","GENERAL_WEB","2026年诺贝尔奖公布了吗？","官方来源","current"],
  ["C07","GENERAL_WEB","当前中国高铁票务规则有哪些公开变化？","官方机构来源","current"],
  ["C08","GENERAL_WEB","Python 最新稳定版本是什么？","官方文档","current"],
  ["C09","GENERAL_WEB","近期全球气候报告有哪些主要结论？","国际机构来源","current"],
  ["C10","GENERAL_WEB","目前主流浏览器的Web标准支持情况如何？","官方技术文档","current"]
];
const wb=Workbook.create(); const s=wb.worksheets.add("Evaluation Set"); s.showGridLines=false;
s.getRange("A1:E1").merge(); s.getRange("A1").values=[["Web Search V0 独立评测集（30题）"]];
s.getRange("A1:E1").format={fill:"#0F4C5C",font:{bold:true,color:"#FFFFFF",size:16},horizontalAlignment:"center"}; s.getRange("A2:E2").values=[["ID","Expected Mode","Query","Expected Knowledge / Source","Notes"]];
s.getRange(`A3:E${rows.length+2}`).values=rows;
s.getRange("A2:E2").format={fill:"#DDEFF2",font:{bold:true,color:"#0F3340"}}; s.getRange(`A2:E${rows.length+2}`).format.borders={preset:"outside",style:"thin",color:"#B8CDD3"};
s.getRange(`A3:E${rows.length+2}`).format.wrapText=true; s.getRange("A:A").format.columnWidth=11; s.getRange("B:B").format.columnWidth=22; s.getRange("C:C").format.columnWidth=42; s.getRange("D:D").format.columnWidth=35; s.getRange("E:E").format.columnWidth=22; s.getRange("1:1").format.rowHeight=28; s.freezePanes.freezeRows(2);
const out="evaluation"; await fs.mkdir(out,{recursive:true}); const x=await SpreadsheetFile.exportXlsx(wb); await x.save(`${out}/web_search_v0_eval_set.xlsx`);
const image=await wb.render({sheetName:"Evaluation Set",range:"A1:E32",scale:1.2,format:"png"}); await fs.writeFile(`${out}/web_search_v0_eval_set_preview.png`,new Uint8Array(await image.arrayBuffer()));
console.log((await wb.inspect({kind:"table",range:"Evaluation Set!A1:E8",include:"values",tableMaxRows:8,tableMaxCols:5})).ndjson);
