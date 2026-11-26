---
id: st-0005
type: strategy
title: Antonacci 双动量 GEM（美股/非美股/债券，文献操作化）
status: research_only
vt_artifact_id: art_8b068c163977
markets: [us]
asset_classes: [equity, bond]
horizon: 月度（12 月动量状态持续期）
related: [st-0002]
sources:
  - title: "Antonacci, G. Risk Premia Harvesting Through Dual Momentum. SSRN 2042750（2012-04 首发，2013-01 版逐字读取；发表于 Journal of Management & Entrepreneurship 2(1): 27-55, 2017-03——非 JPM 2016，简报猜测已纠正）"
    url: https://doi.org/10.2139/ssrn.2042750
    date: 2012-04
  - title: "Antonacci, G. (2014). Dual Momentum Investing: An Innovative Strategy for Higher Returns with Lower Risk. McGraw-Hill, ISBN 978-0-07-184944-9（2014-10-31；书目元数据经 Amazon/Newswire 核对，书内正文未读，GEM 三资产细节为出版方描述+二手佐证）"
    url: https://www.amazon.com/dp/0071849440
    date: 2014-10
entry_rules: 每月末比较 SPY（美股）与 ACWX（非美股）过去 12 个月总收益，取较高者为相对动量赢家；若赢家 12 个月总收益 > BIL（3 月美债代理）同期收益（绝对动量为正），次月首个交易日开盘满仓持有赢家；否则满仓持有 AGG（美国综合债）。只做多，不加杠杆，三选一。
exit_rules: 每月末重新计算双动量并滚动换仓（次月首个交易日开盘执行）；赢家切换或绝对动量转负时换仓至新目标；无月内止损止盈；暖机期（前 12 个月）信号未定义持现金。
position_sizing: 单一资产满仓（100% 资金持有 SPY/ACWX/AGG 之一），无杠杆、无分散；绝对动量门槛用 BIL 同期收益（论文 3 月美债口径的 ETF 代理）。
signal_definition: "r_X(m) = 过去 12 个月总收益（复权收盘，月末对月末），X ∈ {SPY, ACWX, BIL, AGG}；winner = argmax(r_SPY, r_ACWX)；target = winner 若 r_winner > r_BIL，否则 AGG；月度评估，无跳月（论文 'we adjust all our positions monthly without skipping a month'）；12 月形成期（论文 'twelve months is more common and has lower transaction costs, we will use that timeframe'）。"
intended_use: 全球股票双动量轮动框架：相对动量选美股/非美股，绝对动量决定是否退守债券，用于美股账户月度配置决策参考。
limitations: research_only（2026-11-26 batch-1 验证，未转正）：机制已逐字实现并在真实数据跑通——SPY/ACWX/AGG/BIL 双动量 2014-09→2026-11 累计 +115.96%、年化 6.51%、最大回撤 -33.72%、Sharpe 0.47、24 笔、盈利因子 3.18、23 次目标切换（SPY 66.8%/ACWX 20.4%/AGG 12.8% 时间），但核心主张（书副标题"更高收益更低风险"）未获支持：同期 SPY 买入持有 +338.02%（回撤 -33.72%、Sharpe 0.78）、60/40（SPY/AGG 月度再平衡）+172.72%（回撤 -21.59%、Sharpe 0.81）——GEM 绝对收益与 Sharpe 均跑输两个基准，最大回撤与 SPY 完全相同（-33.72%，2020-03 崩盘时满仓 SPY，月度动量来不及退守），"更低风险"不成立；fallback=BIL 变体（论文口径）+118.56%（与 AGG 版差 +2.6pp，敏感性可忽略）。已知缺陷（保留）：书内 GEM 页级规则未读——"美国综合债作为安全资产"来自出版方描述与二手摘要，非论文原文（论文 fallback 为 T-bills），验证结论不得标注为"书原文验证"；ACWX 代理论文 EAFE+、AGG 代理美国综合债、BIL 代理 3 月美债，代理误差未测；满仓单一资产无分散，跳空与换仓日风险集中；12 月窗口未做敏感性；相对动量平手取 SPY 为操作化默认（条目未指定）；论文发表载体 Journal of Management & Entrepreneurship 2017（非 JPM 2016）。结论只适用于有界版本，不外推到书内未读页级规则、论文 T-bill fallback 口径、其他形成期。引用必须标注"未验证，仅供参考"。
created: 2026-11-26
updated: 2026-11-26
---

# Antonacci 双动量 GEM（美股/非美股/债券，文献操作化）

**验证声明：2026-11-26 batch-1 独立验证完成，判定 research_only（未转正）。双动量轮动机制跑通，但"更高收益更低风险"主张未获支持——绝对收益与 Sharpe 均跑输 SPY 买入持有与 60/40，最大回撤与 SPY 相同。引用必须标注"未验证，仅供参考"。证据见 [evidence/st-0005/](../evidence/st-0005/)。**

来源经 librarian 实际抓取核对：SSRN DOI 10.2139/ssrn.2042750（Crossref 确认；SSRN 页对自动抓取 403，论文 2013 版 PDF 经第三方镜像逐字提取）；书元数据经 Amazon 产品页与 Newswire 出版方新闻稿核对（McGraw-Hill，2014-10-31，ISBN 9780071849449）。**诚实性声明：书内正文未读**，GEM 三资产实现（美股/非美股/综合债）为出版方描述（"combines U.S. stock, non-U.S. stock, and aggregate bond indices"）+二手佐证；论文原文确认的是 12 月形成期、月度无跳月、T-bill 绝对门槛与 US vs EAFE+ 股票模块。

## 验证记录（2026-11-26）

- **方法**：逐字实现——每月末比较 SPY 与 ACWX 过去 12 个月总收益（复权收盘月末对月末），取高者为赢家；赢家 12 月收益 > BIL 同期收益则次月满仓赢家，否则满仓 AGG（书 GEM 安全资产）；月度无跳月、只做多、无杠杆；暖机（前 12 个月）持现金。VT 官方日线引擎，月末信号次日开盘成交（内置 1 bar 延迟），`position_adjustment=hold`。相对动量平手取 SPY（操作化默认，条目未指定，已声明）。fallback=BIL 变体（论文 T-bill 口径）作敏感性。
- **标的与窗口**：SPY/ACWX/AGG/BIL（yfinance 复权日线，流动性 ETF 代理）。评估 2014-09-02→2026-11-25（数据自 2013-06 供 12 月暖机）。成本 US 5bps/边滑点零佣金。
- **结果**：GEM（AGG fallback）累计 +115.96%、年化 6.51%、最大回撤 -33.72%、Sharpe 0.47、24 笔、盈利因子 3.18、23 次切换（SPY 66.8%/ACWX 20.4%/AGG 12.8% 时间，BIL 0%）。对照：SPY 买入持有 +338.02%（回撤 -33.72%、Sharpe 0.78）；60/40 月度再平衡 +172.72%（回撤 -21.59%、Sharpe 0.81）。**GEM 全面跑输**；最大回撤与 SPY 完全相同（2020-03 满仓 SPY 承受全部崩盘，月度动量滞后）。fallback=BIL 变体 +118.56%（差 +2.6pp，可忽略）。前后半段 +20.76%/+80.38%。
- **判定**：research_only——机制按规则运行（轮动与退守真实发生），但文献"更高收益更低风险"的预测/绩效主张在本有界窗口未获支持（收益与 Sharpe 跑输、回撤未降）；书正文未读缺口保留。证据阶梯停留在 backtest 阶段。

## 规则详述

- **相对动量**：每月末比较 SPY 与 ACWX 过去 12 个月总收益（复权收盘），取高者为赢家（论文股票模块 MSCI US vs MSCI EAFE+ 的 ETF 代理）。
- **绝对动量**：赢家 12 个月总收益 > BIL 同期收益（论文："Positive absolute momentum exists when the excess return of an asset is positive over the look back period"，门槛为 3 月美债）→ 持有赢家；否则 → 持有 AGG（书 GEM 安全资产；论文 fallback 为 T-bills，差异显式声明）。
- **执行**：月末收盘定信号，次月首个交易日开盘成交；月度无跳月（论文逐字）；持有至下月末重评。无月内止损。
- **仓位**：100% 单一资产（SPY/ACWX/AGG 三选一），无杠杆。
- **暖机**：前 12 个月信号未定义 → 现金。
- **成本与窗口**：US 滑点 5bps/边零佣金；2014-09→2026-11（ACWX 2008 上市全覆盖）；年换手约 2-6 次（动量状态切换）。
- **对照基准**：SPY 买入持有；60/40（SPY/AGG）；可选 fallback=BIL 变体（论文口径）作敏感性。

## 默认边界条件（操作化）

| 原始主张（文献） | 有界版本（本条目） | 默认值依据 |
| --- | --- | --- |
| 12 月形成期、月度调整无跳月 | 同 | 论文默认值（2013 版 PDF 逐字读取） |
| 绝对动量门槛 = 3 月美债超额收益 | BIL ETF 同期收益代理 | 论文规则；BIL 代理为操作化默认 |
| 股票模块 MSCI US vs EAFE+（1987 后 ACWI ex-US） | SPY vs ACWX | 操作化默认（指数→ETF 代理） |
| 书 GEM 安全资产 = 美国综合债 | AGG | 书来源（出版方描述+二手佐证，书正文未读）；论文 fallback=T-bills，差异声明 |
| 执行时点未注明 | 次月首日开盘成交 | 首轮验证惯例 |
| 评估窗口 | 2014-09→2026-11 | 首轮验证惯例 |

**验证结论只适用于上述有界版本，不外推到原始模糊主张**（不外推到书内未读的页级规则、不外推到论文 T-bill fallback 口径、不外推到其他形成期）。

## 适用场景

- 美股账户全球股票轮动 + 熊市退守债券；低换手（年 2-6 次）长期配置。
- 数据条件：SPY/ACWX/AGG/BIL yfinance 日线已实证可用类；需 12 个月暖机。
- 与 st-0004（TSMOM）同族但更集中：双动量三选一 vs 八资产逆波动率。

## 风险

- **来源缺口**：书 GEM 页级规则未读，安全资产与换仓细节存在二手转述误差可能；验证结论不得标注为"书原文验证"。
- **集中风险**：满仓单一资产，换仓日跳空与单一市场黑天鹅无分散缓冲。
- **动量崩溃与鞭打**：震荡市赢家频繁切换（whipsaw）；急跌反弹期动量失效（st-0002 同款风险）。
- **代理误差**：ACWX/AGG/BIL 与原文指数口径差异；债券腿在加息期与股票同跌（2022）。
- **参数敏感**：12 月窗口为文献默认，6 月变体结果可能不同；未做敏感性。
