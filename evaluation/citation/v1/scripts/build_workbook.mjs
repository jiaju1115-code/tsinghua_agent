import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root="D:/python_projects/tsinghua_ai/data_second/citation_pipeline_v1";
const data=JSON.parse(await fs.readFile(path.join(root,"evaluation","workbook_data.json"),"utf8"));
const out=path.join(root,"evaluation","a_vs_citation_pipeline_v1.xlsx");
const qa=path.join(root,"logs","workbook_qa");
await fs.mkdir(qa,{recursive:true});

const wb=Workbook.create();
const summary=wb.worksheets.add("Summary");
const detail=wb.worksheets.add("A vs Pipeline");
const thresholds=wb.worksheets.add("Threshold Sensitivity");
const lists=wb.worksheets.add("Human Lists");
const source=wb.worksheets.add("Metric Source");

summary.showGridLines=false;
summary.getRange("A1:F1").merge(); summary.getRange("A1").values=[["Citation Pipeline V1"]];
summary.getRange("A2:F2").merge(); summary.getRange("A2").values=[["PROVISIONAL_AUTO_EVAL — human-validated citation correctness is N/A"]];
summary.getRange("A4:C4").values=[["Metric","Value","Interpretation"]];
summary.getRange("A5:A13").values=[["Questions"],["Claims"],["Factual claims"],["Claim citation coverage"],["Citation precision proxy"],["A baseline compliance"],["Pipeline compliance"],["Answer preservation"],["Human-validated precision"]];
for(let r=5;r<=13;r++) summary.getRange(`B${r}`).formulas=[[`='Metric Source'!B${r-3}`]];
summary.getRange("C5:C13").values=[["38 frozen questions"],["deterministic claim units"],["eligible for support evaluation"],["supported or partial factual claims"],["assigned citations passing deterministic rules"],["frozen A answer-level metric"],["all factual claims mapped or appropriate refusal"],["body unchanged after marker removal"],["N/A until human review"]];
summary.getRange("A1:F1").format={fill:"#17324D",font:{bold:true,color:"#FFFFFF",size:18},rowHeight:34};
summary.getRange("A2:F2").format={fill:"#FFF4CC",font:{italic:true,color:"#6B4F00"},wrapText:true,rowHeight:28};
summary.getRange("A4:C4").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"}};
summary.getRange("A5:A13").format={fill:"#DCEFF3",font:{bold:true,color:"#0F4C5C"}};
summary.getRange("A:C").format.columnWidth=30; summary.getRange("C:C").format.columnWidth=48;
summary.getRange("B8:B12").format.numberFormat="0.00%";

const headers=["question_id","question","original_answer","cited_answer","original_citation_status","new_citation_status","claim_count","supported_claim_count","partial_claim_count","unsupported_claim_count","citation_count","citation_coverage","citation_precision_proxy","preservation_status","human_citation_correctness","human_claim_support","human_comment"];
const matrix=data.rows.map(r=>headers.map(h=>r[h]));
detail.showGridLines=false;
detail.getRange("A1:Q1").merge(); detail.getRange("A1").values=[["A Baseline vs Citation Pipeline V1 — 38 Questions"]];
detail.getRange("A2:Q2").merge(); detail.getRange("A2").values=[["Yellow columns are blank human-review inputs; no human label contributed to automatic metrics."]];
detail.getRange("A4:Q4").values=[headers]; detail.getRange("A5:Q42").values=matrix;
detail.tables.add("A4:Q42",true,"CitationPipelineTable").style="TableStyleMedium2";
detail.freezePanes.freezeRows(4); detail.freezePanes.freezeColumns(2);
detail.getRange("A1:Q1").format={fill:"#17324D",font:{bold:true,color:"#FFFFFF",size:17},rowHeight:32};
detail.getRange("A2:Q2").format={fill:"#EAF0F6",font:{italic:true,color:"#334155"},wrapText:true,rowHeight:28};
detail.getRange("A4:Q4").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"},wrapText:true,horizontalAlignment:"center",rowHeight:42};
detail.getRange("A5:Q42").format={verticalAlignment:"top",wrapText:true,font:{name:"Microsoft YaHei",size:10}};
for(const c of ["L","M"]) detail.getRange(`${c}5:${c}42`).format.numberFormat="0.00%";
const widths={A:13,B:36,C:48,D:52,E:18,F:18,G:13,H:15,I:15,J:16,K:13,L:16,M:18,N:16,O:22,P:22,Q:38};
for(const [c,w] of Object.entries(widths)) detail.getRange(`${c}:${c}`).format.columnWidth=w;
detail.getRange("O5:Q42").format={fill:"#FFF4CC",font:{color:"#6B4F00"},verticalAlignment:"top",wrapText:true};
detail.getRange("O5:O42").dataValidation={rule:{type:"list",values:["correct","partial","incorrect","uncertain"]}};
detail.getRange("P5:P42").dataValidation={rule:{type:"list",values:["supported","partial","unsupported","conflicting","uncertain"]}};
detail.getRange("F5:F42").conditionalFormats.add("containsText",{text:"COMPLIANT",format:{fill:"#DCFCE7",font:{color:"#166534",bold:true}}});
detail.getRange("N5:N42").conditionalFormats.add("containsText",{text:"FAILED",format:{fill:"#FEE2E2",font:{color:"#991B1B",bold:true}}});

thresholds.showGridLines=false;
thresholds.getRange("A1:E1").merge(); thresholds.getRange("A1").values=[["Threshold Sensitivity — factual claims only"]];
thresholds.getRange("A3:E3").values=[["Threshold","Supported proxy","Unsupported","Eligible factual claims","Coverage proxy"]];
thresholds.getRange(`A4:E${3+data.thresholds.length}`).values=data.thresholds.map(x=>[x.threshold,x.SUPPORTED||0,x.UNSUPPORTED||0,x.eligible_factual_claims,x.coverage_proxy]);
thresholds.getRange("A1:E1").format={fill:"#17324D",font:{bold:true,color:"#FFFFFF",size:16},rowHeight:30};
thresholds.getRange("A3:E3").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"}};
thresholds.getRange("A:E").format.columnWidth=24; thresholds.getRange("A4:A8").format.numberFormat="0.00"; thresholds.getRange("E4:E8").format.numberFormat="0.00%";
thresholds.getRange("A10:E11").merge(); thresholds.getRange("A10").values=[["Thresholds were predeclared. Sensitivity results are descriptive and were not used to tune per-question decisions."]]; thresholds.getRange("A10:E11").format={fill:"#FFF4CC",font:{italic:true,color:"#6B4F00"},wrapText:true};

lists.getRange("A1:B1").values=[["human_citation_correctness","human_claim_support"]];
lists.getRange("A2:A5").values=[["correct"],["partial"],["incorrect"],["uncertain"]];
lists.getRange("B2:B6").values=[["supported"],["partial"],["unsupported"],["conflicting"],["uncertain"]];
lists.getRange("A1:B1").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"}}; lists.getRange("A:B").format.columnWidth=28;

source.showGridLines=false;
source.getRange("A1:B1").values=[["metric","value"]];
source.getRange("A2:B10").values=[["Questions",data.summary.questions],["Claims",data.summary.claims],["Factual claims",data.summary.factual_claims],["Claim citation coverage",data.summary.coverage],["Citation precision proxy",data.summary.precision_proxy],["A baseline compliance",data.summary.baseline_compliance],["Pipeline compliance",data.summary.pipeline_compliance],["Answer preservation",data.summary.preservation],["Human-validated precision",""]];
source.getRange("A1:B1").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"}}; source.getRange("A:B").format.columnWidth=30; source.getRange("B5:B9").format.numberFormat="0.00%";

const inspect=await wb.inspect({kind:"table",range:"'A vs Pipeline'!A1:Q42",include:"values,formulas",tableMaxRows:42,tableMaxCols:17,maxChars:50000});
const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:200},summary:"formula error scan"});
await fs.writeFile(path.join(qa,"workbook.inspect.ndjson"),inspect.ndjson,"utf8"); await fs.writeFile(path.join(qa,"workbook.formula_errors.ndjson"),errors.ndjson,"utf8");
for(const [name,sheetName,range,scale] of [["summary.png","Summary","A1:F14",1.2],["comparison.png","A vs Pipeline","A1:Q12",0.65],["thresholds.png","Threshold Sensitivity","A1:E11",1.1],["human_lists.png","Human Lists","A1:B6",1.2],["metric_source.png","Metric Source","A1:B10",1.1]]){
  const img=await wb.render({sheetName,range,scale,format:"png"}); await fs.writeFile(path.join(qa,name),new Uint8Array(await img.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(wb)).save(out);
const rt=await SpreadsheetFile.importXlsx(await FileBlob.load(out));
const ids=rt.worksheets.getItem("A vs Pipeline").getRange("A5:A42").values.flat().filter(Boolean);
if(ids.length!==38||new Set(ids).size!==38) throw new Error("round-trip ID check failed");
const human=rt.worksheets.getItem("A vs Pipeline").getRange("O5:Q42").values.flat();
if(human.some(v=>v!==null&&v!=="")) throw new Error("human fields were prefilled");
console.log(JSON.stringify({output:out,rows:ids.length,humanFieldsBlank:true,formulaScan:errors.ndjson},null,2));
