# Campus MD-to-SFT Factory V1

安全优先的 campus Markdown 候选数据工厂。API key 只从 `MOMO_API_KEY` 读取；没有配置时输出 `MOMO_API_KEY_NOT_CONFIGURED` 并停止 API 调用。默认只允许 public、canonical、eligible source。

入口：

```powershell
python experiments/campus_md_to_sft_factory_v1/src/run_pilot.py
python experiments/campus_md_to_sft_factory_v1/src/run_full_batch.py
```

本轮只生成候选池，不创建 train/validation/test split，也不修改 production KB、retriever 或 answer runtime。
