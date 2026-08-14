import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_blind_test_v1/blind_bundle_v1/manifest/blind_manifest_clean.xlsx";
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const overview = await workbook.inspect({
  kind: "sheet,table",
  maxChars: 30000,
  tableMaxRows: 60,
  tableMaxCols: 30,
  tableMaxCellChars: 500,
});
process.stdout.write(overview.ndjson);
