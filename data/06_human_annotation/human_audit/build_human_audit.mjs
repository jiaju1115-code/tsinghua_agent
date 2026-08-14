import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "D:/python_projects/tsinghua_ai/data_second";
const outputDir = path.join(root, "human_audit");
const workDir = path.join(outputDir, "_work");
const publicPath = path.join(root, "staging_public_baseline_v1/public_staging_manifest.xlsx");
const restrictedPath = path.join(root, "restricted_expansion_v1/candidates/restricted_approved_candidates.xlsx");
const outputPath = path.join(outputDir, "human_audit_sample.xlsx");
const seed = 20260813;
const publicTarget = 50;
const priorityCategories = [
  "学生事务",
  "餐饮服务",
  "交通服务",
  "体育与场馆",
  "奖助与资助",
  "就业与职业发展",
  "校园综合服务",
  "校园访问",
];

function mulberry32(initialSeed) {
  let state = initialSeed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffle(values, random) {
  const result = [...values];
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function countBy(rows, key) {
  const counts = {};
  for (const row of rows) counts[row[key]] = (counts[row[key]] ?? 0) + 1;
  return Object.fromEntries(Object.entries(counts).sort(([a], [b]) => a.localeCompare(b, "zh-CN")));
}

async function readTable(filePath, sheetName, rangeAddress) {
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(filePath));
  const values = workbook.worksheets.getItem(sheetName).getRange(rangeAddress).values;
  const header = values[0];
  return values.slice(1).map((row) => Object.fromEntries(header.map((name, index) => [name, row[index]])));
}

function allocateLargestRemainder(categoryCounts, target) {
  const categories = Object.keys(categoryCounts).sort((a, b) => a.localeCompare(b, "zh-CN"));
  const population = categories.reduce((sum, category) => sum + categoryCounts[category], 0);
  const allocations = {};
  const remainders = [];
  let allocated = 0;
  for (const category of categories) {
    const exact = (target * categoryCounts[category]) / population;
    const base = Math.floor(exact);
    allocations[category] = base;
    allocated += base;
    remainders.push({ category, remainder: exact - base });
  }
  remainders.sort((a, b) => b.remainder - a.remainder || a.category.localeCompare(b.category, "zh-CN"));
  for (let i = 0; i < target - allocated; i += 1) allocations[remainders[i].category] += 1;
  return allocations;
}

await fs.mkdir(workDir, { recursive: true });

const publicData = await readTable(publicPath, "Manifest", "A4:P238");
const restrictedData = await readTable(restrictedPath, "Approved", "A4:L8");
if (publicData.length !== 234 || restrictedData.length !== 4) {
  throw new Error(`Unexpected input counts: public=${publicData.length}, restricted=${restrictedData.length}`);
}
if (publicData.some((row) => row.v3_2_action !== "approve") || restrictedData.some((row) => row.v3_2_action !== "approve")) {
  throw new Error("Input includes a row whose V3.2 action is not approve.");
}

const random = mulberry32(seed);
const priorityPublic = publicData.filter((row) => priorityCategories.includes(row.category));
const nonPriorityPublic = publicData.filter((row) => !priorityCategories.includes(row.category));
const remainingTarget = publicTarget - priorityPublic.length;
if (remainingTarget < 0) throw new Error("Priority categories exceed the public sample target.");
const nonPriorityCounts = countBy(nonPriorityPublic, "category");
const nonPriorityAllocation = allocateLargestRemainder(nonPriorityCounts, remainingTarget);
const supplement = [];
for (const category of Object.keys(nonPriorityAllocation).sort((a, b) => a.localeCompare(b, "zh-CN"))) {
  const pool = nonPriorityPublic.filter((row) => row.category === category);
  supplement.push(...shuffle(pool, random).slice(0, nonPriorityAllocation[category]));
}
const selectedPublic = [...priorityPublic, ...supplement];
if (selectedPublic.length !== publicTarget || new Set(selectedPublic.map((row) => row.id)).size !== publicTarget) {
  throw new Error("Public sample does not contain exactly 50 unique rows.");
}

const auditRows = [
  ...selectedPublic.map((row) => ({
    sample_id: row.id,
    source: "staging_public_baseline_v1",
    source_type: "public",
    title: row.title,
    url: row.url,
    category: row.category,
    content_path: `staging_public_baseline_v1/${String(row.content_file).replaceAll("\\\\", "/")}`,
    v3_2_decision: row.v3_2_action,
    human_valid: null,
    category_correct: null,
    content_complete: null,
    useful_for_qa: null,
    human_note: null,
  })),
  ...restrictedData.map((row) => ({
    sample_id: row.restricted_id,
    source: "restricted_expansion_v1",
    source_type: "restricted",
    title: row.title,
    url: row.url,
    category: row.category,
    content_path: `restricted_expansion_v1/${String(row.source_file).replaceAll("\\\\", "/")}`,
    v3_2_decision: row.v3_2_action,
    human_valid: null,
    category_correct: null,
    content_complete: null,
    useful_for_qa: null,
    human_note: null,
  })),
];
const shuffledAuditRows = shuffle(auditRows, random);
if (shuffledAuditRows.length !== 54 || restrictedData.some((row) => !shuffledAuditRows.some((audit) => audit.sample_id === row.restricted_id))) {
  throw new Error("Final sample must contain 54 rows and all four Restricted rows.");
}

const headers = [
  "sample_id", "source", "source_type", "title", "url", "category", "content_path", "v3_2_decision",
  "human_valid", "category_correct", "content_complete", "useful_for_qa", "human_note",
];
const matrix = shuffledAuditRows.map((row) => headers.map((header) => row[header]));

const workbook = Workbook.create();
const auditSheet = workbook.worksheets.add("Human Audit");
const summarySheet = workbook.worksheets.add("Sampling Summary");

auditSheet.showGridLines = false;
auditSheet.getRange("A1:M1").merge();
auditSheet.getRange("A1").values = [["Human Audit Sample · Public 50 + Restricted 4"]];
auditSheet.getRange("A2:M2").merge();
auditSheet.getRange("A2").values = [["黄色列由人工填写；程序未预填任何人工结论。固定随机种子：20260813"]];
auditSheet.getRange("A4:M4").values = [headers];
auditSheet.getRange(`A5:M${4 + matrix.length}`).values = matrix;
auditSheet.tables.add(`A4:M${4 + matrix.length}`, true, "HumanAuditSample").style = "TableStyleMedium2";
auditSheet.freezePanes.freezeRows(4);
auditSheet.freezePanes.freezeColumns(3);

auditSheet.getRange("A1:M1").format = {
  fill: "#17324D",
  font: { bold: true, color: "#FFFFFF", size: 16 },
  horizontalAlignment: "left",
  verticalAlignment: "center",
};
auditSheet.getRange("A2:M2").format = {
  fill: "#EAF0F6",
  font: { color: "#334155", italic: true, size: 10 },
  verticalAlignment: "center",
};
auditSheet.getRange("A4:M4").format = {
  fill: "#2B6F77",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
auditSheet.getRange(`I5:M${4 + matrix.length}`).format = {
  fill: "#FFF4CC",
  font: { color: "#6B4F00" },
  verticalAlignment: "top",
  wrapText: true,
};
auditSheet.getRange(`A5:H${4 + matrix.length}`).format = { verticalAlignment: "top" };
auditSheet.getRange(`D5:G${4 + matrix.length}`).format.wrapText = true;
auditSheet.getRange(`I5:L${4 + matrix.length}`).dataValidation = {
  rule: { type: "list", values: ["是", "否", "不确定"] },
};
auditSheet.getRange("A1:M1").format.rowHeight = 30;
auditSheet.getRange("A2:M2").format.rowHeight = 24;
auditSheet.getRange("A4:M4").format.rowHeight = 34;
auditSheet.getRange("A:A").format.columnWidth = 16;
auditSheet.getRange("B:B").format.columnWidth = 25;
auditSheet.getRange("C:C").format.columnWidth = 13;
auditSheet.getRange("D:D").format.columnWidth = 34;
auditSheet.getRange("E:E").format.columnWidth = 45;
auditSheet.getRange("F:F").format.columnWidth = 20;
auditSheet.getRange("G:G").format.columnWidth = 42;
auditSheet.getRange("H:H").format.columnWidth = 15;
auditSheet.getRange("I:L").format.columnWidth = 16;
auditSheet.getRange("M:M").format.columnWidth = 30;

const publicPopulationCounts = countBy(publicData, "category");
const publicSampleCounts = countBy(selectedPublic, "category");
const restrictedSampleCounts = countBy(restrictedData, "category");
const allCategories = [...new Set([...Object.keys(publicPopulationCounts), ...Object.keys(restrictedSampleCounts), ...priorityCategories])]
  .sort((a, b) => a.localeCompare(b, "zh-CN"));

summarySheet.showGridLines = false;
summarySheet.getRange("A1:D1").merge();
summarySheet.getRange("A1").values = [["Sampling Summary"]];
summarySheet.getRange("A3:B8").values = [
  ["随机种子", seed],
  ["Public population", publicData.length],
  ["Public sample", null],
  ["Restricted population", restrictedData.length],
  ["Restricted sample", null],
  ["Total sample", null],
];
summarySheet.getRange("B5").formulas = [[`=COUNTIF('Human Audit'!C5:C58,"public")`]];
summarySheet.getRange("B7").formulas = [[`=COUNTIF('Human Audit'!C5:C58,"restricted")`]];
summarySheet.getRange("B8").formulas = [[`=COUNTA('Human Audit'!A5:A58)`]];
summarySheet.getRange("A10:D10").values = [["category", "Public population", "Public sample", "Restricted sample"]];
summarySheet.getRange(`A11:A${10 + allCategories.length}`).values = allCategories.map((category) => [category]);
summarySheet.getRange(`B11:B${10 + allCategories.length}`).values = allCategories.map((category) => [publicPopulationCounts[category] ?? 0]);
for (let i = 0; i < allCategories.length; i += 1) {
  const row = 11 + i;
  summarySheet.getRange(`C${row}`).formulas = [[`=COUNTIFS('Human Audit'!F5:F58,A${row},'Human Audit'!C5:C58,"public")`]];
  summarySheet.getRange(`D${row}`).formulas = [[`=COUNTIFS('Human Audit'!F5:F58,A${row},'Human Audit'!C5:C58,"restricted")`]];
}
summarySheet.tables.add(`A10:D${10 + allCategories.length}`, true, "SamplingSummary").style = "TableStyleMedium2";
summarySheet.freezePanes.freezeRows(10);
summarySheet.getRange("A1:D1").format = {
  fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 }, verticalAlignment: "center",
};
summarySheet.getRange("A3:A8").format = { fill: "#EAF0F6", font: { bold: true, color: "#17324D" } };
summarySheet.getRange("B3:B8").format = { fill: "#F8FAFC", horizontalAlignment: "right", numberFormat: "#,##0" };
summarySheet.getRange("A10:D10").format = {
  fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true,
};
summarySheet.getRange(`B11:D${10 + allCategories.length}`).format.numberFormat = "#,##0";
summarySheet.getRange("A:A").format.columnWidth = 24;
summarySheet.getRange("B:D").format.columnWidth = 21;
summarySheet.getRange("A1:D1").format.rowHeight = 30;
summarySheet.getRange("A10:D10").format.rowHeight = 32;

const humanFieldIndexes = [8, 9, 10, 11, 12];
for (const row of shuffledAuditRows) {
  for (const index of humanFieldIndexes) {
    if (headers.map((header) => row[header])[index] !== null) throw new Error("A human audit field was prefilled.");
  }
}

const inspectAudit = await workbook.inspect({
  kind: "table",
  range: "'Human Audit'!A4:M12",
  include: "values,formulas",
  tableMaxRows: 9,
  tableMaxCols: 13,
  maxChars: 10000,
});
const inspectSummary = await workbook.inspect({
  kind: "table",
  range: `'Sampling Summary'!A1:D${10 + allCategories.length}`,
  include: "values,formulas",
  tableMaxRows: 40,
  tableMaxCols: 4,
  maxChars: 12000,
});
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});

const auditPreview = await workbook.render({ sheetName: "Human Audit", range: "A1:M15", scale: 1, format: "png" });
const summaryPreview = await workbook.render({ sheetName: "Sampling Summary", autoCrop: "all", scale: 1.5, format: "png" });
await fs.writeFile(path.join(workDir, "human_audit_preview.png"), new Uint8Array(await auditPreview.arrayBuffer()));
await fs.writeFile(path.join(workDir, "sampling_summary_preview.png"), new Uint8Array(await summaryPreview.arrayBuffer()));

await fs.mkdir(outputDir, { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

const exportedWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const exportedAuditSheet = exportedWorkbook.worksheets.getItem("Human Audit");
const exportedIds = exportedAuditSheet.getRange("A5:A58").values.flat().filter((value) => value !== null && value !== "");
const exportedHumanValues = exportedAuditSheet.getRange("I5:M58").values.flat();
if (exportedIds.length !== 54 || new Set(exportedIds).size !== 54) {
  throw new Error("Exported workbook does not contain 54 unique sample IDs.");
}
if (exportedHumanValues.some((value) => value !== null && value !== "")) {
  throw new Error("Exported workbook contains a prefilled human audit value.");
}

const samplingRecord = {
  seed,
  publicPopulation: publicData.length,
  publicSample: selectedPublic.length,
  restrictedPopulation: restrictedData.length,
  restrictedSample: restrictedData.length,
  totalSample: shuffledAuditRows.length,
  priorityCategories,
  priorityPublicIncluded: priorityPublic.length,
  absentPriorityPublicCategories: priorityCategories.filter((category) => !publicPopulationCounts[category]),
  remainingTarget,
  nonPriorityAllocation,
  publicPopulationCounts,
  publicSampleCounts,
  restrictedSampleCounts,
  selectedPublicIds: selectedPublic.map((row) => row.id).sort(),
  selectedRestrictedIds: restrictedData.map((row) => row.restricted_id).sort(),
  humanFieldsBlank: true,
};
await fs.writeFile(path.join(workDir, "sampling_record.json"), JSON.stringify(samplingRecord, null, 2), "utf8");
await fs.writeFile(path.join(workDir, "audit_inspect.ndjson"), inspectAudit.ndjson, "utf8");
await fs.writeFile(path.join(workDir, "summary_inspect.ndjson"), inspectSummary.ndjson, "utf8");
await fs.writeFile(path.join(workDir, "formula_errors.ndjson"), errors.ndjson, "utf8");
await fs.writeFile(path.join(workDir, "export_verification.json"), JSON.stringify({
  exportedSampleIds: exportedIds.length,
  exportedUniqueSampleIds: new Set(exportedIds).size,
  exportedHumanFieldsBlank: true,
}, null, 2), "utf8");
console.log(JSON.stringify(samplingRecord, null, 2));
console.log(`FORMULA_SCAN=${errors.ndjson}`);
console.log(`OUTPUT=${outputPath}`);
