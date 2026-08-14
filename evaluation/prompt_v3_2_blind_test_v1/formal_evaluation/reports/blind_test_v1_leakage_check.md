# Prompt V3.2 Blind Test V1 泄漏检查

## 结论

`PASS — 0 SAMPLE LEAKAGE`

## 检查结果

- 冻结样本：50 条。
- 与历史 30 条调参集按 ID 交叉：0 条。
- 按原始 URL 交叉：0 条。
- 按 normalized URL 交叉：0 条。
- 样本内 URL 重复：0 条。
- 样本内 normalized URL 重复：0 条。
- 冻结人工文件 action 完整度：50/50。
- 人工文件 SHA-256：`EC1E846091532205A04480320A4A4572D99526F58FE8A9037390BED4BC502CA6`。
- Prompt V3.2 SHA-256：`B94623C520FC46D83A49A4D043AD182646E7A881E7E1751E3E98E98724D771CD`。
- Prompt 中出现本批样本 ID：0 条。
- 独立模型输入仅含 blind_id、original_id、title、url、source_domain、content_file、content_sha256；不含人工标签、人工备注或任何历史 AI 判断。
- 模型输入清单 SHA-256：`91B1ED54A0F65693648BF8B97F214C0060C4940960FD28D6C40ECBD288CDD0C9`。

## 阶段锁定

泄漏检查在 API 调用前完成。后续模型运行仅读取独立输入清单和正文文件；冻结人工标签只会在 AI 原始结果全部保存后用于合并评估。
