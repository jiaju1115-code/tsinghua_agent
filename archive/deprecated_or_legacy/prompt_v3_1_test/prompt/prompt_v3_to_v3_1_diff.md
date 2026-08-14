# Prompt V3 → V3.1 定向修订说明

## 修改范围

本轮不是重写审核体系，只定向修改三个已由 30 条固定样本暴露的问题：事件判断顺序、`historical_but_valuable` 边界、`active_time_bound` 动作。

## 规则变化

### 1. 事件时效判断前置

V3 先判断知识价值、再判断时效，容易把内容丰富的已结束课堂、讲座和活动报道判为长期知识。V3.1 要求对课堂、讲座、展览、比赛、活动、培训、会议和论坛单场报告等页面，先识别页面核心主题和事件状态，再判断正文是否包含知识。

若页面核心是已经结束的一次性事件，统一：

```text
action = reject
reject_type = expired_event
time_status = expired
```

正文中附带的演讲观点、嘉宾经历、研究方法、数据库介绍或活动总结不能推翻该结论。

### 2. 收紧 historical_but_valuable

V3 对“历史但有价值”的解释偏宽。V3.1 只允许在过去事件明确形成当前仍存在的实体、制度、服务、平台、资源或设施时使用该标签，例如仍在使用的上线系统、持续提供的已订购数据库、仍有效的制度、仍存在的机构和设施。

已结束的讲座、课堂、培训、会议、展览、比赛、活动、活动回顾、单场报告和经验分享不得使用 `historical_but_valuable`。

### 3. active_time_bound 统一 review

删除 V3 中“信息价值特别明确、当前有效时可 approve”的例外。V3.1 规定：只要页面核心价值依赖当前有效且未来有明确截止日期的时间窗口，统一：

```text
action = review
time_status = active_time_bound
```

这适用于数据库试用、临时开放、报名预约、暑期安排、临时交通和阶段性资源开放。

### 4. 增加长期资源保护表述

为防止时效规则过度收紧，明确图书借还、信息系统开发、长期数据库、图书馆与网络服务、机构、科研资源、设施、制度和服务说明，在无明确截止时间且当前持续存在时仍原则上 approve。

## 保持不变

- “清华校园知识库”而非仅办事指南的总体目标；
- Quality Gate 与 Prompt 的职责边界；
- 主体归属与 `out_of_scope` 规则；
- category 枚举和 content_type 枚举；
- JSON 输出结构和字段校验；
- candidate_user_question、positive_evidence、negative_evidence 等输出要求；
- reject 主要收敛为 `out_of_scope` 与 `expired_event`，`other` 仅作极少数兼容用途；
- 模型、temperature、并发、输入样本、正文内容和 API 参数。
