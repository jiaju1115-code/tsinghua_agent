import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "D:/python_projects/tsinghua_ai/data_second/model_selection";
const output = path.join(root, "base_model_scorecard.xlsx");
const work = path.join(root, "_work");
await fs.mkdir(work, { recursive: true });

const weights = [
  ["中文及领域适配潜力", 0.25, "中文基础、校园语料适配潜力；不是聊天能力"],
  ["训练与 PEFT 可行性", 0.20, "LoRA/QLoRA/Full FT 的现实性与兼容风险"],
  ["当前硬件适配", 0.20, "服从 CPU-only、32GB RAM 的本机事实"],
  ["Tokenizer / context", 0.10, "中文 token 效率与上下文窗口"],
  ["License 与公开展示", 0.10, "许可清晰度、门控与公开展示阻力"],
  ["Transformers / PEFT / 推理生态", 0.10, "官方支持、工具链和 RAG 集成"],
  ["复现与工程风险", 0.05, "下载、架构新颖性、环境与部署风险"],
];

const candidates = [
  {
    model: "Qwen/Qwen3.5-2B-Base", publisher: "Qwen", stage: "Pretrained/Base", params: 2,
    weightsGb: 4.24, license: "Apache-2.0", gated: "No", context: 262144, official: "Yes",
    measured: "Tokenizer PASS；完整 CPU benchmark 见 JSONL", recommendation: "推荐",
    scores: [5.0, 4.0, 3.0, 5.0, 5.0, 4.0, 3.5],
    rationale: "中文与长上下文强，权重公开；当前机器不能正式训练，且 Qwen3.5 混合/VL 架构较新。",
  },
  {
    model: "Qwen/Qwen3.5-4B-Base", publisher: "Qwen", stage: "Pretrained/Base", params: 4,
    weightsGb: 8.68, license: "Apache-2.0", gated: "No", context: 262144, official: "Yes",
    measured: "Tokenizer PASS；因 CPU-only 未下载权重实测", recommendation: "第二候选/算力升级",
    scores: [5.0, 3.0, 1.0, 5.0, 5.0, 4.0, 2.5],
    rationale: "潜在能力更高，但约9.32GB BF16权重且无GPU；当前机器不具备现实训练与公平横测条件。",
  },
  {
    model: "Qwen/Qwen3.5-9B-Base", publisher: "Qwen", stage: "Pretrained/Base", params: 9,
    weightsGb: 17.98, license: "Apache-2.0", gated: "No", context: 262144, official: "Yes",
    measured: "Tokenizer PASS；硬件不现实，未下载权重", recommendation: "不进入当前实测",
    scores: [5.0, 2.0, 0.5, 5.0, 5.0, 4.0, 1.5],
    rationale: "参数量和部署成本显著上升；当前无CUDA，无法验证训练可行性，不能因更大而优先。",
  },
  {
    model: "google/gemma-3-1b-pt", publisher: "Google DeepMind", stage: "Pretrained/Base", params: 1,
    weightsGb: 1.86, license: "Gemma", gated: "Manual", context: 32768, official: "Yes",
    measured: "401 gated；Tokenizer/权重未实测", recommendation: "低算力对照（受阻）",
    scores: [3.0, 3.0, 3.5, 3.0, 3.0, 4.0, 2.5],
    rationale: "官方多语言PT模型且较小；HF门控与专用许可增加复现阻力，中文与校园适配证据弱于Qwen。",
  },
  {
    model: "google/gemma-3-270m", publisher: "Google DeepMind", stage: "Pretrained/Base", params: 0.27,
    weightsGb: 0.50, license: "Gemma", gated: "Manual", context: 32768, official: "Yes",
    measured: "401 gated；Tokenizer/权重未实测", recommendation: "管线校验对照（受阻）",
    scores: [2.0, 4.0, 5.0, 3.0, 3.0, 4.0, 3.0],
    rationale: "资源需求最低，适合管线测试；容量过小，不适合作为校园中文智能体最终训练底座。",
  },
];

const wb = Workbook.create();
const score = wb.worksheets.add("Scorecard");
const longlist = wb.worksheets.add("Longlist");
const weightSheet = wb.worksheets.add("Weights & Method");
for (const ws of [score, longlist, weightSheet]) ws.showGridLines = false;

score.getRange("A1:Q1").merge();
score.getRange("A1").values = [["Base Model Selection Scorecard — 2026-08-13"]];
score.getRange("A2:Q2").merge();
score.getRange("A2").values = [["1–5分；加权分=SUMPRODUCT(维度分,权重)/5×100。机械分仅供比较，最终结论必须结合硬件与实测。"]];
const scoreHeaders = ["model_id", "publisher", "stage", "params_B", "weight_GiB", "license", "gated", "context", "中文/领域", "PEFT", "硬件", "Tokenizer/context", "许可/展示", "生态", "复现风险", "weighted_score_100", "技术判断"];
score.getRange("A4:Q4").values = [scoreHeaders];
const scoreMatrix = candidates.map((c) => [c.model, c.publisher, c.stage, c.params, c.weightsGb, c.license, c.gated, c.context, ...c.scores, null, c.recommendation]);
score.getRange(`A5:Q${4 + candidates.length}`).values = scoreMatrix;
for (let i = 0; i < candidates.length; i += 1) {
  const row = 5 + i;
  score.getRange(`P${row}`).formulas = [[`=ROUND((I${row}*'Weights & Method'!B4+J${row}*'Weights & Method'!B5+K${row}*'Weights & Method'!B6+L${row}*'Weights & Method'!B7+M${row}*'Weights & Method'!B8+N${row}*'Weights & Method'!B9+O${row}*'Weights & Method'!B10)/5*100,1)`]];
}
score.tables.add(`A4:Q${4 + candidates.length}`, true, "ModelScorecard").style = "TableStyleMedium2";
score.freezePanes.freezeRows(4);
score.freezePanes.freezeColumns(2);

longlist.getRange("A1:N1").merge();
longlist.getRange("A1").values = [["Official Base Model Longlist"]];
longlist.getRange("A3:N3").values = [["model_id", "official", "base/pretrained", "params_B", "HF weight GiB", "license", "gated", "context", "revision", "tokenizer", "weight benchmark", "training fit", "RAG fit", "notes"]];
const revisions = {
  "Qwen/Qwen3.5-2B-Base": "b1485b2fa6dfa1287294f269f5fb618e03d52d7c",
  "Qwen/Qwen3.5-4B-Base": "1001bb4d826a52d1f399e183466143f4da7b741b",
  "Qwen/Qwen3.5-9B-Base": "68c46c4b3498877f3ef123c856ecfde50c39f404",
  "google/gemma-3-1b-pt": "fcf18a2a879aab110ca39f8bffbccd5d49d8eb29",
  "google/gemma-3-270m": "9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1",
};
const longRows = candidates.map((c) => [c.model, "Yes", "Yes", c.params, c.weightsGb, c.license, c.gated, c.context, revisions[c.model], c.measured.split("；")[0], c.measured, c.recommendation, "High: generator与embedding解耦", c.rationale]);
longlist.getRange(`A4:N${3 + candidates.length}`).values = longRows;
longlist.tables.add(`A3:N${3 + candidates.length}`, true, "ModelLonglist").style = "TableStyleMedium2";
longlist.freezePanes.freezeRows(3);
longlist.freezePanes.freezeColumns(2);

weightSheet.getRange("A1:C1").merge();
weightSheet.getRange("A1").values = [["Weights & Method"]];
weightSheet.getRange("A3:C3").values = [["评分维度", "权重", "解释"]];
weightSheet.getRange("A4:C10").values = weights;
weightSheet.getRange("A12:C12").values = [["数据隔离", "状态", "说明"]];
weightSheet.getRange("A13:C16").values = [
  ["Corpus / Training Data", "未构建", "本阶段未把KB或Gold数据自动转成训练集"],
  ["Knowledge Base", "独立", "PROVISIONAL_KB_V0 仅用于检索"],
  ["Evaluation / Gold Set", "隔离", "未读取、未用于训练"],
  ["Base Model benchmark held-out", "排除训练", "10个固定Public source_id写入heldout_index.json"],
];
weightSheet.getRange("B4:B10").format.numberFormat = "0%";

const titleFmt = { fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 }, verticalAlignment: "center" };
const subFmt = { fill: "#EAF0F6", font: { color: "#334155", italic: true }, verticalAlignment: "center", wrapText: true };
const headerFmt = { fill: "#2B6F77", font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
score.getRange("A1:Q1").format = titleFmt;
score.getRange("A2:Q2").format = subFmt;
score.getRange("A4:Q4").format = headerFmt;
longlist.getRange("A1:N1").format = titleFmt;
longlist.getRange("A3:N3").format = headerFmt;
weightSheet.getRange("A1:C1").format = titleFmt;
weightSheet.getRange("A3:C3").format = headerFmt;
weightSheet.getRange("A12:C12").format = headerFmt;
score.getRange("A1:Q1").format.rowHeight = 30;
score.getRange("A2:Q2").format.rowHeight = 28;
score.getRange("A4:Q4").format.rowHeight = 38;
score.getRange("D5:P9").format.numberFormat = "0.0";
score.getRange("H5:H9").format.numberFormat = "#,##0";
score.getRange("A:A").format.columnWidth = 31;
score.getRange("B:C").format.columnWidth = 19;
score.getRange("D:O").format.columnWidth = 14;
score.getRange("P:P").format.columnWidth = 19;
score.getRange("Q:Q").format.columnWidth = 21;
score.getRange("A4:Q9").format.wrapText = true;
longlist.getRange("A:A").format.columnWidth = 31;
longlist.getRange("B:M").format.columnWidth = 18;
longlist.getRange("N:N").format.columnWidth = 52;
longlist.getRange("A3:N8").format.wrapText = true;
weightSheet.getRange("A:A").format.columnWidth = 30;
weightSheet.getRange("B:B").format.columnWidth = 16;
weightSheet.getRange("C:C").format.columnWidth = 68;
weightSheet.getRange("A1:C16").format.wrapText = true;

const inspect = await wb.inspect({ kind: "table", range: "Scorecard!A1:Q9", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 17, maxChars: 16000 });
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" });
const p1 = await wb.render({ sheetName: "Scorecard", range: "A1:Q9", scale: 1, format: "png" });
const p2 = await wb.render({ sheetName: "Longlist", range: "A1:N8", scale: 1, format: "png" });
await fs.writeFile(path.join(work, "scorecard.png"), new Uint8Array(await p1.arrayBuffer()));
await fs.writeFile(path.join(work, "longlist.png"), new Uint8Array(await p2.arrayBuffer()));
await fs.writeFile(path.join(work, "inspect.ndjson"), inspect.ndjson, "utf8");
await fs.writeFile(path.join(work, "formula_errors.ndjson"), errors.ndjson, "utf8");
const blob = await SpreadsheetFile.exportXlsx(wb);
await blob.save(output);
const roundtrip = await SpreadsheetFile.importXlsx(await FileBlob.load(output));
const verify = await roundtrip.inspect({ kind: "table", range: "Scorecard!A4:Q9", include: "values,formulas", tableMaxRows: 7, tableMaxCols: 17, maxChars: 16000 });
const verifyErrors = await roundtrip.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "roundtrip formula errors" });
await fs.writeFile(path.join(work, "roundtrip_inspect.ndjson"), verify.ndjson, "utf8");
await fs.writeFile(path.join(work, "roundtrip_formula_errors.ndjson"), verifyErrors.ndjson, "utf8");
console.log(JSON.stringify({ output, formulaScan: errors.ndjson }));
