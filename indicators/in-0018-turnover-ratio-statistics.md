---
id: in-0018
type: indicator
title: 换手率分布统计（market-turn-over-ratio-statistics-data，低换手个股家数，日频）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日频
related: [in-0017, in-0019, in-0003]
formula: |
  belowPercent1/3/5/10 = 当日换手率低于 1%/3%/5%/10% 的个股家数（按字段名推断）
  belowPermill8 = 当日换手率低于 0.8%（8‰）的个股家数（按字段名推断）
  低换手占比 = belowX / totalCompany
data_source: |
  legulegu 端点 /stockdata/market-turn-over-ratio-statistics-data?token=（market-turn-over-ratio-statistics 页，jQuery 族；
  亦为 broker-recommend-monthly-regression/statistics 等页共享组件）。
  频率：日频（实测 4849 点，2006-12-01→2026-11-27）。
  字段：belowPermill8/belowPercent1/belowPercent3/belowPercent5/belowPercent10/totalCompany/close。
  样本 2006-12-01：belowPermill8=17、belowPercent1=29、belowPercent3=615、belowPercent5=990、belowPercent10=1238、
  totalCompany=1296、close=2102.05（上证综指量级，对照指数未随接口声明）。
  ClickHouse 映射：legulegu.series，无参数端点 param 段为 -（占位，不省略），series_id 如
  market-turn-over-ratio-statistics-data:-:belowPercent1（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /stockdata/market-turn-over-ratio-statistics-data?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析日频序列；各阈值家数除以 totalCompany 得占比；
  3. 占比序列的历史分位自行计算并注明窗口；
  4. 与指数 close 对照观察"指数涨而低换手占比升"的宽度背离；
  5. 输出附阈值口径、区间与数据日期。
unit: 家数（只）；占比为 %。
sources:
  - title: 乐咕乐股网：换手率统计（market-turn-over-ratio-statistics）
    url: https://www.legulegu.com/stockdata/market-turn-over-ratio-statistics
    date: 2026-11-28
intended_use: 市场交易热度的结构度量：低换手个股占比抬升提示交易冷清/宽度恶化，与成交集中度（in-0003）互补。
limitations: |
  candidate 未验证。阈值语义按字段名推断（Permill8=0.8%），换手率分母（流通股本/总股本）未声明；
  totalCompany 池范围（是否含 ST/北交所/停牌）未声明；close 对照指数未声明（量级为上证综指）。
  2006-12 起样本早期 totalCompany≈1300，与当前全 A 数量差异大，占比跨年代比较须注意池扩张。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 换手率分布统计（market-turn-over-ratio-statistics-data）

## 口径说明

- 统计当日换手率低于各阈值（0.8%/1%/3%/5%/10%）的个股家数，totalCompany 为池内总数。
- 样本（2006-12-01）：1296 只中 1238 只换手 <10%、990 只 <5%、615 只 <3%、29 只 <1%、17 只 <0.8%。
- 频率以接口日期序列为准：日频，2006-12-01→2026-11-27（4849 点）。
- 阈值含义与换手率分母口径未随接口声明，按字段名推断。
- ClickHouse 映射：`legulegu.series`，series_id=`market-turn-over-ratio-statistics-data:-:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 各阈值家数 / totalCompany → 占比序列。
3. 自算历史分位（窗口注明）。
4. 与 close 对照找宽度背离。
5. 输出附阈值口径与池范围待验证声明。

## 解读注意

- 低换手占比高 = 多数股票无人交易，行情靠少数头部股支撑——与成交集中度（in-0003）同向印证结构恶化。
- 占比的绝对水平随池扩张漂移（2006 年 1300 只 vs 当前 5000+ 只），跨年代比较用分位而非绝对值。
- 换手率阈值对流通盘口径敏感，分母未声明前不做跨源比较。
- 日频但非实时；盘中决策须配日内宽度（in-0017）。
- 本条目 candidate，引用须标注未验证。
