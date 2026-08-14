import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "file:///C:/Users/%E6%9E%97%E5%AE%87%E8%BD%A9/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const base = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_blind_test_v1";
const specs = [
  { json: "manifest/blind_test_exclusion_list.json", xlsx: "manifest/blind_test_exclusion_list.xlsx", sheet: "历史排除", title: "Blind Test V1 历史调参样本排除名单", kind: "internal" },
  { json: "manifest/blind_candidate_pool.json", xlsx: "manifest/blind_candidate_pool.xlsx", sheet: "候选池", title: "Blind Test V1 排除后候选池", kind: "internal" },
  { json: "samples/blind_test_v1_sample_manifest.json", xlsx: "samples/blind_test_v1_sample_manifest.xlsx", sheet: "样本清单", title: "Blind Test V1 50条内部样本清单", kind: "internal" },
  { json: "human_label/blind_test_v1_human_label.json", xlsx: "human_label/blind_test_v1_human_label.xlsx", sheet: "人工标注", title: "Prompt V3.2 Blind Test V1 人工标注表", kind: "human" },
];

const colName = n => { let s=""; while(n){ n--; s=String.fromCharCode(65+n%26)+s; n=Math.floor(n/26); } return s; };
const widthFor = (h, kind) => {
  if (/^(id|blind_id|original_id)$/.test(h)) return 18;
  if (/url|content_file/.test(h)) return 42;
  if (/title/.test(h)) return 34;
  if (h === "cleaned_content") return 80;
  if (/reason|note/.test(h)) return 44;
  if (/action|category|type|relevance|status|method|group|coverage/.test(h)) return 22;
  if (/sha256/.test(h)) return 38;
  return kind === "human" ? 20 : 18;
};

async function build(spec, index) {
  const rows=JSON.parse(await fs.readFile(path.join(base,spec.json),"utf8"));
  const headers=Object.keys(rows[0]??{}); const last=colName(headers.length); const wb=Workbook.create(); const sheet=wb.worksheets.add(spec.sheet); sheet.showGridLines=false;
  sheet.getRange(`A1:${last}1`).format={fill:"#123B4A",font:{name:"Microsoft YaHei",size:16,bold:true,color:"#FFFFFF"},rowHeight:34}; sheet.getRange("A1").values=[[spec.title]];
  sheet.getRange(`A2:${last}2`).format={fill:"#E6F2F4",font:{name:"Microsoft YaHei",size:9,color:"#34515A"},rowHeight:23};
  sheet.getRange("A2").values=[[spec.kind==="human"?"请先阅读标注指南；所有 human 字段由人工填写，表内未展示历史 AI 审核结果。":`内部抽样审计文件｜生成日期 2026-08-13｜共 ${rows.length} 条`]];
  const matrix=[headers,...rows.map(r=>headers.map(h=>r[h]??""))]; sheet.getRangeByIndexes(2,0,matrix.length,headers.length).values=matrix;
  sheet.getRange(`A3:${last}3`).format={fill:"#167C8C",font:{name:"Microsoft YaHei",size:10,bold:true,color:"#FFFFFF"},horizontalAlignment:"center",verticalAlignment:"center",wrapText:true,rowHeight:36,borders:{bottom:{style:"medium",color:"#123B4A"}}};
  const body=sheet.getRangeByIndexes(3,0,rows.length,headers.length); body.format={font:{name:"Microsoft YaHei",size:9,color:"#1F2937"},verticalAlignment:"top",wrapText:true,rowHeight:spec.kind==="human"?84:48,borders:{insideHorizontal:{style:"thin",color:"#E5E7EB"}}};
  headers.forEach((h,c)=>{sheet.getRangeByIndexes(2,c,rows.length+1,1).format.columnWidth=widthFor(h,spec.kind);});
  const table=sheet.tables.add(`A3:${last}${rows.length+3}`,true,`BlindV1_${index}`); table.style="TableStyleMedium2"; table.showFilterButton=true;
  const groupCol=headers.indexOf("source_group"); if(groupCol>=0){const rg=sheet.getRangeByIndexes(3,groupCol,rows.length,1);rg.conditionalFormats.add("containsText",{text:"random",format:{fill:"#DBEAFE",font:{color:"#1D4ED8",bold:true}}});rg.conditionalFormats.add("containsText",{text:"targeted",format:{fill:"#F3E8FF",font:{color:"#7E22CE",bold:true}}});}
  if(spec.kind==="human"){
    for(const h of ["human_action","human_category","human_reject_type","human_topic_relevance","human_time_status","human_valid_until","human_note"]){const c=headers.indexOf(h);sheet.getRangeByIndexes(3,c,rows.length,1).format={fill:"#FFF7ED",font:{name:"Microsoft YaHei",size:9,color:"#7C2D12"},verticalAlignment:"top",wrapText:true,borders:{insideHorizontal:{style:"thin",color:"#FED7AA"}}};}
    const setValidation=(h,values)=>{const c=headers.indexOf(h);sheet.getRangeByIndexes(3,c,rows.length,1).dataValidation={rule:{type:"list",values}};};
    setValidation("human_action",["approve","review","reject"]); setValidation("human_reject_type",["topic_irrelevant","expired_event","other"]); setValidation("human_topic_relevance",["high","medium","low"]); setValidation("human_time_status",["evergreen","active_time_bound","expired","historical_but_valuable","unknown"]);
  }
  sheet.freezePanes.freezeRows(3); sheet.freezePanes.freezeColumns(Math.min(3,headers.length));
  const inspect=await wb.inspect({kind:"region",sheetId:spec.sheet,range:`A1:${colName(Math.min(headers.length,12))}8`,maxChars:5000}); await fs.writeFile(path.join(base,`audit/workbook_${index}_inspect.ndjson`),inspect.ndjson,"utf8");
  const preview=await wb.render({sheetName:spec.sheet,range:`A1:${colName(Math.min(headers.length,12))}9`,scale:1,format:"png"}); await fs.writeFile(path.join(base,`audit/workbook_${index}_preview.png`),new Uint8Array(await preview.arrayBuffer()));
  if(spec.kind==="human"){
    const humanPreview=await wb.render({sheetName:spec.sheet,range:"J1:Q9",scale:1.25,format:"png"});
    await fs.writeFile(path.join(base,`audit/workbook_${index}_human_fields_preview.png`),new Uint8Array(await humanPreview.arrayBuffer()));
  }
  const out=path.join(base,spec.xlsx); await fs.mkdir(path.dirname(out),{recursive:true}); const xlsx=await SpreadsheetFile.exportXlsx(wb); await xlsx.save(out);
  return {file:spec.xlsx,rows:rows.length,columns:headers.length,formulaCount:0};
}
const verification=[];for(let i=0;i<specs.length;i++)verification.push(await build(specs[i],i+1));await fs.writeFile(path.join(base,"audit/workbook_verification.json"),JSON.stringify(verification,null,2),"utf8");console.log(JSON.stringify(verification));
