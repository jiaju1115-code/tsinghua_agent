# API Provider / 模型路由 / 分组隔离诊断

## A. 新Key认证

- KEY_GROUP=`new_group`
- API Base：`https://momoapi.cc/v1`
- Auth：PASS；HTTP=200；latency=1.446s
- `/models`：PASS，但 `data=[]`（已二次确认响应结构正确）
- `gpt-5.4-mini available`：False
- 分组诊断码：`NEW_GROUP_MODEL_NOT_AVAILABLE`

## B. 新分组 + gpt-5.4-mini

- NOT_RUN

## C. 其他模型诊断

- DIAGNOSTIC_ONLY：True
- model：None
- NOT_RUN

## D. 新旧分组比较

| 测试 | old_group | new_group |
|---|---|---|
| Auth | PASS | PASS |
| Models | PASS | PASS |
| gpt-5.4-mini minimal generation | FAIL HTTP 504 | NOT_RUN |

## E. 故障定位

- 最终诊断：`INCONCLUSIVE`（新分组没有任何可访问模型，无法执行路由生成对照）
- 真实 BLINDV1-001：`NOT_RUN`
- READY_TO_RESUME_BLIND_TEST：`False`
- Backend identity：`BACKEND_IDENTITY_NOT_VERIFIABLE`
- 未运行50条正式盲测；其他模型仅用于故障隔离。
