import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = String.raw`D:\python_projects\tsinghua_ai\data_second\prompt_v3_2_blind_test_v1`;
const sourceManifestPath = path.join(root, "samples", "blind_test_v1_sample_manifest.json");
const sourcePromptPath = String.raw`D:\python_projects\tsinghua_ai\data_second\prompt_v3_2_test\prompt\prompt_v3_2.md`;
const out = path.join(root, "blind_bundle_v1");
const allowed = ["blind_id", "original_id", "title", "url", "normalized_url", "domain", "source_group", "content_file"];

const sha = (b) => crypto.createHash("sha256").update(b).digest("hex");
const escMeta = (v) => String(v ?? "").replace(/\r?\n/g, " ");

await fs.rm(out, { recursive: true, force: true });
for (const d of ["prompt", "manifest", "samples", "verification"]) await fs.mkdir(path.join(out, d), { recursive: true });

const source = JSON.parse(await fs.readFile(sourceManifestPath, "utf8"));
if (!Array.isArray(source) || source.length !== 50) throw new Error("Frozen manifest is not exactly 50 rows");

const clean = [];
for (const row of source) {
  const targetName = `${row.blind_id}.md`;
  const targetRel = `samples/${targetName}`;
  const srcContent = await fs.readFile(path.join(root, row.content_file), "utf8");
  const sample = [
    `blind_id: ${escMeta(row.blind_id)}`,
    `original_id: ${escMeta(row.original_id)}`,
    `title: ${escMeta(row.title)}`,
    `url: ${escMeta(row.url)}`,
    `domain: ${escMeta(row.domain)}`,
    `source_group: ${escMeta(row.source_group)}`,
    "",
    "# Content",
    "",
    srcContent,
  ].join("\n");
  await fs.writeFile(path.join(out, targetRel), sample, "utf8");
  clean.push({
    blind_id: row.blind_id ?? "", original_id: row.original_id ?? "", title: row.title ?? "",
    url: row.url ?? "", normalized_url: row.normalized_url ?? "", domain: row.domain ?? "",
    source_group: row.source_group ?? "", content_file: targetRel,
  });
}

const jsonlPath = path.join(out, "manifest", "blind_manifest_clean.jsonl");
await fs.writeFile(jsonlPath, clean.map(r => JSON.stringify(r)).join("\n") + "\n", "utf8");

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Blind Manifest");
sheet.showGridLines = false;
const matrix = [allowed, ...clean.map(r => allowed.map(k => r[k]))];
sheet.getRange(`A1:H${matrix.length}`).values = matrix;
sheet.getRange("A1:H1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" }, rowHeight: 24 };
sheet.getRange(`A2:H${matrix.length}`).format = { font: { color: "#1F2937" }, wrapText: false };
sheet.getRange(`A1:H${matrix.length}`).format.borders = { preset: "inside", style: "thin", color: "#D9E2F3" };
sheet.getRange("A:A").format.columnWidth = 16;
sheet.getRange("B:B").format.columnWidth = 18;
sheet.getRange("C:C").format.columnWidth = 48;
sheet.getRange("D:E").format.columnWidth = 42;
sheet.getRange("F:F").format.columnWidth = 24;
sheet.getRange("G:G").format.columnWidth = 14;
sheet.getRange("H:H").format.columnWidth = 28;
sheet.freezePanes.freezeRows(1);
sheet.tables.add(`A1:H${matrix.length}`, true, "BlindManifestClean");
const xlsxPath = path.join(out, "manifest", "blind_manifest_clean.xlsx");
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(xlsxPath);
const preview = await workbook.render({ sheetName: "Blind Manifest", range: "A1:H12", scale: 1, format: "png" });
await fs.writeFile(path.join(out, "verification", "manifest_preview.png"), new Uint8Array(await preview.arrayBuffer()));

const promptBytes = await fs.readFile(sourcePromptPath);
const promptPath = path.join(out, "prompt", "prompt_v3_2.md");
await fs.writeFile(promptPath, promptBytes);

const sampleHashes = {};
for (const r of clean) sampleHashes[r.blind_id] = sha(await fs.readFile(path.join(out, r.content_file)));
const shaManifest = {
  prompt_sha256: sha(await fs.readFile(promptPath)),
  clean_manifest_jsonl_sha256: sha(await fs.readFile(jsonlPath)),
  clean_manifest_xlsx_sha256: sha(await fs.readFile(xlsxPath)),
  sample_sha256: sampleHashes,
  total_sample_count: clean.length,
};
await fs.writeFile(path.join(out, "verification", "sha256_manifest.json"), JSON.stringify(shaManifest, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ out, allowed, promptSourceSha: sha(promptBytes), ...shaManifest }, null, 2));
