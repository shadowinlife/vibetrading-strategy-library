# evidence/ — holdout 深化证据（2026-11-27，harvest-holdout-001）

监督者决策 H7：对 3 条 validated 策略（st-0001 / st-0003 / st-0014）执行保留样本外 holdout 验证。
规则与参数完全冻结（逐字复用首轮 signal_engine 与成本配置），仅改评估窗口；暖机自 2022-01，评估严格 2024-01-01→2026-11-25（从未参与规则设计的干净保留样本）。
判定汇总见各条目 frontmatter `status`/`evidence` 与正文「holdout 验证记录」；本目录存放可复核原始输出。
首轮证据见 [README.md](README.md)，batch-1 见 [README-batch1.md](README-batch1.md)，batch-2 见 [README-batch2.md](README-batch2.md)。

## 判定汇总（证据阶梯 backtest → holdout）

| 条目 | 机制主张 | holdout 判定 | 一句话 |
| --- | --- | --- | --- |
| st-0001 | 回避主跌段（策略回撤 << 标的回撤） | 成立 → holdout | 三市场策略回撤 -1.43%/-3.57%/-6.95% 远小于标的 -18.76%/-49.62%/-53.33%；绝对收益仍大幅跑输 B&H；加密盈利因子 3.61→1.64、Sharpe 0.81→0.39 衰减如实记录 |
| st-0003 | 回撤控制（GTAA < 等权月度再平衡） | 成立 → holdout | GTAA -8.16% < 等权 -10.58%（比值 0.77 vs 全窗口 0.44，边际收窄）；Sharpe 1.00 < 等权 1.28（全窗口优势反转消失）；绝对收益跑输 |
| st-0014 | 回撤控制（ERC < 60/40 < SPY）+ ERC 收敛 | 成立 → holdout | ERC -5.14% < 60/40 -10.39% < SPY -18.76%；Sharpe 1.57 > 1.10；13 季度全收敛（≤15 迭代）、60% 上限 4 季度触发、阈值零触发（最大漂移 2.93pp） |

三条均升级 holdout，status 保持 validated，未降级；未做 shadow/live。

## 目录

| 子目录 | 内容 |
| --- | --- |
| st-0001/holdout/ | 三市场（SPY.US / 0700.HK / BTC-USDT）holdout：config-{us,hk,crypto}.json、metrics/equity/trades/positions/target_positions CSV、analysis.json（策略 vs 标的 B&H、机制判定） |
| st-0003/holdout/ | GTAA + 等权月度再平衡基准：config-gtaa/bench-ew.json、metrics/equity/trades/positions CSV、analysis.json（GTAA vs 等权 vs SPY B&H、回撤比值、Sharpe 反转） |
| st-0014/holdout/ | ERC + 60/40 季度再平衡基准：config-erc/bench-6040.json、metrics/equity/trades/positions CSV、rebalance_notes.json、analysis.json（回撤次序、求解器收敛/上限触发/RC 偏离、阈值不动点零触发） |

## 执行环境与方法

- 回测：VT 官方日线引擎 `backtest.runner`（venv python，cwd=/opt/vibe-trading/agent），信号收盘计算、次日开盘成交（内置 1 bar 延迟）。run 根 `~/.vibe-trading/runs/harvest-holdout-001`。
- 暖机与评估分离：取数自 2022-01-01，`evaluation_start_date=2024-01-01`、`end_date=2026-11-25`（`warmup_bars` 与 `evaluation_start_date` 互斥）。
- st-0001 `hold` 状态机；st-0003 GTAA `hold`、等权基准 `rebalance`+`MS`；st-0014 `rebalance`+显式季度 ISO mask（含首评估日建仓）+阈值两遍不动点。
- 成本沿用各条目首轮配置（US 5bps/边零佣金；HK 印花税 0.1%/边+佣金+滑点+征费/结算、100 股/手；crypto taker 0.1%/边）。
- 买入持有对照：首评估 bar 开盘建仓、零成本，从 run 自身 ohlcv artifact 计算（同区间同口径）。
- 成交完整性：rebalance 运行全部成交日 ⊆ mask ∪ {末日强平}（已校验通过）。
- 复现脚本：任务目录 `/root/projects/harvest-holdout-001/`（build_runs.py / analyze.py / update_ledger.py）。

## 诚实性声明

- 所有数字来自 VT 回测引擎真实输出与 run 自身 ohlcv artifact，原始 CSV/JSON 随本目录入库；未编造数字。
- 样本约 2.9 年功效有限，holdout 含 2024-2025 市场结构；机制主张「持续成立」为方向性判断，不外推到更长样本。
- st-0003 Sharpe 优势本窗口消失、st-0001 加密盈利因子衰减、三条绝对收益跑输 B&H、st-0014 阈值机制未激活——均如实记录，未粉饰。
