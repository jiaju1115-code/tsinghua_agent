import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_test";
const specs = [
  ["analysis/v2_vs_human_analysis.json", "analysis/v2_vs_human_analysis.xlsx", "V2 vs Human", "Prompt V2 与人工判断差异分析"],
  ["results/prompt_v3_30_results.json", "results/prompt_v3_30_results.xlsx", "Prompt V3 30", "Prompt V3 30 条回归结果"],
];
const excelCol = (n) => { let s = ""; while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26); } return s; };
const widthFor = (h) => {
  if (/^id$/.test(h)) return 18;
  if (/url/.test(h)) return 45;
  if (/title/.test(h)) return 34;
  if (/reason|evidence|note|question|rule/.test(h)) return 48;
  if (/action|status|type|category/.test(h)) return 24;
  return 20;
};
async function build([jsonRel, xlsxRel, sheetName, title], idx) {
  const rows = JSON.parse(await fs.readFile(path.join(base, jsonRel), "utf8"));
  const headers = Object.keys(rows[0] ?? {});
  const wb = Workbook.create();
  const sheet = wb.worksheets.add(sheetName);
  sheet.showGridLines = false;
  sheet.getCell(0, 0).values = [[title]];
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = { fill: "#0F4C5C", font: { name: "Microsoft YaHei", size: 15, bold: true, color: "#FFFFFF" }, rowHeight: 32 };
  sheet.getCell(1, 0).values = [[`固定 30 条样本；生成时间 2026-08-12；共 ${rows.length} 条`]];
  sheet.getRangeByIndexes(1, 0, 1, headers.length).format = { fill: "#E7F3F5", font: { name: "Microsoft YaHei", size: 9, color: "#34515A" }, rowHeight: 23 };
  const matrix = [headers, ...rows.map(r => headers.map(h => r[h] ?? ""))];
  sheet.getRangeByIndexes(2, 0, matrix.length, headers.length).values = matrix;
  sheet.getRangeByIndexes(2, 0, 1, headers.length).format = { fill: "#137C8B", font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, rowHeight: 34 };
  if (rows.length) {
    const body = sheet.getRangeByIndexes(3, 0, rows.length, headers.length);
    body.format = { font: { name: "Microsoft YaHei", size: 9, color: "#1F2937" }, verticalAlignment: "top", wrapText: true, rowHeight: 48, borders: { insideHorizontal: { style: "thin", color: "#E5E7EB" } } };
    headers.forEach((h, c) => { sheet.getRangeByIndexes(2, c, rows.length + 1, 1).format.columnWidth = widthFor(h); });
    const table = sheet.tables.add(`A3:${excelCol(headers.length)}${rows.length + 3}`, true, `T_V3_${String(idx).padStart(2, "0")}`);
    table.style = "TableStyleMedium2"; table.showFilterButton = true;
    for (const actionHeader of ["V2", "V3", "human", "V2_action", "human_action"]) {
      const c = headers.indexOf(actionHeader); if (c < 0) continue;
      const range = sheet.getRangeByIndexes(3, c, rows.length, 1);
      for (const [text, fill, color] of [["approve", "#DCFCE7", "#166534"], ["review", "#FEF3C7", "#92400E"], ["reject", "#FEE2E2", "#991B1B"]]) range.conditionalFormats.add("containsText", { text, format: { fill, font: { color, bold: true } } });
    }
  }
  sheet.freezePanes.freezeRows(3); sheet.freezePanes.freezeColumns(Math.min(3, headers.length));
  const outPath = path.join(base, xlsxRel); await fs.mkdir(path.dirname(outPath), { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(wb); await xlsx.save(outPath);
  const preview = await wb.render({ sheetName, range: `A1:${excelCol(Math.min(headers.length, 8))}${Math.min(rows.length + 3, 10)}`, scale: 1, format: "png" });
  const previewPath = path.join(base, "audit", `preview_${String(idx).padStart(2, "0")}.png`); await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  return { file: xlsxRel, rows: rows.length, columns: headers.length, preview: previewPath, formulaCount: 0 };
}
const verification = []; for (let i = 0; i < specs.length; i++) verification.push(await build(specs[i], i + 1));
await fs.writeFile(path.join(base, "audit", "workbook_verification.json"), JSON.stringify(verification, null, 2), "utf8");
console.log(JSON.stringify(verification));
