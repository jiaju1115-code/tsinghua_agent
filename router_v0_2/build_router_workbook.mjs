import {createRequire} from 'module';
const require=createRequire(import.meta.url); const {Workbook}=require('artifact-tool');
import fs from 'fs';
const root=process.cwd(); const wb=new Workbook();
for (const [name,file] of [['Development24','development_24_results.jsonl'],['FrozenFull30','frozen_full30_results.jsonl'],['Blind42','blind_42_results.jsonl']]) {
 const rows=fs.readFileSync(`${root}/results/${file}`,'utf8').trim().split(/\n/).map(JSON.parse);
 const sh=wb.worksheets.add(name); const headers=['evaluation_id','set','group','subject','query','expected_mode','mode','correct','router_reason'];
 sh.getRangeByIndexes(0,0,1,headers.length).values=[headers];
 sh.getRangeByIndexes(1,0,rows.length,headers.length).values=rows.map(r=>headers.map(h=>r[h]??''));
 sh.getRangeByIndexes(0,0,1,headers.length).format.font={bold:true}; sh.freezePanes.freezeRows(1); sh.getUsedRange().format.autofitColumns();
}
await wb.xlsx.write(`${root}/evaluation/router_v0_2_evaluation.xlsx`);
