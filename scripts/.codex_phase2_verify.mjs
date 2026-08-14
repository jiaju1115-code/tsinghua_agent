import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";
const dir="D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_blind_test_v1/codex_evaluation/results";
const files=[["codex_blind_test_v1_results.xlsx","Results",51,29],["codex_blind_test_v1_disagreements.xlsx","Disagreements",5,14],["human_label_questions.xlsx","Questions",12,15]];
const out=[];
for(const [f,sn,rows,cols] of files){const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${dir}/${f}`));const ins=await wb.inspect({kind:"table",sheetId:sn,range:`A1:AC${rows}`,include:"values",tableMaxRows:3,tableMaxCols:cols,maxChars:5000});const png=await wb.render({sheetName:sn,range:`A1:${cols>26?"AC":String.fromCharCode(64+cols)}${Math.min(rows,8)}`,scale:1,format:"png"});await fs.writeFile(`${dir}/${f}.preview.png`,new Uint8Array(await png.arrayBuffer()));out.push({file:f,expected_rows:rows,expected_cols:cols,inspect:ins.ndjson.slice(0,1000),preview:`${dir}/${f}.preview.png`});}
process.stdout.write(JSON.stringify(out));
