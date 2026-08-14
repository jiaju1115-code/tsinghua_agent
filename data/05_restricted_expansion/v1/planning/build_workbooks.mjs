import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = String.raw`D:\python_projects\tsinghua_ai`;
const staging = path.join(root, "data_second", "staging_public_baseline_v1");
const restricted = path.join(root, "data_second", "restricted_expansion_v1");
const planning = path.join(restricted, "planning");
const previews = path.join(restricted, "_workbook_previews");
await fs.mkdir(previews, { recursive: true });

const load = async (name) => JSON.parse(await fs.readFile(path.join(planning, name), "utf8"));

const specs = [
  {
    out: path.join(staging, "public_staging_manifest.xlsx"),
    preview: "public_staging_manifest.png",
    title: "Public Staging Manifest",
    subtitle: "V3.2 approve only · candidate baseline · not production",
    sheet: "Manifest",
    rows: await load("_public_manifest_rows.json"),
    columns: ["id", "title", "url", "domain", "source_batch", "category", "content_type", "topic_relevance", "time_status", "content_file", "content_hash", "v3_2_action", "qa_status", "normalized_url", "original_id", "quality_class"],
  },
  {
    out: path.join(staging, "public_staging_gap_analysis.xlsx"),
    preview: "public_staging_gap_analysis.png",
    title: "Public Staging Gap Analysis",
    subtitle: "Restricted quota basis after public approve merge",
    sheet: "Gap Analysis",
    rows: await load("_gap_rows.json"),
    columns: ["category", "public_approve_count", "restricted_priority", "planning_floor", "minimum_gap", "gap_status"],
  },
  {
    out: path.join(planning, "restricted_gap_plan.xlsx"),
    preview: "restricted_gap_plan.png",
    title: "Restricted Gap Plan",
    subtitle: "P0/P1 targeted; P2 only for high-value stable material",
    sheet: "Gap Plan",
    rows: await load("_plan_rows.json"),
    columns: ["category", "public_approve_count", "restricted_priority", "planning_floor", "minimum_gap", "gap_status"],
  },
  {
    out: path.join(planning, "restricted_seed_urls.xlsx"),
    preview: "restricted_seed_urls.png",
    title: "Restricted Seed URLs",
    subtitle: "23 prior login_required records with independent value judgement",
    sheet: "Seeds",
    rows: await load("_seed_rows.json"),
    columns: ["seed_id", "title", "url", "normalized_url", "original_category", "discovery_source", "previous_failure_reason", "domain", "priority", "recommended_for_authenticated_fetch", "value_judgement", "parent_url"],
  },
];

const colors = { navy: "#16324F", teal: "#1F7A8C", pale: "#E8F1F5", grid: "#D8E2E8", text: "#172B3A", amber: "#FFF3CD", red: "#FDE2E2" };

for (const spec of specs) {
  const wb = Workbook.create();
  const ws = wb.worksheets.add(spec.sheet);
  ws.showGridLines = false;
  const cols = spec.columns.length;
  const endCol = toCol(cols);
  ws.getRange(`A1:${endCol}1`).merge();
  ws.getRange("A1").values = [[spec.title]];
  ws.getRange(`A2:${endCol}2`).merge();
  ws.getRange("A2").values = [[spec.subtitle]];
  ws.getRange(`A1:${endCol}1`).format = { fill: colors.navy, font: { color: "#FFFFFF", bold: true, size: 16 }, rowHeight: 28 };
  ws.getRange(`A2:${endCol}2`).format = { fill: colors.pale, font: { color: colors.text, italic: true, size: 10 }, rowHeight: 22 };
  ws.getRange(`A4:${endCol}4`).values = [spec.columns];
  ws.getRange(`A4:${endCol}4`).format = { fill: colors.teal, font: { color: "#FFFFFF", bold: true }, wrapText: true, rowHeight: 30, borders: { preset: "all", style: "thin", color: colors.grid } };
  if (spec.rows.length) {
    const matrix = spec.rows.map((r) => spec.columns.map((c) => r[c] ?? ""));
    ws.getRange(`A5:${endCol}${4 + matrix.length}`).values = matrix;
    ws.getRange(`A5:${endCol}${4 + matrix.length}`).format = { font: { color: colors.text, size: 9 }, wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: colors.grid } };
    if (spec.columns.includes("gap_status")) {
      const c = toCol(spec.columns.indexOf("gap_status") + 1);
      ws.getRange(`${c}5:${c}${4 + matrix.length}`).conditionalFormats.add("containsText", { text: "明显不足", format: { fill: colors.red, font: { color: "#8B1E1E", bold: true } } });
    }
    if (spec.columns.includes("recommended_for_authenticated_fetch")) {
      const c = toCol(spec.columns.indexOf("recommended_for_authenticated_fetch") + 1);
      ws.getRange(`${c}5:${c}${4 + matrix.length}`).conditionalFormats.add("containsText", { text: "conditional", format: { fill: colors.amber } });
    }
    const table = ws.tables.add(`A4:${endCol}${4 + matrix.length}`, true, `T_${spec.sheet.replace(/\W/g, "_")}`);
    table.style = "TableStyleMedium2";
  }
  ws.freezePanes.freezeRows(4);
  ws.getUsedRange().format.autofitColumns();
  ws.getUsedRange().format.autofitRows();
  for (let i = 1; i <= cols; i++) {
    const c = toCol(i);
    let px = 130;
    const name = spec.columns[i - 1];
    if (["title", "url", "normalized_url", "content_file", "value_judgement", "parent_url"].includes(name)) px = name === "title" || name === "value_judgement" ? 240 : 300;
    if (["content_hash"].includes(name)) px = 260;
    ws.getRange(`${c}:${c}`).format.columnWidthPx = px;
  }
  const preview = await wb.render({ sheetName: spec.sheet, range: `A1:${endCol}${Math.min(20, 4 + spec.rows.length)}`, scale: 1, format: "png" });
  await fs.writeFile(path.join(previews, spec.preview), new Uint8Array(await preview.arrayBuffer()));
  const inspected = await wb.inspect({ kind: "sheet,region", sheetId: spec.sheet, range: `A1:${endCol}${Math.min(10, 4 + spec.rows.length)}`, maxChars: 2500, tableMaxRows: 6, tableMaxCols: Math.min(cols, 12) });
  await fs.writeFile(path.join(previews, spec.preview.replace(".png", ".inspect.json")), JSON.stringify(inspected, null, 2), "utf8");
  const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 3000 });
  await fs.writeFile(path.join(previews, spec.preview.replace(".png", ".errors.json")), JSON.stringify(errors, null, 2), "utf8");
  const output = await SpreadsheetFile.exportXlsx(wb);
  await output.save(spec.out);
  console.log(JSON.stringify({ output: spec.out, rows: spec.rows.length, preview: path.join(previews, spec.preview) }));
}

function toCol(n) {
  let s = "";
  while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26); }
  return s;
}
