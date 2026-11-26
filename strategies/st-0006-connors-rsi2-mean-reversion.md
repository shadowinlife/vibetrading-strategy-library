---
id: st-0006
type: strategy
title: Connors RSI(2) 均值回归（200 日均线过滤，文献操作化）
status: research_only
markets: [us]
asset_classes: [equity]
horizon: 数日（短期均值回归）
sources:
  - title: "Connors, L., & Alvarez, C. (2008). Short Term Trading Strategies That Work. TradingMarkets Publishing Group, 140pp, ISBN 978-0-9819239-0-1（出版年 2008-11-01 经 Amazon 产品页核对；常被引为 2009，差异已注明；书内正文未读）"
    url: https://www.amazon.com/dp/0981923909
    date: 2008-11
  - title: "StockCharts ChartSchool: RSI(2) 交易策略（规则二手正典页，明确归属 Connors：200 日 SMA 过滤、RSI(2)<10 买、>90 卖/做空、收盘上穿 5 日 SMA 离场、不用止损；2026-11-26 实际抓取）"
    url: https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2
    date: 2026-11
entry_rules: 三 ETF 独立 sleeve（SPY/QQQ/IWM 各 1/3 资金）；收盘价 > 200 日 SMA（趋势过滤）且 RSI(2) < 10 时，次日开盘该 sleeve 满仓买入；只做多，不加杠杆；RSI(2) 为 Wilder 2 期 RSI。
exit_rules: 持仓后收盘价上穿 5 日 SMA（收盘 > 5 日 SMA）时次日开盘该 sleeve 清仓（StockCharts 归属 Connors 的离场规则）；失效退出：收盘价跌破 200 日 SMA 时次日开盘清仓（操作化默认，趋势过滤破坏）；不设固定止损（Connors 不主张止损，二手页明确）；RSI(2)>90 离场为简报变体，作敏感性对照而非主规则。
position_sizing: 每 ETF 独立 sleeve 各 1/3 资金，sleeve 内满仓进出（0/100% 两态）；组合最大仓位 100%（三标的同时触发）；不加杠杆、不摊平；无信号时该 sleeve 持现金。
signal_definition: "RSI(2) = Wilder RSI(period=2)（收盘日收益率）；MA200 = close.rolling(200).mean()；MA5 = close.rolling(5).mean()；入场 = (close > MA200) AND (RSI2 < 10)；离场 = (close > MA5) OR (close < MA200)；信号收盘计算、次日开盘成交。阈值 10/90 为书中梯度（2/5/10/25 买档、75/90/95 卖档）的一个陈述变体，非唯一默认；常见实现版用 RSI(2)<5，验证须做 <5 敏感性。"
intended_use: 美股大盘 ETF 短期超卖均值回归框架：上升趋势中的 2 期 RSI 极端低位买入、回归 5 日均线离场，用于数日级持仓决策参考。
limitations: research_only（2026-11-26 batch-1 验证，未转正）：机制已逐字实现并在真实数据跑通——SPY/QQQ/IWM 三 sleeve RSI(2)<10 + 200 日过滤 + 收盘上穿 5 日均线离场，2014-09→2026-11 累计 +23.73%、年化 1.76%、最大回撤 -17.99%、Sharpe 0.35、303 笔、盈利因子 1.37，但均值回归边际弱且成本脆弱：303 笔平均收益 +0.22%（naive t=1.95、p=0.053，跨 sleeve 日历重叠，未达 5% 显著）；同期三 ETF 等权买入持有 +346.71%，策略大幅跑输；成本敏感显著——滑点 5bps→10bps/边累计收益 +23.73%→+11.85%（拖累 11.9pp）。敏感性（必做已做）：入场 <5 变体 +22.22%（回撤 -12.25%、Sharpe 0.42、166 笔）；离场 RSI(2)>90 变体 +74.02%（Sharpe 0.60、227 笔，优于主规则但仍远跑输买入持有）；无 200 日过滤变体 +41.87%（回撤 -29.82%、426 笔）。已知缺陷（保留）：书内正文未读——阈值与离场规则来自 StockCharts ChartSchool 二手正典页（明确归属 Connors），10/90 只是书中梯度的一个陈述变体（常见实现版 <5），不得宣称 10/90 为"书唯一默认"；出版年 2008（常被引为 2009）已按 ISBN 纠正；有界版本仅 3 个 ETF，个股适用性未覆盖；无止损（文献主张）单笔尾部风险无界，200 日过滤破坏退出为操作化补丁；RSI(2) 对跳空与单日极端收益敏感。结论只适用于有界版本，不外推到书内未读其他阈值档、个股、无过滤版本。引用必须标注"未验证，仅供参考"。
created: 2026-11-26
updated: 2026-11-26
---

# Connors RSI(2) 均值回归（200 日均线过滤，文献操作化）

**验证声明：2026-11-26 batch-1 独立验证完成，判定 research_only（未转正）。RSI(2) 均值回归机制跑通，但边际弱（303 笔 naive t=1.95、p=0.053）、成本脆弱（滑点翻倍收益减半）、大幅跑输买入持有；阈值与离场敏感性已做。引用必须标注"未验证，仅供参考"。证据见 [evidence/st-0006/](../evidence/st-0006/)。**

来源经 librarian 实际抓取核对：Amazon 产品页确认书目（TradingMarkets，2008-11-01，140pp，ISBN 9780981923901）；规则文本读取自 StockCharts ChartSchool RSI(2) 页（二手正典，明确归属 Connors）："Traders should look for buying opportunities when 2-period RSI moves below 10"；"Connors recommends the 200-day moving average"；"exiting long positions on a move above the 5-day SMA"；"Connors does not advocate using stops"。**诚实性声明：书内正文未读**，阈值梯度（2/5/10/25 买档）来自章节级二手摘要，10/90 为一个陈述变体。

## 验证记录（2026-11-26）

- **方法**：逐字实现——三 ETF 独立 sleeve 各 1/3 资金；收盘 > 200 日 SMA 且 Wilder RSI(2) < 10 次日开盘满仓买入；持仓后收盘 > 5 日 SMA 次日开盘清仓；失效退出收盘 < 200 日 SMA 次日开盘清仓（操作化补丁）；无固定止损。RSI(2) 用 ewm(alpha=1/2, adjust=False) 精确复现 Wilder 种子（前 2 期均值）与 RMA 递推。VT 官方日线引擎，信号收盘计算次日开盘成交（内置 1 bar 延迟），`position_adjustment=hold`，逐 sleeve 状态机。
- **标的与窗口**：SPY/QQQ/IWM（yfinance 复权日线，流动性最好的三个美股大盘/成长/小盘 ETF）。评估 2014-09-02→2026-11-25（数据自 2013-06 供 200 日暖机）。成本 US 5bps/边滑点零佣金。
- **结果（主规则 <10/MA5 离场/有过滤）**：累计 +23.73%、年化 1.76%、最大回撤 -17.99%、Sharpe 0.35、303 笔、盈利因子 1.37；303 笔平均收益 +0.22%（naive t=1.95、p=0.053，跨 sleeve 日历重叠，未达 5% 显著）。同期三 ETF 等权买入持有 +346.71%——大幅跑输。
- **敏感性（条目声明必做，已做）**：入场 <5：+22.22%（回撤 -12.25%、Sharpe 0.42、166 笔）；离场 RSI(2)>90：+74.02%（Sharpe 0.60、227 笔，优于主规则但仍远跑输买入持有）；无 200 日过滤：+41.87%（回撤 -29.82%、426 笔）。**成本扫描**：滑点 5bps→10bps/边，+23.73%→+11.85%（拖累 11.9pp，高换手成本脆弱如实记录）。
- **判定**：research_only——机制跑通但均值回归边际弱、统计分离不足（p=0.053）、成本脆弱、全面跑输买入持有；阈值/离场/过滤敏感性显示结果对操作化选择敏感。证据阶梯停留在 backtest 阶段。

## 规则详述

- **信号定义**：RSI(2) = Wilder 2 期 RSI；趋势过滤 close > MA200；入场 RSI(2) < 10（变体，见边界条件）；离场 close > MA5（二手页归属 Connors 的离场规则）。
- **入场**：收盘确认 (close > MA200) 且 (RSI2 < 10)，次日开盘该 sleeve 满仓买入。
- **出场**：收盘 > MA5 → 次日开盘清仓；失效退出 close < MA200 → 次日开盘清仓（操作化默认）；无固定止损（文献主张）。
- **仓位**：SPY/QQQ/IWM 三独立 sleeve 各 1/3 资金，sleeve 内 0/100% 两态；无杠杆。
- **执行假设**：日线、信号收盘计算、次日开盘成交；US 滑点 5bps/边零佣金（首轮惯例）。窗口 2014-09→2026-11；200 日暖机。
- **敏感性（验证必做）**：入场阈值 <5（常见实现版）vs <10；离场 RSI(2)>90（简报变体）vs close>MA5（二手页规则）；有/无 200 日过滤。
- **对照基准**：各 ETF 买入持有；无过滤 RSI(2) 变体。

## 默认边界条件（操作化）

| 原始主张（文献/二手正典） | 有界版本（本条目） | 默认值依据 |
| --- | --- | --- |
| RSI(2) 低位买、高位卖（书梯度 2/5/10/25 与 75/90/95） | 入场 <10、离场 close>MA5 | 10 为二手页陈述变体（非唯一默认）；MA5 离场：StockCharts 归属 Connors；<5 敏感性必做 |
| 200 日 SMA 趋势过滤 | 同 | 二手正典页（归属 Connors） |
| 不用止损 | 无固定止损 + MA200 破坏退出 | 无止损：文献主张；MA200 失效退出：操作化默认 |
| 书检验个股与 ETF | 仅 SPY/QQQ/IWM 三 ETF | 操作化默认（首轮 yfinance 已实证类；个股池未纳入） |
| 执行时点未注明 | 次日开盘成交 | 首轮验证惯例 |
| 仓位未注明 | 三 sleeve 各 1/3，sleeve 满仓进出 | 操作化默认 |

**验证结论只适用于上述有界版本，不外推到原始模糊主张**（不外推到书内未读的其他阈值档、不外推到个股、不外推到无过滤版本）。

## 适用场景

- 美股大盘 ETF 上升趋势中的短期超卖反弹；数日级持有、高换手。
- 数据条件：yfinance 日线已实证；需 200 日暖机。
- 与趋势类条目（st-0001/st-0003）互补：趋势过滤内的均值回归 sleeve。

## 风险

- **来源缺口**：书正文未读，阈值与离场规则存在二手转述误差；引用必须注明二手来源与变体身份。
- **尾部风险**：无止损 + 数日持有，黑天鹅跳空（如 2020-03）单笔亏损无界；MA200 失效退出滞后。
- **成本侵蚀**：高换手（年均数十笔/sleeve），5bps/边下成本占比高；成本敏感性未测前不得宣称净收益。
- **阈值任意性**：10 vs 5 vs 2 结果差异可能显著；只报单一阈值即挑选偏差。
- ** regime 依赖**：200 日过滤在熊市空仓（躲过主跌但也错过 V 型反弹首段）；震荡市 RSI 极端频繁触发鞭打。
