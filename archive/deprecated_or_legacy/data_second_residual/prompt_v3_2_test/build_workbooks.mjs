import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_test";
const specs = [
  { json: "analysis/v3_2_topic_analysis.json", xlsx: "analysis/v3_2_topic_analysis.xlsx", sheet: "主题预分析", title: "Prompt V3.2 主题相关性预分析" },
  { json: "results/prompt_v3_2_30_results.json", xlsx: "results/prompt_v3_2_30_results.xlsx", sheet: "V3.2 30条回归", title: "Prompt V3.2 固定 30 条回归结果" },
];

const colName = n => { let s=""; while(n){ n--; s=String.fromCharCode(65+n%26)+s; n=Math.floor(n/26); } return s; };
const widthFor = h => {
  if (h === "id") return 18; if (h === "title") return 34; if (h === "url") return 44;
  if (/reason|evidence|note|question/.test(h)) return 47; if (/action|relevance|reject_type|content_type|time_status|category/.test(h)) return 23;
  if (/valid_/.test(h)) return 16; return 20;
};

async function build(spec, index) {
  const rows = JSON.parse(await fs.readFile(path.join(base, spec.json), "utf8"));
  const headers = Object.keys(rows[0] ?? {}); const last = colName(headers.length);
  const wb = Workbook.create(); const sheet = wb.worksheets.add(spec.sheet); sheet.showGridLines = false;
  sheet.getRange(`A1:${last}1`).format = { fill: "#123B4A", font: { name: "Microsoft YaHei", size: 16, bold: true, color: "#FFFFFF" }, rowHeight: 34 };
  sheet.getRange("A1").values = [[spec.title]];
  sheet.getRange(`A2:${last}2`).format = { fill: "#E6F2F4", font: { name: "Microsoft YaHei", size: 9, color: "#34515A" }, rowHeight: 23 };
  sheet.getRange("A2").values = [[`固定 30 条样本｜生成日期 2026-08-12｜共 ${rows.length} 条`]];
  const matrix = [headers, ...rows.map(r => headers.map(h => r[h] ?? ""))];
  sheet.getRangeByIndexes(2, 0, matrix.length, headers.length).values = matrix;
  sheet.getRange(`A3:${last}3`).format = { fill: "#167C8C", font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, rowHeight: 34, borders: { bottom: { style: "medium", color: "#123B4A" } } };
  sheet.getRangeByIndexes(3, 0, rows.length, headers.length).format = { font: { name: "Microsoft YaHei", size: 9, color: "#1F2937" }, verticalAlignment: "top", wrapText: true, rowHeight: 48, borders: { insideHorizontal: { style: "thin", color: "#E5E7EB" } } };
  headers.forEach((h,c)=>{ sheet.getRangeByIndexes(2,c,rows.length+1,1).format.columnWidth=widthFor(h); });
  const table=sheet.tables.add(`A3:${last}${rows.length+3}`,true,`PromptV32_${index}`); table.style="TableStyleMedium2"; table.showFilterButton=true;
  for (const h of ["V2","V3","V3_1","V3_2","human","human_action"]) {
    const c=headers.indexOf(h); if(c<0) continue; const rg=sheet.getRangeByIndexes(3,c,rows.length,1);
    rg.conditionalFormats.add("containsText",{text:"approve",format:{fill:"#DCFCE7",font:{color:"#166534",bold:true}}});
    rg.conditionalFormats.add("containsText",{text:"review",format:{fill:"#FEF3C7",font:{color:"#92400E",bold:true}}});
    rg.conditionalFormats.add("containsText",{text:"reject",format:{fill:"#FEE2E2",font:{color:"#991B1B",bold:true}}});
  }
  for (const h of ["topic_relevance","proposed_topic_relevance"]) {
    const c=headers.indexOf(h); if(c<0) continue; const rg=sheet.getRangeByIndexes(3,c,rows.length,1);
    rg.conditionalFormats.add("containsText",{text:"high",format:{fill:"#DCFCE7",font:{color:"#166534",bold:true}}});
    rg.conditionalFormats.add("containsText",{text:"medium",format:{fill:"#FEF3C7",font:{color:"#92400E",bold:true}}});
    rg.conditionalFormats.add("containsText",{text:"low",format:{fill:"#FEE2E2",font:{color:"#991B1B",bold:true}}});
  }
  for (const h of ["reject_type","proposed_reject_type"]) {
    const c=headers.indexOf(h); if(c<0) continue; const rg=sheet.getRangeByIndexes(3,c,rows.length,1);
    rg.conditionalFormats.add("containsText",{text:"topic_irrelevant",format:{fill:"#E5E7EB",font:{color:"#374151",bold:true}}});
    rg.conditionalFormats.add("containsText",{text:"expired_event",format:{fill:"#FEE2E2",font:{color:"#991B1B",bold:true}}});
  }
  sheet.freezePanes.freezeRows(3); sheet.freezePanes.freezeColumns(Math.min(3,headers.length));
  const inspect=await wb.inspect({kind:"region",sheetId:spec.sheet,range:`A1:${last}8`,maxChars:5000});
  await fs.writeFile(path.join(base,`audit/workbook_${index}_inspect.ndjson`),inspect.ndjson,"utf8");
  const preview=await wb.render({sheetName:spec.sheet,range:`A1:${colName(Math.min(headers.length,12))}10`,scale:1,format:"png"});
  await fs.writeFile(path.join(base,`audit/workbook_${index}_preview.png`),new Uint8Array(await preview.arrayBuffer()));
  const out=path.join(base,spec.xlsx); await fs.mkdir(path.dirname(out),{recursive:true}); const xlsx=await SpreadsheetFile.exportXlsx(wb); await xlsx.save(out);
  return {file:spec.xlsx,rows:rows.length,columns:headers.length,formulaCount:0};
}
const verification=[]; for(let i=0;i<specs.length;i++) verification.push(await build(specs[i],i+1));
await fs.writeFile(path.join(base,"audit/workbook_verification.json"),JSON.stringify(verification,null,2),"utf8");
console.log(JSON.stringify(verification));
