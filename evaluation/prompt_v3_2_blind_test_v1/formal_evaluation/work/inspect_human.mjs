import fs from "node:fs/promises";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_blind_test_v1";
const input = `${base}/human_label/blind_test_v1_human_label.xlsx`;
await fs.mkdir(`${base}/formal_evaluation/audit`, {recursive:true});
const manifest = JSON.parse(await fs.readFile(`${base}/samples/blind_test_v1_sample_manifest.json`, "utf8"));
const blob = await FileBlob.load(input);
const wb = await SpreadsheetFile.importXlsx(blob);
const sheetInfo = await wb.inspect({ kind: "sheet", include: "id,name", maxChars: 2000 });
const sheet = wb.worksheets.getItemAt(0);
const used = sheet.getUsedRange(true);
const values = used.values;
const headerIndex = values.findIndex(row => row.includes("blind_id") && row.includes("human_action"));
if (headerIndex < 0) throw new Error("human label header not found");
const headers = values[headerIndex].map(x => String(x ?? "").trim());
const rows = values.slice(headerIndex + 1).filter(row => String(row[0] ?? "").trim()).map(row => Object.fromEntries(headers.map((h,i)=>[h,row[i] ?? ""])));
const validActions = new Set(["approve","review","reject"]);
const validTopic = new Set(["high","medium","low",""]);
const validReject = new Set(["topic_irrelevant","expired_event","other",""]);
const clean = v => String(v ?? "").trim();
const summary = {
  input,
  sha256: crypto.createHash("sha256").update(await fs.readFile(input)).digest("hex").toUpperCase(),
  sheetInfo: sheetInfo.ndjson,
  usedRows: values.length,
  usedColumns: Math.max(...values.map(r=>r.length)),
  headerRow1Based: headerIndex + 1,
  dataRows: rows.length,
  manifestRows: manifest.length,
  idSetMatchesManifest: rows.length === manifest.length && rows.every((r,i)=>clean(r.blind_id)===manifest[i].blind_id),
  actionValidCount: rows.filter(r=>validActions.has(clean(r.human_action))).length,
  actionMissingOrIllegalCount: rows.filter(r=>!validActions.has(clean(r.human_action))).length,
  topicValidNonblankCount: rows.filter(r=>["high","medium","low"].includes(clean(r.human_topic_relevance))).length,
  topicMissingOrIllegalCount: rows.filter(r=>!validTopic.has(clean(r.human_topic_relevance)) || clean(r.human_topic_relevance)==="").length,
  rejectTypeValidNonblankCount: rows.filter(r=>["topic_irrelevant","expired_event","other"].includes(clean(r.human_reject_type))).length,
  rejectTypeIllegalCount: rows.filter(r=>!validReject.has(clean(r.human_reject_type))).length,
  actionDistribution: Object.groupBy(rows, r=>clean(r.human_action)),
};
summary.actionDistribution = Object.fromEntries(Object.entries(summary.actionDistribution).map(([k,v])=>[k,v.length]));
await fs.writeFile(`${base}/formal_evaluation/audit/human_label_preflight.json`, JSON.stringify(summary,null,2), "utf8");
await fs.writeFile(`${base}/formal_evaluation/audit/frozen_human_labels.json`, JSON.stringify(rows,null,2), "utf8");
const preview = await wb.render({sheetName: sheet.name, range:"A1:Q10", scale:1, format:"png"});
await fs.writeFile(`${base}/formal_evaluation/audit/human_label_preview.png`, new Uint8Array(await preview.arrayBuffer()));
console.log(JSON.stringify(summary,null,2));
