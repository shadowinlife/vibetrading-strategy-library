# evidence/ — batch-2 验证证据（2026-11-26，harvest-validate-b2）

监督者批准的 batch2 候选 6 条（st-0004/st-0007/st-0008/st-0011/st-0012/st-0014）逐条真实验证证据。
判定汇总见各条目 frontmatter `status` 与正文"验证记录"；本目录存放可复核原始输出与脚本。
首轮（library-validate-001）证据见 [README.md](README.md)，batch-1 见 [README-batch1.md](README-batch1.md)。

## 判定汇总

| 条目 | 判定 | 一句话 |
| --- | --- | --- |
| st-0004 | research_only | TSMOM 仅多头跑通但相对八资产等权无统计分离（月度差 NW t=-0.29），绝对收益跑输；多空研究级敏感性本窗口 -5.51%（借券成本未建模） |
| st-0014 | validated | ERC 回撤控制主张获支持（回撤 -14.74% < 60/40 -21.47% < SPY -33.72%，2022 压力段 -6.22% vs -16.90%/-18.65%，Sharpe 0.846≥0.825）；绝对收益跑输如实记录；阈值 12 年零触发 |
| st-0011 | rejected | 双语义×双对均无正向边际；KO/PEP 与 BTC/ETH 均不协整（EG ADF t=+0.26/+0.32 与 -1.42/-2.46）；crypto 无状态版单笔均值显著为负（t=-2.35） |
| st-0007 | research_only | 大盘池反转溢价消失（L−W 价差 -0.18%/月，NW t=-0.41，非重叠 147 月）；仅多头跑输等权池、回撤 -50.16%；January +2.58%（n=12）低功效 |
| st-0008 | rejected | 有界总波动率代理版本被显著反向证据反驳（低−高价差 -0.98%/月，NW t=-2.14/-2.28）；交易版跑输等权池；防御性/2022 子主张获支持；不外推到原文 FF3 特质波动率 |
| st-0012 | research_only | 方向性主张未获支持：SPY 低/高波态前向分离非重叠后消失（p=0.78），BTC 显著反向（p=0.037）；SPY 回撤减半为机械副产品、跑输 B&H，BTC -79.63% 灾难性跑输 |

## 目录

| 子目录 | 内容 |
| --- | --- |
| st-0004/ | TSMOM 仅多头主规则 + 多空研究级敏感性 + 八资产等权月度再平衡基准：signal_engine、config、metrics/equity/trades CSV、analysis.json（子周期/2022/月度差 NW 检验/上限触发月份） |
| st-0014/ | ERC 主规则 + 60/40 季度再平衡基准：同上 + solver-diagnostics.json（54 季度收敛/上限触发/RC 偏离）+ threshold-iterations.json（阈值不动点过程） |
| st-0011/ | KO/PEP 与 BTC/ETH × 状态机/无状态（4 套）：同上 + analysis.json（配对往返 t/EG 协整/状态占用/强制平仓/语义差异/mask 校验） |
| st-0007/ | 仅多头 losers 十分位 + 503 等权池基准：同上 + decile-monthly-spread.csv（研究级无成本月价差序列）+ pools.json（成分快照） |
| st-0008/ | 仅多头低波五分位：同上 + quintile-monthly-spread.csv + pools.json + sp500-constituents-gics.csv（GICS 行业集中度输入）；等权池基准复用 st-0007（同池/窗口/成本/数据基，声明） |
| st-0012/ | SPY/BTC × 有成本/零成本（4 套）：同上 + analysis.json（前向 20 日分离 naive/NW/非重叠步长/抖动成本/2022） |
| batch2-scripts/ | 批次级脚本（as-executed 布局）：fetch_data.py（VT loader 取数+ETH 深度探测）、build_runs.py（建 run+翻转/季度/阈值 mask）、run_all.py（顺序回测）、analyze_runs.py（基准/子周期/价差/协整/分离检验）、ledger_sync.py（SdmRegisterTool 台账）、fetch_results.json（取数探测结果） |

## 执行环境与方法

- 回测：Vibe-Trading 官方日线引擎 `backtest.runner`（进程内 CLI，cwd=/opt/vibe-trading/agent，venv python）。信号收盘计算、**次日开盘成交**（引擎内置 1 bar 延迟，不手动 shift）。
- 月度策略（st-0004/0007/0008）用 `position_adjustment=rebalance` + `rebalance_mask=MS`（权重每月 resize，hold 会丢弃同向 resize——batch1 教训）。
- 锁存/两态策略（st-0011/0012）用 `rebalance` + 显式 ISO 翻转日 mask（翻转次一交易日+首评估日），翻转间持有、无漂移再平衡；四+四套运行 mask 与 artifact 数据重算信号逐字一致、成交全落在 mask 内（除末日强制平仓）。
- st-0014 阈值再平衡：引擎自身 positions.csv 实际权重两遍不动点迭代（季度-only mask → 读 |实际−目标|≥10pp 触发日 → 加执行日重跑至稳定；排除末日强制平仓与季度信号日目标切换）。结果：季度间最大漂移 4.82pp，12 年零阈值触发，49 个季度执行日。ERC 求解 Spinu CCD 容差 1e-8，54 季度全收敛（≤16 迭代），60% 上限 8 季度触发（RC 份额偏离最大 19.7pp，操作化补丁声明）。
- 基准：买入持有从各 run 自己的 ohlcv artifact 计算（同数据 basis，首评估 bar 开盘建仓、末日收盘、零成本）；等权/60-40 用 VT rebalance 实跑。st-0007/st-0008 策略 run 含 SPY.US 零权重载体以同 run 计算 SPY B&H；st-0008 等权池基准复用 st0007-bench-ew（声明）。
- 成本：US 5bps/边滑点零佣金；crypto taker/maker 0.1%+引擎默认滑点 0.05%（batch1 惯例）；零成本变体（st-0012）量化抖动成本。借券成本（st-0004 ls/st-0011 US）与永续资金费率（st-0011 crypto）未建模，研究级口径声明。
- 数据：yfinance（US ETF 11 只 + S&P500 503 快照+SPY 载体，504/504 成功）、OKX history-candles（BTC/ETH 自 2017-12-01，ETH 深度探测至 2017-10-10 可得）。**任务内 loader 缓存**（VIBE_TRADING_DATA_CACHE=true + CACHE_ROOT 指向任务 work/data-cache，进程级 env，不改全局配置）：三次 503 池运行共享一次网络取数；end_date=2026-11-25（最后已结算 bar）。prep 存档与 run artifact 数据一致性校验（rtol 1e-5）全部通过。GICS 行业：GitHub datasets s-and-p-500-companies **data/constituents.csv**（main 分支根路径 404，data/ 路径成功）。
- 统计：月度形成+1 月持有的前向价差天然非重叠（st-0007/0008），另给 Newey-West（Bartlett HAC）lag1/lag3 稳健性；st-0012 前向 20 日分离给 naive（重叠夸大）+NW lag20+非重叠 20-bar 步长三口径；st-0011 配对往返序贯非重叠（同一时间仅一对仓位）；协整为手工 Engle-Granger（log 价格 OLS 残差 ADF，AIC 选 lag，EG 渐近临界值；venv 无 statsmodels）。
- 复现：batch2-scripts/ 按原执行布局归档（引用 /root/projects/harvest-validate-b2/work 与 ~/.vibe-trading/runs/harvest-validate-b2）；跨目录重跑需先按脚本内引用摆放输入文件。输入行情未入库（体积原因），按 config 的 source/codes/dates 可重新取数；pools.json 成分快照随 st-0007/st-0008 入库。

## 诚实性声明

- 所有数字来自真实工具输出（VT 回测引擎/公开 API/免费行情源），原始 CSV 随本目录入库。
- 跑输买入持有一律如实写（st-0004/0007/0008/0012 绝对收益均跑输对应基准；st-0014 跑输 60/40 与 SPY）；research_only 未转正、rejected 被拒，引用必须标注对应状态。
- 判定边界：st-0008 被拒仅限有界总波动率代理版本（不外推到原文 FF3 特质波动率）；st-0011 被拒仅限两对×双语义有界版本（不外推到任意高相关对）；st-0012 crypto 腿反向证据如实记录、整体 research_only（US 非重叠未显著反向）。
- 定性操作化条目判定只针对有界版本，limitations 保留"结论不外推到原始定性主张/镜像原口径"。
- 未验证部分（holdout/shadow/live、成本敏感性、其他参数窗口、FF3 升级、精确对冲比率、组合用法等）在各条目 limitations 逐条写明。
