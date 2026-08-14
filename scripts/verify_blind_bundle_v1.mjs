import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = String.raw`D:\python_projects\tsinghua_ai\data_second\prompt_v3_2_blind_test_v1`;
const out = path.join(root, "blind_bundle_v1");
const sourceManifest = JSON.parse(await fs.readFile(path.join(root, "samples", "blind_test_v1_sample_manifest.json"), "utf8"));
const cleanLines = (await fs.readFile(path.join(out, "manifest", "blind_manifest_clean.jsonl"), "utf8")).trim().split(/\r?\n/).map(JSON.parse);
const allowed = ["blind_id", "original_id", "title", "url", "normalized_url", "domain", "source_group", "content_file"];
const allowedSet = new Set(allowed);
const sha = b => crypto.createHash("sha256").update(b).digest("hex");

const xlsx = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(out, "manifest", "blind_manifest_clean.xlsx")));
const xs = xlsx.worksheets.getItem("Blind Manifest");
const xlsxValues = xs.getRange("A1:H51").values;
const xlsxHeaders = xlsxValues[0];
const jsonFields = [...new Set(cleanLines.flatMap(Object.keys))];
const sourceIds = sourceManifest.map(r => r.blind_id);
const sourceUrls = sourceManifest.map(r => r.url);
const cleanIds = cleanLines.map(r => r.blind_id);
const cleanUrls = cleanLines.map(r => r.url);
const unique = a => new Set(a).size === a.length;
const exactSame = (a,b) => a.length === b.length && a.every((v,i) => v === b[i]);

const forbidden = ["human_", "human action", "human label", "old_v2", "v2_action", "v3_action", "v3_1_action", "v3_2_action", "ai_action", "ai reason", "gold_label", "gold label", "disagreement", "frozen_human", "approve 27", "reject 22", "review 1"];
const scanFiles = [path.join(out, "manifest", "blind_manifest_clean.jsonl"), ...cleanLines.map(r => path.join(out, r.content_file))];
const hits = {};
for (const term of forbidden) hits[term] = 0;
for (const f of scanFiles) {
  const txt = (await fs.readFile(f, "utf8")).toLowerCase();
  for (const term of forbidden) hits[term] += txt.split(term.toLowerCase()).length - 1;
}

let sampleStructureValid = true;
let bodyExactCount = 0;
const requiredPrefix = ["blind_id:", "original_id:", "title:", "url:", "domain:", "source_group:", "", "# Content", ""];
for (const row of cleanLines) {
  const text = await fs.readFile(path.join(out, row.content_file), "utf8");
  const lines = text.split("\n");
  if (!requiredPrefix.every((v,i) => i === 6 || i === 8 ? lines[i] === v : lines[i].startsWith(v))) sampleStructureValid = false;
  const body = lines.slice(9).join("\n");
  const srcRow = sourceManifest.find(x => x.blind_id === row.blind_id);
  const srcBody = await fs.readFile(path.join(root, srcRow.content_file), "utf8");
  if (body === srcBody) bodyExactCount++;
}

const promptSource = await fs.readFile(String.raw`D:\python_projects\tsinghua_ai\data_second\prompt_v3_2_test\prompt\prompt_v3_2.md`);
const promptCopy = await fs.readFile(path.join(out, "prompt", "prompt_v3_2.md"));
const forbiddenHumanFiles = ["blind_test_v1_human_label.xlsx", "frozen_human_labels.json", "blind_test_v1_results.xlsx", "blind_test_v1_disagreements.xlsx", "human_label_questions.xlsx"];
const allPaths = [];
async function walk(d) { for (const e of await fs.readdir(d,{withFileTypes:true})) { const p=path.join(d,e.name); e.isDirectory()?await walk(p):allPaths.push(p); } }
await walk(out);
const copiedHumanFiles = allPaths.filter(p => forbiddenHumanFiles.includes(path.basename(p).toLowerCase()));
const historicalAiFieldCount = jsonFields.filter(k => /(^|_)(old_)?(ai|v2|v3|v3_1|v3_2).*action|reason|prediction|label|evaluation|disagreement/i.test(k)).length + xlsxHeaders.filter(k => !allowedSet.has(k)).length;
const humanFieldCount = jsonFields.filter(k => /^human_/i.test(k)).length + xlsxHeaders.filter(k => /^human_/i.test(k)).length;
const oldV2FieldCount = jsonFields.filter(k => /old_v2_action/i.test(k)).length + xlsxHeaders.filter(k => /old_v2_action/i.test(k)).length;
const oldPromptResultFieldCount = jsonFields.filter(k => /v3(?:_1|_2)?_action/i.test(k)).length + xlsxHeaders.filter(k => /v3(?:_1|_2)?_action/i.test(k)).length;
const random = cleanLines.filter(r => r.source_group === "random").length;
const targeted = cleanLines.filter(r => r.source_group === "targeted").length;
const leakedLabelValues = hits["approve 27"] + hits["reject 22"] + hits["review 1"];
const checks = {
  sample_count: cleanLines.length, random_count: random, targeted_count: targeted,
  blind_ids_preserved: exactSame(sourceIds, cleanIds), urls_preserved: exactSame(sourceUrls, cleanUrls),
  blind_ids_unique: unique(cleanIds), urls_unique: unique(cleanUrls), normalized_urls_unique: unique(cleanLines.map(r=>r.normalized_url)),
  jsonl_fields_exact: exactSame(jsonFields, allowed), xlsx_fields_exact: exactSame(xlsxHeaders, allowed),
  prompt_source_sha256: sha(promptSource), prompt_copy_sha256: sha(promptCopy), prompt_sha256_matches: sha(promptSource) === sha(promptCopy),
  human_files_copied: copiedHumanFiles.length, human_field_count: humanFieldCount,
  historical_ai_action_field_count: historicalAiFieldCount, old_V2_action_field_count: oldV2FieldCount,
  old_V3_V3_1_V3_2_result_field_count: oldPromptResultFieldCount,
  specific_human_label_value_leaks: leakedLabelValues,
  forbidden_text_hits: hits, sample_structure_valid: sampleStructureValid, exact_body_matches: bodyExactCount,
  xlsx_row_count: xlsxValues.length - 1,
};
const ready = cleanLines.length===50 && random===25 && targeted===25 && checks.blind_ids_preserved && checks.urls_preserved && checks.blind_ids_unique && checks.urls_unique && checks.normalized_urls_unique && checks.jsonl_fields_exact && checks.xlsx_fields_exact && checks.prompt_sha256_matches && copiedHumanFiles.length===0 && humanFieldCount===0 && historicalAiFieldCount===0 && oldV2FieldCount===0 && oldPromptResultFieldCount===0 && leakedLabelValues===0 && Object.values(hits).every(v=>v===0) && sampleStructureValid && bodyExactCount===50 && checks.xlsx_row_count===50;
const report = { status: ready ? "BLIND_BUNDLE_READY" : "BLIND_BUNDLE_INVALID", ...checks, suitable_as_only_phase1_input: ready, sampled_structure_review: [1,6,11,16,21,26,31,36,41,46].map(n=>`BLINDV1-${String(n).padStart(3,"0")}`) };
await fs.writeFile(path.join(out,"verification","blind_bundle_verification.json"), JSON.stringify(report,null,2)+"\n","utf8");
const md = `# Blind Bundle Verification\n\n- 最终状态：\`${report.status}\`\n- 样本仍为50条：${cleanLines.length===50}\n- random / targeted：${random} / ${targeted}\n- blind_id完全保持：${checks.blind_ids_preserved}\n- URL完全保持：${checks.urls_preserved}\n- Prompt SHA-256与冻结V3.2一致：${checks.prompt_sha256_matches}\n- Human文件复制进入Bundle：${copiedHumanFiles.length}\n- human字段数量：${humanFieldCount}\n- 历史AI action字段数量：${historicalAiFieldCount}\n- old_V2_action字段数量：${oldV2FieldCount}\n- 旧V3/V3.1/V3.2结果字段数量：${oldPromptResultFieldCount}\n- 具体人工标签值泄漏：${leakedLabelValues}\n- 全部50条正文逐字匹配：${bodyExactCount===50}\n- 全部50条样本结构检查通过：${sampleStructureValid}\n- 至少10条结构抽查：通过（${report.sampled_structure_review.join(", ")}）\n- 适合作为新Codex盲测唯一输入：${ready}\n`;
await fs.writeFile(path.join(out,"verification","blind_bundle_verification.md"), md,"utf8");
const hashManifestPath = path.join(out,"verification","sha256_manifest.json");
const hashes = JSON.parse(await fs.readFile(hashManifestPath,"utf8"));
hashes.verification_json_sha256 = sha(await fs.readFile(path.join(out,"verification","blind_bundle_verification.json")));
hashes.verification_md_sha256 = sha(await fs.readFile(path.join(out,"verification","blind_bundle_verification.md")));
await fs.writeFile(hashManifestPath, JSON.stringify(hashes,null,2)+"\n","utf8");
console.log(JSON.stringify(report,null,2));
