import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const v1 = "D:/python_projects/tsinghua_ai/data_second/rag_v1";
const workDir = path.join(v1, "logs", "workbook_qa");
const rows = JSON.parse(await fs.readFile(path.join(v1, "evaluation", "smoke_comparison_rows.json"), "utf8"));
const headers = ["query_id", "query", "V0 TF-IDF结果", "Dense结果", "Hybrid结果", "Hybrid + Rerank结果", "expected category",
  "expected source", "top5 category hit", "top5 source hit", "previous V0 verdict", "V1 verdict", "change", "note"];
const keys = ["query_id", "query", "v0_tfidf_result", "dense_result", "hybrid_result", "hybrid_rerank_result", "expected_category",
  "expected_source", "top5_category_hit", "top5_source_hit", "previous_v0_verdict", "v1_verdict", "change", "note"];
const matrix = rows.map((row) => keys.map((key) => row[key]));

const wb = Workbook.create();
const sheet = wb.worksheets.add("V0 vs V1 Smoke");
const summary = wb.worksheets.add("Verdict Summary");
sheet.showGridLines = false;
sheet.getRange("A1:N1").merge();
sheet.getRange("A1").values = [["V0 vs V1 — Frozen 10-Query Smoke Comparison"]];
sheet.getRange("A2:N2").merge();
sheet.getRange("A2").values = [["Verdicts distinguish retriever behavior from source-data ceilings; no external model supplied correctness labels."]];
sheet.getRange("A4:N4").values = [headers];
sheet.getRange(`A5:N${4 + matrix.length}`).values = matrix;
sheet.tables.add(`A4:N${4 + matrix.length}`, true, "SmokeComparison").style = "TableStyleMedium2";
sheet.freezePanes.freezeRows(4);
sheet.freezePanes.freezeColumns(2);
sheet.getRange("A1:N1").format = { fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 } };
sheet.getRange("A2:N2").format = { fill: "#EAF0F6", font: { italic: true, color: "#334155" }, wrapText: true };
sheet.getRange("A4:N4").format = { fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
sheet.getRange(`A5:N${4 + matrix.length}`).format = { verticalAlignment: "top", wrapText: true };
sheet.getRange("A:A").format.columnWidth = 12;
sheet.getRange("B:B").format.columnWidth = 42;
sheet.getRange("C:F").format.columnWidth = 42;
sheet.getRange("G:H").format.columnWidth = 21;
sheet.getRange("I:J").format.columnWidth = 30;
sheet.getRange("K:M").format.columnWidth = 16;
sheet.getRange("N:N").format.columnWidth = 44;
sheet.getRange("A1:N1").format.rowHeight = 30;
sheet.getRange("A2:N2").format.rowHeight = 26;
sheet.getRange("A4:N4").format.rowHeight = 38;

summary.showGridLines = false;
summary.getRange("A1:C1").merge();
summary.getRange("A1").values = [["Smoke Verdict Summary"]];
summary.getRange("A3:C3").values = [["verdict", "V0 count", "V1 count"]];
summary.getRange("A4:A6").values = [["pass"], ["partial"], ["fail"]];
for (let r = 4; r <= 6; r++) {
  summary.getRange(`B${r}`).formulas = [[`=COUNTIF('V0 vs V1 Smoke'!K5:K14,A${r})`]];
  summary.getRange(`C${r}`).formulas = [[`=COUNTIF('V0 vs V1 Smoke'!L5:L14,A${r})`]];
}
summary.getRange("A8:B11").values = [["change", "count"], ["improved", null], ["unchanged", null], ["degraded", null]];
for (let r = 9; r <= 11; r++) summary.getRange(`B${r}`).formulas = [[`=COUNTIF('V0 vs V1 Smoke'!M5:M14,A${r})`]];
summary.getRange("A1:C1").format = { fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 } };
summary.getRange("A3:C3").format = { fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
summary.getRange("A8:B8").format = { fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
summary.getRange("A:C").format.columnWidth = 20;

await fs.mkdir(workDir, { recursive: true });
const inspect = await wb.inspect({ kind: "table", range: "'V0 vs V1 Smoke'!A1:N14", include: "values,formulas", tableMaxRows: 14, tableMaxCols: 14, maxChars: 20000 });
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
const preview1 = await wb.render({ sheetName: "V0 vs V1 Smoke", range: "A1:N10", scale: 0.8, format: "png" });
const preview2 = await wb.render({ sheetName: "Verdict Summary", autoCrop: "all", scale: 1.5, format: "png" });
await fs.writeFile(path.join(workDir, "smoke_comparison.png"), new Uint8Array(await preview1.arrayBuffer()));
await fs.writeFile(path.join(workDir, "smoke_verdict_summary.png"), new Uint8Array(await preview2.arrayBuffer()));
await fs.writeFile(path.join(workDir, "smoke_inspect.ndjson"), inspect.ndjson, "utf8");
await fs.writeFile(path.join(workDir, "smoke_formula_errors.ndjson"), errors.ndjson, "utf8");
const output = path.join(v1, "evaluation", "v0_vs_v1_smoke_comparison.xlsx");
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
const roundTrip = await SpreadsheetFile.importXlsx(await FileBlob.load(output));
const ids = roundTrip.worksheets.getItem("V0 vs V1 Smoke").getRange("A5:A14").values.flat().filter(Boolean);
if (ids.length !== 10 || new Set(ids).size !== 10) throw new Error("Round-trip smoke query verification failed");
console.log(JSON.stringify({ output, rows: ids.length, formula_scan: errors.ndjson }));
