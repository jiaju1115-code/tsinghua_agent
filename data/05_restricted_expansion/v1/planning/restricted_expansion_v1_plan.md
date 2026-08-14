# Restricted / Authenticated Expansion V1 Plan

- Public staging approve：234
- 旧 login_required seeds：23
- 推荐认证后抓取：12
- 条件抓取：1
- 认证原则：仅复用现有合法 session；若失效，状态为 `NEED_MANUAL_LOGIN`。
- 安全原则：private/sensitive gate 在 Quality Gate 之前；仅 safe_general_content 继续。
- 抓取范围：P0/P1 优先，单系统约 50 个 detail 上限，list page 仅一层定向 follow。
- 数据状态：仅 restricted candidate，不进入 production。
