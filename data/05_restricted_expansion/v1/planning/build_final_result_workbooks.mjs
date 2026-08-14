import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const base=String.raw`D:\python_projects\tsinghua_ai\data_second\restricted_expansion_v1`;
const preview=path.join(base,"_workbook_previews"); await fs.mkdir(preview,{recursive:true});
const specs=[
 {out:path.join(base,"safety_gate","private_sensitive_gate_results.xlsx"),title:"Private / Sensitive Gate Results",sheet:"Safety Gate",json:path.join(base,"safety_gate","_restricted_safety_rows.json"),cols:["restricted_id","seed_id","title","url","private_sensitive_status","reason","source_file"]},
 {out:path.join(base,"quality_gate","restricted_quality_gate_results.xlsx"),title:"Restricted Quality Gate Results",sheet:"Quality Gate",json:path.join(base,"quality_gate","_restricted_qg_rows.json"),cols:["restricted_id","title","url","category","private_sensitive_status","quality_class","diagnostic_reason","duplicate_status","duplicate_of","quality_gate_pass","source_file","actual_content_hash","hash_match"]},
 {out:path.join(base,"candidates","restricted_expansion_v1_all.xlsx"),title:"Restricted Expansion V1 — All Candidates",sheet:"All",json:path.join(base,"candidates","_restricted_all_rows.json"),cols:["restricted_id","title","url","domain","system_source","discovery_category","auth_required","auth_method_type","private_sensitive_status","quality_class","content_hash","category","content_type","topic_relevance","time_status","v3_2_action","v3_2_reject_type","reason","data_status","source_file"]},
 {out:path.join(base,"candidates","restricted_approved_candidates.xlsx"),title:"Restricted Approved Candidates",sheet:"Approved",json:path.join(base,"candidates","_restricted_approved_rows.json"),cols:["restricted_id","title","url","category","content_type","topic_relevance","time_status","v3_2_action","data_status","source_file","content_hash","reason"]},
 {out:path.join(base,"candidates","restricted_review_candidates.xlsx"),title:"Restricted Review Candidates",sheet:"Review",json:path.join(base,"candidates","_restricted_review_rows.json"),cols:["restricted_id","title","url","category","content_type","topic_relevance","time_status","v3_2_action","data_status","source_file","content_hash","reason"]},
];
for(const s of specs){
 const rows=JSON.parse(await fs.readFile(s.json,"utf8")); const wb=Workbook.create();const ws=wb.worksheets.add(s.sheet);ws.showGridLines=false;const end=col(s.cols.length);
 ws.getRange(`A1:${end}1`).merge();ws.getRange("A1").values=[[s.title]];ws.getRange(`A2:${end}2`).merge();ws.getRange("A2").values=[[`${rows.length} rows · candidate status · not production`]];
 ws.getRange(`A1:${end}1`).format={fill:"#16324F",font:{color:"#FFFFFF",bold:true,size:15},rowHeight:28};ws.getRange(`A2:${end}2`).format={fill:"#E8F1F5",font:{color:"#172B3A",italic:true},rowHeight:22};
 ws.getRange(`A4:${end}4`).values=[s.cols];ws.getRange(`A4:${end}4`).format={fill:"#1F7A8C",font:{color:"#FFFFFF",bold:true},wrapText:true,rowHeight:30,borders:{preset:"all",style:"thin",color:"#D8E2E8"}};
 if(rows.length){const m=rows.map(r=>s.cols.map(c=>r[c]??""));ws.getRange(`A5:${end}${4+m.length}`).values=m;ws.getRange(`A5:${end}${4+m.length}`).format={font:{color:"#172B3A",size:9},wrapText:true,verticalAlignment:"top",borders:{preset:"all",style:"thin",color:"#D8E2E8"}};const t=ws.tables.add(`A4:${end}${4+m.length}`,true,`T_${s.sheet.replace(/\W/g,"_")}`);t.style="TableStyleMedium2";}else{ws.getRange(`A5:${end}5`).merge();ws.getRange("A5").values=[["0 rows"]];ws.getRange(`A5:${end}5`).format={fill:"#F4F7F9",font:{italic:true,color:"#526776"}};}
 ws.freezePanes.freezeRows(4);ws.getUsedRange().format.autofitColumns();for(let i=1;i<=s.cols.length;i++){const n=s.cols[i-1];ws.getRange(`${col(i)}:${col(i)}`).format.columnWidthPx=["title","url","reason","source_file"].includes(n)?280:150;}
 const png=await wb.render({sheetName:s.sheet,range:`A1:${end}${Math.min(18,Math.max(5,4+rows.length))}`,scale:1,format:"png"});await fs.writeFile(path.join(preview,path.basename(s.out,".xlsx")+".png"),new Uint8Array(await png.arrayBuffer()));
 const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},maxChars:2000});await fs.writeFile(path.join(preview,path.basename(s.out,".xlsx")+".errors.json"),JSON.stringify(errors,null,2));
 const x=await SpreadsheetFile.exportXlsx(wb);await x.save(s.out);console.log(JSON.stringify({output:s.out,rows:rows.length}));
}
function col(n){let s="";while(n>0){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26)}return s}
