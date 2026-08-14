import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/public_expansion_v1/run_6";
const specs = [
  ["_all.json", "public_expansion_v1_all.xlsx", "全部候选"],
  ["_approved.json", "public_expansion_v1_approved.xlsx", "准入候选"],
  ["_review.json", "public_expansion_v1_review.xlsx", "人工复核"],
  ["_human_check.json", "public_expansion_v1_human_check.xlsx", "人工抽检"],
];

async function build(jsonName, xlsxName, sheetName) {
  const rows = JSON.parse(await fs.readFile(`${base}/${jsonName}`, "utf8"));
  const headers = Object.keys(rows[0] ?? {});
  const wb = Workbook.create();
  const sheet = wb.worksheets.add(sheetName);
  const matrix = [headers, ...rows.map(r => headers.map(h => r[h] ?? ""))];
  sheet.getRangeByIndexes(0, 0, matrix.length, headers.length).values = matrix;
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);
  const used = sheet.getUsedRange();
  used.format = {
    font: { name: "Microsoft YaHei", size: 10, color: "#1F2937" },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#E5E7EB" },
  };
  const header = sheet.getRangeByIndexes(0, 0, 1, used.columnCount);
  header.format = {
    fill: "#0F766E",
    font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    rowHeight: 32,
    borders: { preset: "all", style: "thin", color: "#0B5F59" },
  };
  const widths = [16, 34, 48, 25, 22, 12, 20, 22, 18, 15, 38, 42, 42, 16, 52, 16, 20, 28];
  for (let col = 0; col < used.columnCount; col++) {
    sheet.getRangeByIndexes(0, col, used.rowCount, 1).format.columnWidth = widths[col] ?? 20;
  }
  if (used.rowCount > 1 && used.columnCount > 4) {
    sheet.getRangeByIndexes(1, 4, used.rowCount - 1, 1).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
  }
  if (used.rowCount > 1) sheet.getRangeByIndexes(1, 0, used.rowCount - 1, used.columnCount).format.rowHeight = 48;
  const table = sheet.tables.add(used.address, true, `T_${xlsxName.replace(/[^A-Za-z0-9]/g, "_")}`);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  const actionCol = 5;
  if (used.columnCount > actionCol && used.rowCount > 1) {
    const actionRange = sheet.getRangeByIndexes(1, actionCol, used.rowCount - 1, 1);
    actionRange.conditionalFormats.add("containsText", { text: "approve", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
    actionRange.conditionalFormats.add("containsText", { text: "review", format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } } });
    actionRange.conditionalFormats.add("containsText", { text: "reject", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
  }
  if (xlsxName.includes("human_check") && used.columnCount >= 18 && used.rowCount > 1) {
    sheet.getRangeByIndexes(1, 15, used.rowCount - 1, 3).format = { fill: "#FFF7ED", font: { name: "Microsoft YaHei", size: 10, color: "#7C2D12" }, wrapText: true, borders: { preset: "all", style: "thin", color: "#FDBA74" } };
    sheet.getRangeByIndexes(1, 15, used.rowCount - 1, 1).dataValidation = { rule: { type: "list", values: ["approve", "review", "reject"] } };
  }
  const out = await SpreadsheetFile.exportXlsx(wb);
  await out.save(`${base}/${xlsxName}`);
  const preview = await wb.render({ sheetName, range: `A1:H${Math.min(8, used.rowCount)}`, scale: 1, format: "png" });
  await fs.writeFile(`${base}/_${xlsxName}.png`, new Uint8Array(await preview.arrayBuffer()));
  if (xlsxName.includes("human_check")) {
    const previewHuman = await wb.render({ sheetName, range: `N1:R${Math.min(8, used.rowCount)}`, scale: 1, format: "png" });
    await fs.writeFile(`${base}/_${xlsxName}.human_fields.png`, new Uint8Array(await previewHuman.arrayBuffer()));
  }
  const check = await wb.inspect({ kind: "table", range: `${sheetName}!A1:H${Math.min(6, used.rowCount)}`, include: "values,formulas", tableMaxRows: 6, tableMaxCols: 8, maxChars: 2500 });
  const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula errors", maxChars: 1200 });
  return { xlsxName, rows: used.rowCount - 1, columns: used.columnCount, check: check.ndjson, errors: errors.ndjson };
}

const results = [];
for (const spec of specs) results.push(await build(...spec));
await fs.writeFile(`${base}/_workbook_verification.json`, JSON.stringify(results, null, 2), "utf8");
console.log(JSON.stringify(results.map(({xlsxName, rows, columns}) => ({xlsxName, rows, columns}))));
