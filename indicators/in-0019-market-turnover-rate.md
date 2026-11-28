---
id: in-0019
type: indicator
title: 市场换手率（market-turnover-rate，1/7/30日累计，日频）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日频
related: [in-0018, in-0003]
formula: |
  turnover1d = 全市场当日换手率（%）
  turnover7d / turnover30d = 近 7/30 日累计换手率（%，推断为日换手率滚动求和：
  样本 2023-11-27 turnover1d=1.0529、turnover7d=7.6718≈7×1.05、turnover30d=33.3404≈30×1.11，量级一致）
data_source: |
  legulegu 端点 /api/stockdata/market-turnover-rate?token=（market-turnover-rate 页，React 族）。
  频率：日频（实测 728 点，2023-11-27→2026-11-27，约 3 年——匿名窗口疑似 3 年，全历史深度未验证）。
  字段：tradeDate/turnover1d/turnover7d/turnover30d/shClose/szClose/hs300Close/cybClose/zz500Close。
  换手率分子分母口径（成交额/流通市值或总市值）未随接口声明。
  ClickHouse 映射：legulegu.series，无参数端点 param 段为 -（占位，不省略），series_id 如
  market-turnover-rate:-:turnover1d（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/market-turnover-rate?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析日频序列（tradeDate 为日期字段名，与其他端点的 date 不同）；
  3. 1d 为当日热度，7d/30d 为累计热度（滚动窗口口径推断，须验证）；
  4. 历史分位在 3 年窗口内自算并注明窗口受限；
  5. 与五个指数 close 对照观察量价关系。
unit: "%（换手率）"
sources:
  - title: 乐咕乐股网：市场换手率（market-turnover-rate）
    url: https://www.legulegu.com/stockdata/market-turnover-rate
    date: 2026-11-28
intended_use: A 股整体交易热度的日频度量，1d 捕捉情绪脉冲、7d/30d 捕捉热度趋势，供过热/冷清判断。
limitations: |
  candidate 未验证。匿名窗口约 3 年（2023-11-27 起），长期分位不可算；
  换手率分母口径未声明（流通/总市值差异显著）；7d/30d 的滚动求和口径为量级推断；
  全市场池范围（含北交所与否）未声明。站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 市场换手率（market-turnover-rate）

## 口径说明

- 全市场换手率三窗口：1d/7d/30d；样本 2023-11-27：1.0529%/7.6718%/33.3404%，7d≈7×1d、30d≈30×日均，推断为滚动累计。
- 附五个指数收盘对照：上证/深证/沪深300/创业板/中证500。
- 频率以接口日期序列为准：日频；窗口 2023-11-27→2026-11-27（728 点，约 3 年）。
- 分子分母口径未声明。
- ClickHouse 映射：`legulegu.series`，series_id=`market-turnover-rate:-:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 按 tradeDate 解析；三窗口并列报告。
3. 窗口内自算分位（注明仅 3 年）。
4. 与指数对照：放量滞涨/缩量上涨等量价结构。
5. 输出附窗口起点与口径待验证声明。

## 解读注意

- 换手率极端高位 = 情绪过热（顶部辅助证据），极端低位 = 冷清（底部区域特征），均非精确择时信号。
- 30d 累计平滑了脉冲，适合趋势判断；1d 适合事件反应。
- 3 年窗口覆盖的体制有限，分位读数对窗口敏感，不得外推"历史极端"。
- 与低换手占比（in-0018）联用：总换手高而低换手占比也高 = 成交向头部集中（in-0003）。
- 本条目 candidate，引用须标注未验证。
