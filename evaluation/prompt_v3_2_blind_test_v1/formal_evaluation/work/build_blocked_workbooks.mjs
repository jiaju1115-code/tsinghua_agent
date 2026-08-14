import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_blind_test_v1/formal_evaluation";
const specs = [
  {json:"results/blind_test_v1_results.json",xlsx:"results/blind_test_v1_results.xlsx",sheet:"正式对比",title:"Prompt V3.2 Blind Test V1｜正式结果（API 阻塞）",empty:false},
  {json:"results/blind_test_v1_disagreements.json",xlsx:"results/blind_test_v1_disagreements.xlsx",sheet:"Action分歧",title:"Prompt V3.2 Blind Test V1｜Action 分歧（未评估）",empty:true,headers:["blind_id","title","human_action","v3_2_action","human_topic_relevance","v3_2_topic_relevance","human_reject_type","v3_2_reject_type","human_note","v3_2_reason","disagreement_type","probable_cause"]},
  {json:"results/human_label_questions.json",xlsx:"results/human_label_questions.xlsx",sheet:"人工标签疑问",title:"Prompt V3.2 Blind Test V1｜人工标签疑问（未评估）",empty:true,headers:["blind_id","title","human_action","v3_2_action","human_note","question_reason","suggested_review_point"]},
];

const colName=n=>{let s="";while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);}return s;};
const widthFor=h=>{
  if(/^(blind_id|original_id)$/.test(h)) return 17;
  if(h==="title") return 34;
  if(h==="url") return 42;
  if(/reason|note|question|cause/.test(h)) return 42;
  if(/category|content_type|topic_relevance|reject_type|time_status|disagreement/.test(h)) return 23;
  return 18;
};

async function build(spec,index){
  const rows=JSON.parse(await fs.readFile(path.join(base,spec.json),"utf8"));
  const headers=rows.length?Object.keys(rows[0]):spec.headers;
  const last=colName(headers.length);
  const wb=Workbook.create();
  const sheet=wb.worksheets.add(spec.sheet); sheet.showGridLines=false;
  const titleLast=colName(Math.min(headers.length,12));
  sheet.getRange(`A1:${titleLast}1`).merge(); sheet.getRange("A1").values=[[spec.title]];
  sheet.getRange(`A1:${last}1`).format={fill:"#7F1D1D",font:{name:"Microsoft YaHei",size:16,bold:true,color:"#FFFFFF"},rowHeight:34,verticalAlignment:"center"};
  sheet.getRange(`A2:${titleLast}2`).merge(); sheet.getRange("A2").values=[["EVALUATION_BLOCKED：上游 chat completion 接口超时，AI 字段为空，禁止将本文件解释为模型性能结果。"]];
  sheet.getRange(`A2:${last}2`).format={fill:"#FEF2F2",font:{name:"Microsoft YaHei",size:10,bold:true,color:"#991B1B"},rowHeight:28,verticalAlignment:"center"};
  sheet.getRangeByIndexes(2,0,1,headers.length).values=[headers];
  sheet.getRange(`A3:${last}3`).format={fill:"#334155",font:{name:"Microsoft YaHei",size:9,bold:true,color:"#FFFFFF"},wrapText:true,rowHeight:34,horizontalAlignment:"center",verticalAlignment:"center"};
  if(rows.length){
    const matrix=rows.map(r=>headers.map(h=>r[h]??""));
    sheet.getRangeByIndexes(3,0,rows.length,headers.length).values=matrix;
    const body=sheet.getRangeByIndexes(3,0,rows.length,headers.length);
    body.format={font:{name:"Microsoft YaHei",size:9,color:"#1F2937"},verticalAlignment:"top",wrapText:true,rowHeight:42,borders:{insideHorizontal:{style:"thin",color:"#E5E7EB"}}};
    const statusCol=headers.indexOf("disagreement_type");
    if(statusCol>=0) sheet.getRangeByIndexes(3,statusCol,rows.length,1).format={fill:"#FEF3C7",font:{name:"Microsoft YaHei",size:9,bold:true,color:"#92400E"},wrapText:true};
    const firstAi=headers.indexOf("v3_2_action"), lastAi=headers.indexOf("v3_2_reason");
    if(firstAi>=0&&lastAi>=firstAi) sheet.getRangeByIndexes(3,firstAi,rows.length,lastAi-firstAi+1).format={fill:"#F8FAFC",font:{name:"Microsoft YaHei",size:9,color:"#64748B"},wrapText:true};
    const table=sheet.tables.add(`A3:${last}${rows.length+3}`,true,`BlindBlocked_${index}`); table.style="TableStyleMedium2"; table.showFilterButton=true;
  }else{
    sheet.getRange(`A4:${last}5`).merge(); sheet.getRange("A4").values=[["无可评估记录：AI 原始结果为 0 条。"]];
    sheet.getRange(`A4:${last}5`).format={fill:"#FFF7ED",font:{name:"Microsoft YaHei",size:12,bold:true,color:"#9A3412"},horizontalAlignment:"center",verticalAlignment:"center"};
  }
  headers.forEach((h,c)=>sheet.getRangeByIndexes(2,c,Math.max(2,rows.length+1),1).format.columnWidth=widthFor(h));
  sheet.freezePanes.freezeRows(3); sheet.freezePanes.freezeColumns(Math.min(3,headers.length));
  const inspect=await wb.inspect({kind:"region",sheetId:spec.sheet,range:`A1:${colName(Math.min(headers.length,12))}${rows.length?8:5}`,maxChars:4000});
  await fs.writeFile(path.join(base,`audit/workbook_${index}_inspect.ndjson`),inspect.ndjson,"utf8");
  const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:50},summary:"formula errors"});
  await fs.writeFile(path.join(base,`audit/workbook_${index}_formula_errors.ndjson`),errors.ndjson,"utf8");
  const preview=await wb.render({sheetName:spec.sheet,range:`A1:${colName(Math.min(headers.length,12))}${rows.length?9:5}`,scale:1,format:"png"});
  await fs.writeFile(path.join(base,`audit/workbook_${index}_preview.png`),new Uint8Array(await preview.arrayBuffer()));
  const xlsx=await SpreadsheetFile.exportXlsx(wb); await xlsx.save(path.join(base,spec.xlsx));
  return {file:spec.xlsx,rows:rows.length,columns:headers.length,status:"EVALUATION_BLOCKED"};
}

const verification=[];
for(let i=0;i<specs.length;i++) verification.push(await build(specs[i],i+1));
await fs.writeFile(path.join(base,"audit/workbook_verification.json"),JSON.stringify(verification,null,2),"utf8");
console.log(JSON.stringify(verification));
