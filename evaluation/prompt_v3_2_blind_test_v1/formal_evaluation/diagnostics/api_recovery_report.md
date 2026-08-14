# API Recovery Report

## API是否恢复

`API_STILL_BLOCKED`

- API Base：`https://momoapi.cc/v1`
- API_KEY_SOURCE：`temporary_runtime`
- TCP 443：PASS
- HTTP：PASS；status=404；latency=1.343s
- Auth：PASS
- gpt-5.4-mini available：True

## 三次最小生成探针

- Probe 1: FAIL；latency=61.426s；HTTP=504；error=HTTP_504_GATEWAY_TIMEOUT

## 真实样本探针

- 状态：NOT_RUN
- blind_id：
- latency：s
- error：

## 是否进入正式50条执行

`False`

## ReadTimeout

- timeout_count：0
- 本诊断不记录 API Key、Authorization Header 或盲测正文。
