import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const base = String.raw`D:\python_projects\tsinghua_ai\data_second\restricted_expansion_v1`;
const previews = path.join(base, "_workbook_previews");
const status = "NEED_MANUAL_LOGIN";

const specs = [
  { out: path.join(base, "safety_gate", "private_sensitive_gate_results.xlsx"), title: "Private / Sensitive Gate Results", sheet: "Safety Gate", cols: ["restricted_id","url","private_sensitive_status","reason","run_status"], rows: [] },
  { out: path.join(base, "quality_gate", "restricted_quality_gate_results.xlsx"), title: "Restricted Quality Gate Results", sheet: "Quality Gate", cols: ["restricted_id","url","quality_class","quality_gate_pass","diagnostic_reason","run_status"], rows: [] },
  { out: path.join(base, "candidates", "restricted_expansion_v1_all.xlsx"), title: "Restricted Expansion V1 — All Candidates", sheet: "All", cols: ["restricted_id","title","url","category","private_sensitive_status","quality_class","v3_2_action","data_status","source_file"], rows: [] },
  { out: path.join(base, "candidates", "restricted_approved_candidates.xlsx"), title: "Restricted Approved Candidates", sheet: "Approved", cols: ["restricted_id","title","url","category","v3_2_action","data_status","source_file"], rows: [] },
  { out: path.join(base, "candidates", "restricted_review_candidates.xlsx"), title: "Restricted Review Candidates", sheet: "Review", cols: ["restricted_id","title","url","category","v3_2_action","data_status","source_file"], rows: [] },
];

for (const spec of specs) {
  const wb = Workbook.create();
  const ws = wb.worksheets.add(spec.sheet);
  ws.showGridLines = false;
  const end = col(spec.cols.length);
  ws.getRange(`A1:${end}1`).merge();
  ws.getRange("A1").values = [[spec.title]];
  ws.getRange(`A2:${end}2`).merge();
  ws.getRange("A2").values = [["Run stopped before authenticated fetch: NEED_MANUAL_LOGIN"]];
  ws.getRange(`A1:${end}1`).format = { fill: "#16324F", font: { color: "#FFFFFF", bold: true, size: 15 }, rowHeight: 28 };
  ws.getRange(`A2:${end}2`).format = { fill: "#FFF3CD", font: { color: "#7A4E00", bold: true }, rowHeight: 24 };
  ws.getRange(`A4:${end}4`).values = [spec.cols];
  ws.getRange(`A4:${end}4`).format = { fill: "#1F7A8C", font: { color: "#FFFFFF", bold: true }, wrapText: true, rowHeight: 30, borders: { preset: "all", style: "thin", color: "#D8E2E8" } };
  ws.getRange(`A5:${end}5`).merge();
  ws.getRange("A5").values = [["0 rows — authentication/session could not be validated; no restricted content was fetched."]];
  ws.getRange(`A5:${end}5`).format = { fill: "#F4F7F9", font: { color: "#526776", italic: true }, rowHeight: 24, borders: { preset: "all", style: "thin", color: "#D8E2E8" } };
  ws.freezePanes.freezeRows(4);
  ws.getUsedRange().format.autofitColumns();
  for (let i=1;i<=spec.cols.length;i++) ws.getRange(`${col(i)}:${col(i)}`).format.columnWidthPx = ["url","source_file","reason"].includes(spec.cols[i-1]) ? 280 : 150;
  const png = await wb.render({ sheetName: spec.sheet, range: `A1:${end}5`, scale: 1, format: "png" });
  const previewName = path.basename(spec.out, ".xlsx") + ".png";
  await fs.writeFile(path.join(previews, previewName), new Uint8Array(await png.arrayBuffer()));
  const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 2000 });
  await fs.writeFile(path.join(previews, previewName.replace(".png", ".errors.json")), JSON.stringify(errors, null, 2));
  const out = await SpreadsheetFile.exportXlsx(wb);
  await out.save(spec.out);
  console.log(JSON.stringify({ output: spec.out, status, rows: 0 }));
}

function col(n) { let s=""; while(n>0){n--;s=String.fromCharCode(65+n%26)+s;n=Math.floor(n/26);} return s; }
