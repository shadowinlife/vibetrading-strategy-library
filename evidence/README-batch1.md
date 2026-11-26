# evidence/ — batch-1 验证证据（2026-11-26，harvest-validate-b1）

监督者批准的 batch1 候选 6 条（st-0003/st-0005/st-0006/st-0009/st-0010/st-0013）逐条真实验证证据。
判定汇总见各条目 frontmatter `status` 与正文"验证记录"；本目录存放可复核原始输出与脚本。
首轮（library-validate-001）证据见 [README.md](README.md)。

## 判定汇总

| 条目 | 判定 | 一句话 |
| --- | --- | --- |
| st-0003 | validated | 10 月 SMA GTAA 回撤控制显著（回撤 -12.4% vs 等权 -28.2%、2022 回避），绝对收益跑输如实记录 |
| st-0005 | research_only | 双动量轮动跑通但全面跑输 SPY B&H 与 60/40，回撤与 SPY 相同，"更高收益更低风险"未获支持 |
| st-0006 | research_only | RSI(2) 边际弱（303 笔 naive t=1.95/p=0.053）、成本脆弱（滑点翻倍收益减半）、跑输 B&H |
| st-0009 | research_only | 波动扩张降仓迁移仅 US 显著、HK 边际、crypto 主回撤未控（2022 零扩张 bar）；Wilder 敏感性 US 外显著 |
| st-0010 | research_only | 两融背离研究级模拟与 ETF 代理小幅跑赢+降回撤，但事件研究非重叠检验推翻 naive 显著、fwd20 方向翻转 |
| st-0013 | research_only | 月份效应默认看多月组合本窗口无正向边际（看多月均值反低于其他月、p=0.58），跑输 B&H |

## 目录

| 子目录 | 内容 |
| --- | --- |
| st-0003/ | GTAA 主规则 + 等权月度再平衡基准：signal_engine、config、metrics/equity/trades CSV、analysis.json（子周期/2022/各资产 B&H） |
| st-0005/ | GEM（AGG fallback）+ BIL fallback 变体 + 60/40 基准：同上 |
| st-0006/ | 主规则 + <5 阈值 + RSI>90 离场 + 无过滤 + 10bps 成本变体（5 套）：同上 + 交易级 t/成本扫描 |
| st-0009/ | 三市场 × SMA/Wilder（6 套）：同上 + 翻转日 mask 验证/数据一致性/扩张相位/2022 |
| st-0010/ | 东财两融快照（存档输入）+ sina 上证日线（存档输入）+ 510050 ETF 代理 VT 回测 + 研究级指数模拟脚本与结果 + 事件研究（非重叠/Newey-West）+ 取数脚本与探测结果 |
| st-0013/ | 默认月份组合 + Sell-in-May 变体：同上 + 月份效应统计 |
| batch1-scripts/ | 批次级脚本（as-executed 布局）：build_runs.py（建 run+算翻转 mask）、run_all.py（顺序回测）、analyze_runs.py（基准/子周期/敏感性/验证） |

## 执行环境与方法

- 回测：Vibe-Trading 官方日线引擎 `backtest.runner`（进程内 CLI，cwd=/opt/vibe-trading/agent，venv python）。信号收盘计算、**次日开盘成交**（引擎内置 1 bar 延迟，不手动 shift）。
- 月度策略（st-0003/0005/0013）与 RSI2（st-0006）用 `position_adjustment=hold`（目标仅在信号翻转时变化，月内/持仓内无交易）。
- **两态 1.0/0.5 策略（st-0009/st-0010）用 `position_adjustment=rebalance` + 显式 ISO 日期 `rebalance_mask`**=每个信号翻转的次一交易日（加首个评估日建仓）。原因：hold 模式会丢弃 1.0→0.5 的同向 resize（引擎语义），而 rebalance 无 mask 会逐日漂移再平衡（违背两态语义）；翻转日 mask 精确实现"仅在信号翻转次日开盘调仓、翻转间持有"。已验证六+一次运行成交日期全部落在 mask 内（除末日强制平仓），且用 run artifact 数据重算信号的翻转日与 mask 逐字一致。
- 基准：买入持有从各 run 自己的 ohlcv artifact 计算（同数据 basis，首评估 bar 开盘建仓、末日收盘、零成本）；等权月度再平衡与 60/40 用 VT rebalance_mask=MS 实跑。引擎自带 benchmark_return 为等权篮子口径，多资产条目另算单资产 B&H。
- 成本：US 5bps/边滑点零佣金；HK 印花税 0.1%/边+佣金 0.015%+滑点 0.1%+征费/结算费、100 股/手假设；crypto taker/maker 0.1%+引擎默认滑点 0.05%（同 st-0001）；A 股 ETF 佣金 0.025%（最低 5 元）+过户费 0.001%+滑点 0.1%、ETF 免印花税；st-0010 研究级指数 0.05%/边（条目操作化默认）。
- 数据源可用性见 [data-source-probes.md](data-source-probes.md)。本批新增：sina `fund_etf_hist_sina`（510050 全历史 5289 行可得）；东财 `fund_etf_hist_em`（510050 全窗口、510300 限流）；腾讯 kline（510300 仅 2024-04 起 640 行）。取数失败如实记录，未编造数字。
- 复现：batch1-scripts/ 与 st-0010/research_sim_event_study.py 按原执行布局归档（引用 /root/projects/harvest-validate-b1/work 与 ~/.vibe-trading/runs/harvest-validate-b1）；跨目录重跑需先按脚本内引用摆放输入文件。st-0010 的两融快照与上证日线为存档输入（东财 2000 行上限起点漂移，不可重新取回同一窗口），已随仓。

## 诚实性声明

- 所有数字来自真实工具输出（VT 回测引擎/公开 API/免费行情源），原始 CSV 随本目录入库。
- 统计检验：st-0006 交易级 t 为 naive（跨 sleeve 日历重叠）；st-0010 事件研究同时给 naive（重叠夸大）、非重叠（≥60 交易日间隔）与 Newey-West（Bartlett HAC，lag=horizon）三种，naive 强显著被非重叠检验推翻如实记录；st-0013 月份效应 naive t 低功效（147 月）如实声明。
- 跑输买入持有一律如实写（st-0003/0005/0006/0009/0013 绝对收益均跑输）；research_only 未转正，引用必须标注"未验证，仅供参考"。
- 定性操作化条目（st-0009/st-0010）判定只针对有界版本，limitations 保留"结论不外推到原始定性主张/镜像原口径"。
- 未验证部分（holdout/shadow/live、其他参数窗口、个股、做空腿、深市/两市口径、510300 对照等）在各条目 limitations 逐条写明。
