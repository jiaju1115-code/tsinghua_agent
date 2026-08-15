import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const input='D:\\python_projects\\tsinghua_ai\\experiments\\generation_citation_eval_v0\\results\\independent_review_packet_adjudicated.xlsx';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(input));
const overview=await wb.inspect({kind:'sheet,table',maxChars:5000,tableMaxRows:6,tableMaxCols:30,tableMaxCellChars:200});
const sheet=wb.worksheets.getItemAt(0);const used=sheet.getUsedRange();const values=used.values;
await fs.writeFile('inputs/adjudication_raw_rows.json',JSON.stringify({sheet:sheet.name,address:used.address,values},null,2),'utf8');
console.log(overview.ndjson);console.log(JSON.stringify({sheet:sheet.name,address:used.address,rows:values.length,cols:values[0]?.length,headers:values[0]},null,2));
