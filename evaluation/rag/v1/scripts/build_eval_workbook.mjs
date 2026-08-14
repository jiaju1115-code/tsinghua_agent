import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const v1 = path.resolve(import.meta.dirname, "..");
const workDir = path.join(v1, "logs", "workbook_qa");
const queries = (await fs.readFile(path.join(v1, "evaluation", "eval_queries.jsonl"), "utf8"))
  .trim().split(/\r?\n/).map((line) => JSON.parse(line));
const chunks = (await fs.readFile(path.resolve(v1, "..", "v0", "chunks", "chunks.jsonl"), "utf8"))
  .trim().split(/\r?\n/).map((line) => JSON.parse(line));
const titleBySource = new Map(chunks.map((row) => [row.source_id, row.title]));

const headers = ["query_id", "query", "category", "expected_source_id", "expected_title", "expected_evidence_keyword",
  "provenance", "eval_status", "expected_source_status", "previous_v0_verdict"];
const rows = queries.map((q) => [q.query_id, q.query, q.category, q.expected_source_id,
  q.expected_source_id ? (titleBySource.get(q.expected_source_id) ?? "SOURCE_ID_NOT_FOUND") : "",
  q.expected_evidence_keyword, q.provenance, q.eval_status, q.expected_source_status, q.previous_v0_verdict]);

const wb = Workbook.create();
const qs = wb.worksheets.add("Query Set");
const cov = wb.worksheets.add("Coverage");
qs.showGridLines = false;
qs.getRange("A1:J1").merge();
qs.getRange("A1").values = [["RAG V1 Retrieval Evaluation Set"]];
qs.getRange("A2:J2").merge();
qs.getRange("A2").values = [["10 Existing Smoke queries are frozen verbatim; added queries are explicitly PROVISIONAL_EVAL, not Gold Evaluation."]];
qs.getRange("A4:J4").values = [headers];
qs.getRange(`A5:J${4 + rows.length}`).values = rows;
qs.tables.add(`A4:J${4 + rows.length}`, true, "RagV1EvalSet").style = "TableStyleMedium2";
qs.freezePanes.freezeRows(4);
qs.freezePanes.freezeColumns(2);
qs.getRange("A1:J1").format = { fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 }, verticalAlignment: "center" };
qs.getRange("A2:J2").format = { fill: "#EAF0F6", font: { italic: true, color: "#334155", size: 10 }, wrapText: true };
qs.getRange("A4:J4").format = { fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
qs.getRange(`A5:J${4 + rows.length}`).format = { verticalAlignment: "top", wrapText: true };
qs.getRange("A:A").format.columnWidth = 14;
qs.getRange("B:B").format.columnWidth = 45;
qs.getRange("C:C").format.columnWidth = 20;
qs.getRange("D:D").format.columnWidth = 18;
qs.getRange("E:E").format.columnWidth = 38;
qs.getRange("F:F").format.columnWidth = 30;
qs.getRange("G:J").format.columnWidth = 22;
qs.getRange("A1:J1").format.rowHeight = 30;
qs.getRange("A2:J2").format.rowHeight = 28;
qs.getRange("A4:J4").format.rowHeight = 34;

const categories = [...new Set(queries.map((q) => q.category))].sort((a, b) => a.localeCompare(b, "zh-CN"));
cov.showGridLines = false;
cov.getRange("A1:D1").merge();
cov.getRange("A1").values = [["Evaluation Coverage"]];
cov.getRange("A3:B8").values = [["Total queries", null], ["Existing Smoke", null], ["Provisional Evaluation", null],
  ["Reliable expected source", null], ["Uncertain expected source", null], ["Covered categories", categories.length]];
cov.getRange("B3").formulas = [["=COUNTA('Query Set'!A5:A1000)"]];
cov.getRange("B4").formulas = [["=COUNTIF('Query Set'!H5:H1000,\"EXISTING_SMOKE\")"]];
cov.getRange("B5").formulas = [["=COUNTIF('Query Set'!H5:H1000,\"PROVISIONAL_EVAL\")"]];
cov.getRange("B6").formulas = [["=COUNTIF('Query Set'!I5:I1000,\"reliable\")"]];
cov.getRange("B7").formulas = [["=COUNTIF('Query Set'!I5:I1000,\"expected_source_uncertain\")"]];
cov.getRange("A10:D10").values = [["category", "all queries", "existing smoke", "provisional"]];
cov.getRange(`A11:A${10 + categories.length}`).values = categories.map((c) => [c]);
for (let i = 0; i < categories.length; i++) {
  const r = 11 + i;
  cov.getRange(`B${r}`).formulas = [[`=COUNTIF('Query Set'!C5:C1000,A${r})`]];
  cov.getRange(`C${r}`).formulas = [[`=COUNTIFS('Query Set'!C5:C1000,A${r},'Query Set'!H5:H1000,"EXISTING_SMOKE")`]];
  cov.getRange(`D${r}`).formulas = [[`=COUNTIFS('Query Set'!C5:C1000,A${r},'Query Set'!H5:H1000,"PROVISIONAL_EVAL")`]];
}
cov.tables.add(`A10:D${10 + categories.length}`, true, "CoverageByCategory").style = "TableStyleMedium2";
cov.freezePanes.freezeRows(10);
cov.getRange("A1:D1").format = { fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 } };
cov.getRange("A3:A8").format = { fill: "#EAF0F6", font: { bold: true, color: "#17324D" } };
cov.getRange("A10:D10").format = { fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
cov.getRange("A:A").format.columnWidth = 28;
cov.getRange("B:D").format.columnWidth = 19;

await fs.mkdir(workDir, { recursive: true });
const inspect = await wb.inspect({ kind: "table", range: `'Query Set'!A1:J${4 + rows.length}`, include: "values,formulas", tableMaxRows: 50, tableMaxCols: 10, maxChars: 20000 });
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
const qPreview = await wb.render({ sheetName: "Query Set", range: "A1:J14", scale: 1, format: "png" });
const cPreview = await wb.render({ sheetName: "Coverage", autoCrop: "all", scale: 1.5, format: "png" });
await fs.writeFile(path.join(workDir, "eval_query_set.png"), new Uint8Array(await qPreview.arrayBuffer()));
await fs.writeFile(path.join(workDir, "eval_coverage.png"), new Uint8Array(await cPreview.arrayBuffer()));
await fs.writeFile(path.join(workDir, "eval_inspect.ndjson"), inspect.ndjson, "utf8");
await fs.writeFile(path.join(workDir, "eval_formula_errors.ndjson"), errors.ndjson, "utf8");
const output = path.join(v1, "evaluation", "rag_v1_eval_set.xlsx");
await (await SpreadsheetFile.exportXlsx(wb)).save(output);
const roundTrip = await SpreadsheetFile.importXlsx(await FileBlob.load(output));
const ids = roundTrip.worksheets.getItem("Query Set").getRange(`A5:A${4 + rows.length}`).values.flat().filter(Boolean);
if (ids.length !== rows.length || new Set(ids).size !== rows.length) throw new Error("Round-trip query count or ID uniqueness failed");
console.log(JSON.stringify({ output, queries: ids.length, existing_smoke: queries.filter((q) => q.eval_status === "EXISTING_SMOKE").length,
  provisional: queries.filter((q) => q.eval_status === "PROVISIONAL_EVAL").length, formula_scan: errors.ndjson }));
