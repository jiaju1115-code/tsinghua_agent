import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const base = "D:/python_projects/tsinghua_ai/data_second/public_rebuild_v1";
const specs = [
  ["source_manifest/public_v1_300_urls.json", "source_manifest/public_v1_300_urls.xlsx", "固定300条URL", "固定 300 条 URL 清单"],
  ["diagnostics/public_v1_300_rebuild_quality.json", "diagnostics/public_v1_300_rebuild_quality.xlsx", "正文质量", "固定 300 条重建正文质量"],
  ["diagnostics/rebuild_extraction_failed.json", "diagnostics/rebuild_extraction_failed.xlsx", "失败记录", "正文抽取失败记录"],
  ["list_pages/rebuild_list_pages.json", "list_pages/rebuild_list_pages.xlsx", "列表页", "List Page 分流记录"],
  ["follow_pages/followed_detail_pages.json", "follow_pages/followed_detail_pages.xlsx", "下钻详情", "一层下钻详情页"],
  ["audit/public_rebuild_v1_all_audited.json", "audit/public_rebuild_v1_all_audited.xlsx", "全部审核", "Prompt V2 全部审核结果"],
  ["audit/public_rebuild_v1_approved.json", "audit/public_rebuild_v1_approved.xlsx", "Approve", "正式知识库候选（Approve）"],
  ["audit/public_rebuild_v1_review.json", "audit/public_rebuild_v1_review.xlsx", "Review", "人工复核（Review）"],
  ["audit/public_rebuild_v1_rejected.json", "audit/public_rebuild_v1_rejected.xlsx", "Reject", "淘汰记录（Reject）"],
  ["human_check/public_rebuild_v1_human_check.json", "human_check/public_rebuild_v1_human_check.xlsx", "人工抽检", "Public Rebuild V1 人工抽检（30 条）"],
];

const widthFor = (h) => {
  if (/^(id|old_id)$/.test(h)) return 17;
  if (/url|source_file/.test(h)) return 46;
  if (/title/.test(h)) return 32;
  if (/reason|evidence|question|note/.test(h)) return 46;
  if (/selector|method|category|content_type|quality_class/.test(h)) return 23;
  if (/time/.test(h)) return 23;
  if (/length|count|ratio|score|status|pass|removed|action|priority/.test(h)) return 16;
  return 20;
};

const excelCol = (n) => {
  let s = "";
  while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26); }
  return s;
};

async function build(spec, index) {
  const [jsonRel, xlsxRel, sheetName, title] = spec;
  const rows = JSON.parse(await fs.readFile(path.join(base, jsonRel), "utf8"));
  const headers = Object.keys(rows[0] ?? {});
  const wb = Workbook.create();
  const sheet = wb.worksheets.add(sheetName);
  sheet.showGridLines = false;
  sheet.getCell(0, 0).values = [[title]];
  sheet.getRangeByIndexes(0, 0, 1, Math.max(headers.length, 1)).format = {
    fill: "#0F4C5C", font: { name: "Microsoft YaHei", size: 15, bold: true, color: "#FFFFFF" },
    verticalAlignment: "center", rowHeight: 32,
  };
  sheet.getCell(1, 0).values = [[`生成时间：2026-08-12｜数据行：${rows.length}｜来源字段中保留公开网页 URL 以便追溯`]];
  sheet.getRangeByIndexes(1, 0, 1, Math.max(headers.length, 1)).format = { fill: "#E7F3F5", font: { name: "Microsoft YaHei", size: 9, color: "#34515A" }, rowHeight: 23 };

  const matrix = [headers, ...rows.map(r => headers.map(h => {
    const v = r[h] ?? "";
    if ((h === "crawl_time" || h === "reviewed_at") && typeof v === "string" && v) {
      const d = new Date(v); return Number.isNaN(d.getTime()) ? v : d;
    }
    return v;
  }))];
  const data = sheet.getRangeByIndexes(2, 0, matrix.length, Math.max(headers.length, 1));
  data.values = matrix.length ? matrix : [[""]];
  const header = sheet.getRangeByIndexes(2, 0, 1, Math.max(headers.length, 1));
  header.format = {
    fill: "#137C8B", font: { name: "Microsoft YaHei", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, rowHeight: 34,
    borders: { bottom: { style: "medium", color: "#0F4C5C" } },
  };
  if (rows.length) {
    const body = sheet.getRangeByIndexes(3, 0, rows.length, headers.length);
    body.format = {
      font: { name: "Microsoft YaHei", size: 9, color: "#1F2937" }, verticalAlignment: "top", wrapText: true,
      rowHeight: 44, borders: { insideHorizontal: { style: "thin", color: "#E5E7EB" } },
    };
    for (let c = 0; c < headers.length; c++) {
      const h = headers[c];
      sheet.getRangeByIndexes(2, c, rows.length + 1, 1).format.columnWidth = widthFor(h);
      if (/length|count|ratio|score|priority|status/.test(h)) body.getColumn(c).format.horizontalAlignment = "right";
      if (h === "crawl_time" || h === "reviewed_at") body.getColumn(c).format.numberFormat = "yyyy-mm-dd hh:mm:ss";
    }
    const table = sheet.tables.add(`A3:${excelCol(headers.length)}${rows.length + 3}`, true, `T_Rebuild_${String(index).padStart(2, "0")}`);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;

    for (const actionHeader of ["action", "rebuild_action", "old_action"]) {
      const c = headers.indexOf(actionHeader);
      if (c >= 0) {
        const range = sheet.getRangeByIndexes(3, c, rows.length, 1);
        range.conditionalFormats.add("containsText", { text: "approve", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
        range.conditionalFormats.add("containsText", { text: "review", format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } } });
        range.conditionalFormats.add("containsText", { text: "reject", format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } } });
        range.conditionalFormats.add("containsText", { text: "extraction_failed", format: { fill: "#E5E7EB", font: { color: "#4B5563" } } });
      }
    }
    const q = headers.indexOf("quality_gate_pass");
    if (q >= 0) {
      const range = sheet.getRangeByIndexes(3, q, rows.length, 1);
      range.conditionalFormats.add("containsText", { text: "TRUE", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
      range.conditionalFormats.add("containsText", { text: "FALSE", format: { fill: "#FEE2E2", font: { color: "#991B1B" } } });
    }
    for (const humanHeader of ["human_action", "human_category", "human_note"]) {
      const c = headers.indexOf(humanHeader);
      if (c >= 0) sheet.getRangeByIndexes(3, c, rows.length, 1).format = {
        fill: "#FFF7ED", font: { name: "Microsoft YaHei", size: 9, color: "#7C2D12" },
        verticalAlignment: "top", wrapText: true, borders: { insideHorizontal: { style: "thin", color: "#FED7AA" } },
      };
    }
    const ha = headers.indexOf("human_action");
    if (ha >= 0) sheet.getRangeByIndexes(3, ha, rows.length, 1).dataValidation = { rule: { type: "list", values: ["approve", "review", "reject"] } };
  }
  sheet.freezePanes.freezeRows(3);
  sheet.freezePanes.freezeColumns(Math.min(2, headers.length));

  const outPath = path.join(base, xlsxRel);
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(wb);
  await xlsx.save(outPath);

  const preview = await wb.render({ sheetName, range: `A1:${excelCol(Math.min(headers.length, 8))}${Math.min(rows.length + 3, 10)}`, scale: 1, format: "png" });
  const previewPath = path.join(base, "intermediate", `preview_${String(index).padStart(2, "0")}.png`);
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  let humanPreviewPath = "";
  if (headers.includes("human_action")) {
    const start = Math.max(1, headers.indexOf("human_action") - 2) + 1;
    const hp = await wb.render({ sheetName, range: `${excelCol(start)}1:${excelCol(headers.length)}${Math.min(rows.length + 3, 10)}`, scale: 1, format: "png" });
    humanPreviewPath = path.join(base, "intermediate", `preview_${String(index).padStart(2, "0")}_human.png`);
    await fs.writeFile(humanPreviewPath, new Uint8Array(await hp.arrayBuffer()));
  }
  // These deliverables intentionally contain no formulas. The compact table
  // source-row reconciliation plus successful export/render is the relevant verification.
  return { xlsxRel, rows: rows.length, columns: headers.length, previewPath, humanPreviewPath, formulaErrors: [], formulaCount: 0 };
}

const verification = [];
for (let i = 0; i < specs.length; i++) verification.push(await build(specs[i], i + 1));
await fs.writeFile(path.join(base, "intermediate", "workbook_verification.json"), JSON.stringify(verification, null, 2), "utf8");
console.log(JSON.stringify(verification.map(x => ({ file: x.xlsxRel, rows: x.rows, columns: x.columns }))));
