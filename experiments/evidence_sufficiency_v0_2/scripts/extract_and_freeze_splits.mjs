import fs from "node:fs/promises";
import path from "node:path";
import crypto from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const repo = "D:/python_projects/tsinghua_ai";
const root = `${repo}/experiments/evidence_sufficiency_v0_2`;
const adjudicated = `${repo}/experiments/evidence_benchmark_expansion_v0_2/adjudication/new_real_adjudication_packet_adjudicated.xlsx`;
const syntheticPath = `${repo}/experiments/evidence_benchmark_expansion_v0_2/synthetic/synthetic_stress_set_v0_2.json`;
for (const d of ["development","evaluation","audit","scripts"]) await fs.mkdir(`${root}/${d}`, {recursive:true});

const blob = await FileBlob.load(adjudicated);
const wb = await SpreadsheetFile.importXlsx(blob);
const summary = await wb.inspect({kind:"workbook,sheet,table",maxChars:5000,tableMaxRows:3,tableMaxCols:18,tableMaxCellChars:100});
await fs.writeFile(`${root}/audit/adjudicated_workbook_inspect.ndjson`, summary.ndjson, "utf8");
const ws = wb.worksheets.getItem("Adjudication Packet");
const values = ws.getUsedRange().values;
const headers = values[0].map(String);
const real = values.slice(1).filter(r=>r[0]).map(row=>Object.fromEntries(headers.map((h,i)=>[h,row[i]??""])));
for (const r of real) {
  for (const k of ["frozen_evidence","evidence_ids","evidence_source_titles","required_answer_points"]) {
    if (typeof r[k] === "string" && /^[\[{]/.test(r[k].trim())) { try { r[k]=JSON.parse(r[k]); } catch {} }
  }
  r.label=String(r.adjudicated_evidence_gate||"").trim();
  r.selection_hash=crypto.createHash("sha256").update(`${r.sample_id}||${r.query}||evidence_sufficiency_v0_2_real`).digest("hex");
}
if (real.length!==32 || real.some(r=>!r.label)) throw new Error(`Expected 32 adjudicated rows; found ${real.length}, missing labels=${real.filter(r=>!r.label).length}`);
const byLabel=Map.groupBy(real, r=>r.label);
const target={EVIDENCE_SUFFICIENT:6,EVIDENCE_PARTIAL:2,EVIDENCE_INSUFFICIENT:0,EVIDENCE_UNKNOWN:0};
const realHold=[];
for (const [label,rows] of byLabel) realHold.push(...rows.toSorted((a,b)=>a.selection_hash.localeCompare(b.selection_hash)).slice(0,target[label]??0));
const realHoldIds=new Set(realHold.map(r=>r.sample_id));
const realDev=real.filter(r=>!realHoldIds.has(r.sample_id));

const synthetic=JSON.parse(await fs.readFile(syntheticPath,"utf8"));
for (const r of synthetic) r.selection_hash=crypto.createHash("sha256").update(`${r.sample_id}||${r.construction_type}||evidence_sufficiency_v0_2_synthetic`).digest("hex");
const synthBy=Map.groupBy(synthetic,r=>r.construction_type);
const synthHold=[];
for (const [kind,rows] of synthBy) {
  const n=kind==="SUFFICIENT_CONTROL"?8:3;
  synthHold.push(...rows.toSorted((a,b)=>a.selection_hash.localeCompare(b.selection_hash)).slice(0,n));
}
// Fill deterministically to exactly 24 while preserving all six construction types.
const synthHoldIds=new Set(synthHold.map(r=>r.sample_id));
const remaining=synthetic.filter(r=>!synthHoldIds.has(r.sample_id)).toSorted((a,b)=>a.selection_hash.localeCompare(b.selection_hash));
for (const r of remaining.slice(0,24-synthHold.length)) { synthHold.push(r); synthHoldIds.add(r.sample_id); }
const synthDev=synthetic.filter(r=>!synthHoldIds.has(r.sample_id));

const stable=x=>JSON.stringify(x,null,2);
const shaFile=async p=>crypto.createHash("sha256").update(await fs.readFile(p)).digest("hex");
await fs.writeFile(`${root}/evaluation/real_internal_holdout.json`,stable(realHold),"utf8");
await fs.writeFile(`${root}/development/real_development_set.json`,stable(realDev),"utf8");
await fs.writeFile(`${root}/evaluation/synthetic_stress_holdout.json`,stable(synthHold),"utf8");
await fs.writeFile(`${root}/development/synthetic_development_set.json`,stable(synthDev),"utf8");
const realFreeze={source:adjudicated,source_sha256:await shaFile(adjudicated),selection_method:"Stratified label hash SHA256(sample_id || query || evidence_sufficiency_v0_2_real)",holdout_sample_ids:realHold.map(r=>r.sample_id).sort(),holdout_distribution:Object.fromEntries([...Map.groupBy(realHold,r=>r.label)].map(([k,v])=>[k,v.length])),development_distribution:Object.fromEntries([...Map.groupBy(realDev,r=>r.label)].map(([k,v])=>[k,v.length])),canonical_sha256:await shaFile(`${root}/evaluation/real_internal_holdout.json`)};
const synFreeze={source:syntheticPath,source_sha256:await shaFile(syntheticPath),selection_method:"Stratified construction hash SHA256(sample_id || construction_type || evidence_sufficiency_v0_2_synthetic)",holdout_sample_ids:synthHold.map(r=>r.sample_id).sort(),holdout_distribution:Object.fromEntries([...Map.groupBy(synthHold,r=>r.construction_type)].map(([k,v])=>[k,v.length])),development_distribution:Object.fromEntries([...Map.groupBy(synthDev,r=>r.construction_type)].map(([k,v])=>[k,v.length])),canonical_sha256:await shaFile(`${root}/evaluation/synthetic_stress_holdout.json`)};
await fs.writeFile(`${root}/audit/real_holdout_freeze.json`,stable(realFreeze),"utf8");
await fs.writeFile(`${root}/audit/synthetic_holdout_freeze.json`,stable(synFreeze),"utf8");
process.stdout.write(JSON.stringify({real:{development:realDev.length,holdout:realHold.length,distribution:realFreeze.holdout_distribution,sha256:realFreeze.canonical_sha256},synthetic:{development:synthDev.length,holdout:synthHold.length,distribution:synFreeze.holdout_distribution,sha256:synFreeze.canonical_sha256}}));
