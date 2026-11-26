# evidence/ — 首轮验证证据（2026-11-26）

验证流水线恢复后的首轮 9 条种子条目验证证据。任务：library-validate-001。
判定汇总见各条目 frontmatter 的 `status` 与 `evidence`；本目录存放可复核的原始输出与脚本。

> batch-1（harvest-validate-b1，2026-11-26）6 条候选验证证据见 [README-batch1.md](README-batch1.md)（st-0003/0005/0006/0009/0010/0013）。
> batch-2（harvest-validate-b2，2026-11-26）6 条候选验证证据见 [README-batch2.md](README-batch2.md)（st-0004/0007/0008/0011/0012/0014）。

## 目录

| 子目录 | 条目 | 内容 |
| --- | --- | --- |
| st-0001/ | 双均线 20/60 | 三市场（SPY.US / 0700.HK / BTC-USDT）VT 日线回测：signal_engine.py、config、metrics/equity/trades CSV、子周期分析 |
| st-0002/ | 截面动量 12-1 | 美股 S&P500（503 只）/港股恒指（85 只）VT 回测 + 十分位 winners/losers 前向价差检验（h1/h6） |
| in-0001/ | 行业估值分位 | 银行业完整样本：整体法 PE_TTM/PB/股息率 + cninfo 官方静态 PE 交叉核对 + 月度历史分位 |
| in-0002/ | 总市值/GDP | 世界银行同口径 2024 年三市场比率 + 实时市值交叉核对 |
| in-0003/ | 成交集中度/两融背离 | 全 A 单日成交集中度（sina 5577 只）+ 沪市两融背离序列（2018-08→2026-11）+ 两市两融快照 |
| in-0004/ | 港美股活跃度集中度 | S&P500/恒指股票池成交集中度日度序列（2013→2026）+ 当前市值集中度 |
| kn-0001/ | 拥挤与顶部 | 两融背离子信号事件研究（前向 20/60 日收益对照） |
| kn-0002/ | 巴菲特指标 | 美国 1975-2024 市值/GDP 序列 vs 前向 10 年收益（总收益/价格双口径） |
| kn-0003/ | 估值分位均值回归 | Shiller CAPE 10 年滚动分位 vs 前向 5/10 年实际总收益 |

## 执行环境与方法

- 回测：Vibe-Trading 官方日线引擎（`backtest.runner`），信号收盘计算、**次日开盘成交**（引擎内置 1 bar 延迟，与条目"次日开盘"规则逐字一致）；st-0001 用 `position_adjustment=hold`，st-0002 用 `rebalance` + `rebalance_mask=MS` 月度执行。
- 成本：美股 5bps/边滑点、零佣金；港股印花税 0.1%/边 + 佣金 0.015% + 滑点 0.1% + 征费/结算费；加密 taker 0.1%/边。港股手数未配置真实每手股数，按 100 股假设（st-0002-hk 存在手数 rounding 现金拖累，已在结果中体现）。
- 数据源与可用性见 [data-source-probes.md](data-source-probes.md)。取数失败与窗口限制一律如实记录，未编造数字。
- 复现：各子目录 compute.py / signal_engine.py + config 可在装好依赖的 VT venv 内重跑；输入行情未全部入库（体积原因），按 config 的 source/codes/dates 可重新取数。st-0002 股票池快照见 st-0002/pools.json（当前成分股，存在幸存者偏差，已在条目 limitations 声明）。
- 分析/计算脚本中的工作目录已参数化：`VALIDATE_EVIDENCE_DIR`（取数与输出目录，需保持任务工作区的文件布局）、`VALIDATE_RUNS_DIR`（VT 回测 run 根目录，默认 `~/.vibe-trading/runs/library-validate-001`）。脚本按原执行布局归档，跨目录重跑需先按脚本内引用摆放输入文件。

## 诚实性声明

- 所有数字来自真实工具输出（VT 回测引擎 / 公开 API / 免费行情源），原始 CSV 随本目录入库。
- 统计检验的 t 值多为 naive（重叠窗口会夸大显著性），各 JSON 内已注明；未把弱显著结果包装成强结论。
- 未验证的部分（可选止损、做空腿、10 年日度分位窗口、全市场历史成交截面等）在各条目 limitations 中逐条写明。