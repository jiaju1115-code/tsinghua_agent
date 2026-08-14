import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "D:/python_projects/tsinghua_ai/data_second/answer_eval_v0";
const qaDir = path.join(root, "logs", "workbook_qa");
const lines = (await fs.readFile(path.join(root, "results", "answer_eval_merged.jsonl"), "utf8"))
  .split(/\r?\n/).filter(Boolean).map(JSON.parse);
const metrics = JSON.parse(await fs.readFile(path.join(root, "results", "final_metrics.json"), "utf8"));
const smoke = JSON.parse(await fs.readFile(path.join(root, "results", "v0_smoke_answer_comparison.json"), "utf8"));
await fs.mkdir(qaDir, { recursive: true });

function col(n){let s="";while(n){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26)}return s}
function joined(v){return Array.isArray(v)?v.join(" | "):(v??"")}
function contextPreview(row){return row.retrieved_context.map(c=>`[${c.context_id}] ${c.source_id} ${c.title}\n${String(c.text).replace(/\s+/g," ").slice(0,500)}`).join("\n---\n")}

const headers = [
  "question_id","question","eval_status","category","expected_source_id","expected_source_status",
  "retrieved_chunk_ids","retrieved_document_ids","retrieval_scores","retrieved_context_preview",
  "generated_answer","answer_citations","generation_latency_s","generation_status","finish_reason",
  "auto_correctness_0_2","auto_faithfulness_0_2","unsupported_claim_count","total_claim_count","unsupported_claim_rate",
  "citation_correctness_0_2","refusal_appropriate","completeness_0_2","retrieval_to_answer_consistency",
  "hallucination_type","auto_reason","auto_eval_status",
  "human_correctness","human_faithfulness","human_hallucination","human_error_type","human_comment"
];
const rows = lines.map(r=>{
  const a=r.auto_evaluation, e=r.auto_evaluation_record;
  return [
    r.question_id,r.question,r.eval_status,r.category,r.expected_source_id||"",r.expected_source_status,
    joined(r.retrieved_chunk_ids),joined(r.retrieved_document_ids),r.retrieval_scores.map(x=>x.toFixed(6)).join(" | "),contextPreview(r),
    r.generated_answer,joined(r.answer_citations),r.latency.generation_seconds,r.generation_status,r.finish_reason,
    a.correctness,a.faithfulness,a.unsupported_claim_count,a.claim_count,a.claim_count?a.unsupported_claim_count/a.claim_count:0,
    a.citation_correctness,a.refusal_appropriate===null?"":String(a.refusal_appropriate),a.completeness,a.consistency,
    joined(a.hallucination_types),a.reason,e.evaluation_status,
    "","","","",""
  ];
});

function styleTitle(sheet, end, title, note){
  sheet.showGridLines=false;
  sheet.getRange(`A1:${end}1`).merge(); sheet.getRange("A1").values=[[title]];
  sheet.getRange(`A2:${end}2`).merge(); sheet.getRange("A2").values=[[note]];
  sheet.getRange(`A1:${end}1`).format={fill:"#17324D",font:{bold:true,color:"#FFFFFF",size:17},rowHeight:32};
  sheet.getRange(`A2:${end}2`).format={fill:"#EAF0F6",font:{italic:true,color:"#334155"},wrapText:true,rowHeight:28};
}

async function makeMainWorkbook(){
  const wb=Workbook.create();
  const summary=wb.worksheets.add("Summary");
  const sheet=wb.worksheets.add("Answer Eval");
  const lists=wb.worksheets.add("Validation Lists");
  summary.showGridLines=false;
  summary.getRange("A1:H1").merge();summary.getRange("A1").values=[["Answer Generation Evaluation V0"]];
  summary.getRange("A2:H2").merge();summary.getRange("A2").values=[["PROVISIONAL_AUTO_EVAL — Human Audit pending; not a final benchmark"]];
  summary.getRange("A1:H1").format={fill:"#17324D",font:{bold:true,color:"#FFFFFF",size:18},rowHeight:34};
  summary.getRange("A2:H2").format={fill:"#FFF4CC",font:{italic:true,color:"#6B4F00"},wrapText:true,rowHeight:28};
  const summaryRows=[
    ["Questions",metrics.questions,"Generator",metrics.generation_model.model_name],
    ["Completed",metrics.generation_completed,"Retriever","BAAI/bge-small-zh-v1.5 Dense Top-5"],
    ["Correctness (0–2)",metrics.answer_correctness_mean_0_to_2,"Fully correct",metrics.fully_correct_count],
    ["Faithfulness (0–2)",metrics.faithfulness_mean_0_to_2,"Unsupported claim rate",metrics.unsupported_claim_rate],
    ["Correct refusals",metrics.correct_refusal_count,"Hallucination answers",metrics.hallucination_answer_count],
    ["Retrieval failures",metrics.retrieval_failure_count,"Source quality failures",metrics.source_quality_failure_count],
    ["Citation mismatches",metrics.hallucination_type_distribution.CITATION_MISMATCH||0,"Avg generation latency (s)",metrics.avg_generation_latency_seconds],
  ];
  summary.getRange("A4:D10").values=summaryRows;
  summary.getRange("A4:A10").format={fill:"#DCEFF3",font:{bold:true,color:"#0F4C5C"}};
  summary.getRange("C4:C10").format={fill:"#DCEFF3",font:{bold:true,color:"#0F4C5C"}};
  summary.getRange("B4:B10").format={fill:"#F7FBFC",font:{bold:true}};
  summary.getRange("D4:D10").format={fill:"#F7FBFC",font:{bold:true},wrapText:true};
  summary.getRange("A12:B12").values=[["Hallucination / error type","Count"]];
  const dist=Object.entries(metrics.hallucination_type_distribution);
  summary.getRange(`A13:B${12+dist.length}`).values=dist;
  summary.getRange("A12:B12").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"}};
  summary.getRange("A:D").format.columnWidth=28;summary.getRange("D:D").format.columnWidth=45;
  summary.getRange("D7").format.numberFormat="0.00%";

  const end=col(headers.length), last=4+rows.length;
  styleTitle(sheet,end,"Answer Generation Evaluation — 38 Questions","自动评分来自本地同源小模型+确定性规则；黄色列由人工填写，当前全部为空。");
  sheet.getRange(`A4:${end}4`).values=[headers];sheet.getRange(`A5:${end}${last}`).values=rows;
  sheet.tables.add(`A4:${end}${last}`,true,"AnswerEvalTable").style="TableStyleMedium2";
  sheet.freezePanes.freezeRows(4);sheet.freezePanes.freezeColumns(4);
  sheet.getRange(`A4:${end}4`).format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"},wrapText:true,horizontalAlignment:"center",rowHeight:42};
  sheet.getRange(`A5:${end}${last}`).format={verticalAlignment:"top",wrapText:true,font:{name:"Microsoft YaHei",size:10}};
  headers.forEach((h,i)=>{const c=col(i+1);let w=16;if(["question","generated_answer","auto_reason"].includes(h))w=42;if(h==="retrieved_context_preview")w=55;if(["retrieved_chunk_ids","retrieved_document_ids","retrieval_scores","hallucination_type","retrieval_to_answer_consistency"].includes(h))w=30;if(h==="human_comment")w=36;sheet.getRange(`${c}:${c}`).format.columnWidth=w;});
  const ucr=col(headers.indexOf("unsupported_claim_rate")+1);sheet.getRange(`${ucr}5:${ucr}${last}`).format.numberFormat="0.00%";
  const lat=col(headers.indexOf("generation_latency_s")+1);sheet.getRange(`${lat}5:${lat}${last}`).format.numberFormat="0.000";
  const hStart=headers.indexOf("human_correctness")+1,hEnd=headers.length;
  sheet.getRange(`${col(hStart)}5:${col(hEnd)}${last}`).format={fill:"#FFF4CC",font:{color:"#6B4F00"},verticalAlignment:"top",wrapText:true};
  sheet.getRange(`${col(hStart)}5:${col(hStart)}${last}`).dataValidation={rule:{type:"list",values:["correct","partial","incorrect","uncertain"]}};
  sheet.getRange(`${col(hStart+1)}5:${col(hStart+1)}${last}`).dataValidation={rule:{type:"list",values:["faithful","partial","unfaithful","uncertain"]}};
  sheet.getRange(`${col(hStart+2)}5:${col(hStart+2)}${last}`).dataValidation={rule:{type:"list",values:["yes","no","uncertain"]}};
  sheet.getRange(`${col(hStart+3)}5:${col(hStart+3)}${last}`).dataValidation={rule:{type:"list",values:["NONE","RETRIEVAL_FAILURE","SOURCE_QUALITY_FAILURE","GENERATION_HALLUCINATION","UNSUPPORTED_INFERENCE","CITATION_MISMATCH","OVERCONFIDENT_ANSWER","INCOMPLETE_ANSWER","CONFLICT_NOT_DISCLOSED"]}};
  sheet.getRange(`Y5:Y${last}`).conditionalFormats.add("containsText",{text:"NONE",format:{fill:"#DCFCE7",font:{color:"#166534"}}});
  sheet.getRange(`Y5:Y${last}`).conditionalFormats.add("containsText",{text:"HALLUCINATION",format:{fill:"#FEE2E2",font:{color:"#991B1B",bold:true}}});

  lists.getRange("A1:D1").values=[["human_correctness","human_faithfulness","human_hallucination","human_error_type"]];
  lists.getRange("A2:A5").values=[["correct"],["partial"],["incorrect"],["uncertain"]];
  lists.getRange("B2:B5").values=[["faithful"],["partial"],["unfaithful"],["uncertain"]];
  lists.getRange("C2:C4").values=[["yes"],["no"],["uncertain"]];
  lists.getRange("D2:D10").values=[["NONE"],["RETRIEVAL_FAILURE"],["SOURCE_QUALITY_FAILURE"],["GENERATION_HALLUCINATION"],["UNSUPPORTED_INFERENCE"],["CITATION_MISMATCH"],["OVERCONFIDENT_ANSWER"],["INCOMPLETE_ANSWER"],["CONFLICT_NOT_DISCLOSED"]];
  lists.getRange("A1:D1").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"}};lists.getRange("A:D").format.columnWidth=28;
  return wb;
}

async function makeSmokeWorkbook(){
  const wb=Workbook.create();const sheet=wb.worksheets.add("V0 Smoke Answer Eval");
  const hs=["question_id","question","RAG V0 original result","RAG V1 Dense result","generated_answer","answer_citations","previous V0 verdict","RAG V1 retrieval verdict","Answer V0 verdict","change","correctness","faithfulness","unsupported claim rate","citation correctness","refusal appropriate","consistency","hallucination types","error attribution","note"];
  const ks=["question_id","question","rag_v0_result","rag_v1_dense_result","generated_answer","answer_citations","previous_v0_verdict","rag_v1_retrieval_verdict","answer_v0_verdict","change","correctness","faithfulness","unsupported_claim_rate","citation_correctness","refusal_appropriate","consistency","hallucination_types","error_attribution","note"];
  const matrix=smoke.map(r=>ks.map(k=>r[k]??""));
  styleTitle(sheet,"S","V0 Smoke → RAG V1 Dense → Answer Generation V0","固定 10 题未修改；transport source gap 与 retrieval/generation 错误分开归因。");
  sheet.getRange("A4:S4").values=[hs];sheet.getRange("A5:S14").values=matrix;sheet.tables.add("A4:S14",true,"SmokeAnswerEvalTable").style="TableStyleMedium2";
  sheet.freezePanes.freezeRows(4);sheet.freezePanes.freezeColumns(2);
  sheet.getRange("A4:S4").format={fill:"#2B6F77",font:{bold:true,color:"#FFFFFF"},wrapText:true,horizontalAlignment:"center",rowHeight:42};
  sheet.getRange("A5:S14").format={verticalAlignment:"top",wrapText:true};
  sheet.getRange("A:A").format.columnWidth=12;sheet.getRange("B:B").format.columnWidth=40;sheet.getRange("C:E").format.columnWidth=46;sheet.getRange("F:S").format.columnWidth=20;sheet.getRange("P:S").format.columnWidth=30;
  sheet.getRange("M5:M14").format.numberFormat="0.00%";
  sheet.getRange("J5:J14").conditionalFormats.add("containsText",{text:"improved",format:{fill:"#DCFCE7",font:{color:"#166534",bold:true}}});
  sheet.getRange("J5:J14").conditionalFormats.add("containsText",{text:"degraded",format:{fill:"#FEE2E2",font:{color:"#991B1B",bold:true}}});
  return wb;
}

async function exportAndVerify(wb, filename, mainSheet, inspectRange, renderRanges){
  const output=path.join(root,"evaluation",filename);
  const inspect=await wb.inspect({kind:"table",range:`'${mainSheet}'!${inspectRange}`,include:"values,formulas",tableMaxRows:50,tableMaxCols:40,maxChars:50000});
  const errors=await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},summary:"formula error scan"});
  await fs.writeFile(path.join(qaDir,`${filename}.inspect.ndjson`),inspect.ndjson,"utf8");
  await fs.writeFile(path.join(qaDir,`${filename}.formula_errors.ndjson`),errors.ndjson,"utf8");
  for(const [name,sheetName,range,scale] of renderRanges){const img=await wb.render({sheetName,range,scale,format:"png"});await fs.writeFile(path.join(qaDir,name),new Uint8Array(await img.arrayBuffer()));}
  await (await SpreadsheetFile.exportXlsx(wb)).save(output);
  const round=await SpreadsheetFile.importXlsx(await FileBlob.load(output));
  const ids=round.worksheets.getItem(mainSheet).getRange(mainSheet==="Answer Eval"?"A5:A42":"A5:A14").values.flat().filter(Boolean);
  const expected=mainSheet==="Answer Eval"?38:10;
  if(ids.length!==expected||new Set(ids).size!==expected)throw new Error(`${filename} round-trip ID validation failed`);
  if(mainSheet==="Answer Eval"){
    const human=round.worksheets.getItem(mainSheet).getRange("AB5:AF42").values.flat();
    if(human.some(v=>v!==null&&v!==""))throw new Error("Human fields were prefilled");
  }
  return {output,rows:ids.length,formulaScan:errors.ndjson};
}

const main=await makeMainWorkbook();
const smokeWb=await makeSmokeWorkbook();
const result1=await exportAndVerify(main,"answer_generation_eval.xlsx","Answer Eval","A1:AF42",[["answer_summary.png","Summary","A1:H22",1.3],["answer_eval.png","Answer Eval","A1:AF12",0.6],["validation_lists.png","Validation Lists","A1:D10",1.1]]);
const result2=await exportAndVerify(smokeWb,"v0_smoke_answer_eval.xlsx","V0 Smoke Answer Eval","A1:S14",[["v0_smoke_answer_eval.png","V0 Smoke Answer Eval","A1:S14",0.65]]);
console.log(JSON.stringify({main:result1,smoke:result2},null,2));
