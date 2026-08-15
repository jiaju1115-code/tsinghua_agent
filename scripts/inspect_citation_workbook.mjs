import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = process.argv[2];
const targetRange = process.argv[3] || "A1:Z40";
const targetSheet = process.argv[4] || "Review Packet";
if (!inputPath) throw new Error("usage: node inspect_citation_workbook.mjs <xlsx>");
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheets = await workbook.inspect({ kind: "sheet", maxChars: 4000 });
console.log(sheets.ndjson);
const result = await workbook.inspect({
  kind: "region",
  sheetId: targetSheet,
  range: targetRange,
  maxChars: 16000,
  tableMaxRows: 30,
  tableMaxCols: 24,
  tableMaxCellChars: 200,
});
console.log(result.ndjson);
