# E2E12 failure cases

评估口径为本地 Qwen Provisional Proxy，不代表人工验收。12题中，1题为正确拒答且无失败；其余11题存在主失败层级。

## Router — 0 cases

12/12 路由正确；False Academic 0，Missed Academic 0。

## Search — 0 cases

所有11道应联网题均取得 Search 候选。

## Extract — 0 cases

11道发生 Extract 的题均至少提取到一个长度达到门槛的正文。

## Evidence — 1 case

- C01「清华图书馆今天几点关门？」：正确进入 Campus，Search/Extract 成功，但最终证据不足以确认当天闭馆时间。系统正确拒答；主失败为 E（Evidence），不是 Router Failure。

## Generation — 10 cases

- Academic：A17、A15、A08、A24、A26、A02。检索链路与 evidence sufficiency 均通过，但本地 proxy 的 correctness 均为 1/2；A08、A26还缺少引用。
- Campus：C03。检索到校医院页面，但答案未给出具体联系方式，correctness 1/2。
- General：G01、G02。G01把不相关内容组织成“量子计算新闻”；G02未给出市场规模，均为 correctness 1/2。
- Hard Negative：N04。检索成功但未回答人口最多的国家，correctness 1/2。

上述均为 G（Generation）主失败，不由 Router 导致；建议下一阶段专项修复生成的任务完成度和证据相关性约束，本实验不执行修复。

## Citation — 0 primary cases

无题以 Citation 作为首要失败；但总体 Citation Presence 仅58.33%，是明确的次级问题。存在引用时，ID 映射有效率与本地 proxy 支持率均为100%。

## Infrastructure — 0 cases

无凭证、网络、依赖或 API 阻断。首个宿主命令在120秒时限结束后续跑；已完成的4题未重复请求，其逐题证据保留在 run log，trace 中对应记录标注为 reconstructed。
