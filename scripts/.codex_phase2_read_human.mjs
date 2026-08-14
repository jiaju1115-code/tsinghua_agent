import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/python_projects/tsinghua_ai/data_second/prompt_v3_2_blind_test_v1/human_label/blind_test_v1_human_label.xlsx";
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.getItem("人工标注");
const values = sheet.getRange("A3:Q53").values;
const headers = values[0];
const wanted = ["blind_id","original_id","title","url","domain","source_group","human_action","human_category","human_reject_type","human_topic_relevance","human_time_status","human_valid_until","human_note"];
const indexes = Object.fromEntries(wanted.map(k => [k, headers.indexOf(k)]));
const rows = values.slice(1).filter(r => r[indexes.blind_id]).map(r => Object.fromEntries(wanted.map(k => [k, r[indexes[k]]])));
process.stdout.write(JSON.stringify(rows));
