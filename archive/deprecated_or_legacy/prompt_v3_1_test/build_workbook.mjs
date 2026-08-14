import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_1_test";
const rows = JSON.parse(await fs.readFile(path.join(base, "results/prompt_v3_1_30_results.json"), "utf8"));
const headers = ["id", "title", "url", "V2_action", "V3_action", "V3_1_action", "human_action", "category", "content_type", "time_status", "reject_type", "candidate_user_question", "positive_evidence", "negative_evidence", "reason"];
const wb = Workbook.create();
const sheet = wb.worksheets.add("V3.1 30条回归");
sheet.showGridLines = false;
sheet.getRange("A1").values = [["Prompt V3.1 固定 30 条回归结果"]];
sheet.getRange("A1:O1").format = { fill: "#123B4A", font: { name: "Microsoft YaHei", size: 16, bold: true, color: "#FFFFFF" }, verticalAlignment: "center", rowHeight: 34 };
sheet.getRange("A2").values = [["同一固定样本｜V2 / V3 / V3.1 / Human 四方对比｜生成日期 2026-08-12"]];
sheet.getRange("A2:O2").format = { fill: "#E6F2F4", font: { name: "Microsoft YaHei", size: 9, color: "#34515A" }, verticalAlignment: "center", rowHeight: 23 };

const matrix = [headers, ...rows.map(r => headers.map(h => r[h] ?? ""))];
sheet.getRangeByIndexes(2, 0, matrix.length, headers.length).values = matrix;
sheet.getRange("A3:O3").format = { fill: "#167C8C", font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, rowHeight: 34, borders: { bottom: { style: "medium", color: "#123B4A" } } };
sheet.getRange("A4:O33").format = { font: { name: "Microsoft YaHei", size: 9, color: "#1F2937" }, verticalAlignment: "top", wrapText: true, rowHeight: 48, borders: { insideHorizontal: { style: "thin", color: "#E5E7EB" } } };

const widths = [18, 34, 44, 15, 15, 15, 15, 24, 22, 23, 20, 42, 48, 48, 50];
widths.forEach((w, i) => { sheet.getRangeByIndexes(2, i, 31, 1).format.columnWidth = w; });
const table = sheet.tables.add("A3:O33", true, "PromptV31Regression");
table.style = "TableStyleMedium2";
table.showFilterButton = true;

for (const col of [3, 4, 5, 6]) {
  const range = sheet.getRangeByIndexes(3, col, 30, 1);
  range.conditionalFormats.add("containsText", { text: "approve", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
  range.conditionalFormats.add("containsText", { text: "review", format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } } });
  range.conditionalFormats.add("containsText", { text: "reject", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
}
sheet.getRange("J4:J33").conditionalFormats.add("containsText", { text: "active_time_bound", format: { fill: "#DBEAFE", font: { color: "#1D4ED8", bold: true } } });
sheet.getRange("K4:K33").conditionalFormats.add("containsText", { text: "expired_event", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
sheet.getRange("K4:K33").conditionalFormats.add("containsText", { text: "out_of_scope", format: { fill: "#E5E7EB", font: { color: "#374151", bold: true } } });
sheet.freezePanes.freezeRows(3);
sheet.freezePanes.freezeColumns(3);

const outputPath = path.join(base, "results/prompt_v3_1_30_results.xlsx");
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const inspect = await wb.inspect({ kind: "region", sheetId: "V3.1 30条回归", range: "A1:O8", maxChars: 5000 });
await fs.writeFile(path.join(base, "audit/workbook_inspect.ndjson"), inspect.ndjson, "utf8");
const preview = await wb.render({ sheetName: "V3.1 30条回归", range: "A1:K10", scale: 1, format: "png" });
await fs.writeFile(path.join(base, "audit/workbook_preview.png"), new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);
await fs.writeFile(path.join(base, "audit/workbook_verification.json"), JSON.stringify({ rows: rows.length, columns: headers.length, formulaCount: 0, outputPath }, null, 2), "utf8");
console.log(JSON.stringify({ rows: rows.length, columns: headers.length, outputPath }));
