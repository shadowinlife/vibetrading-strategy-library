---
id: in-0008
type: indicator
title: 全A等权/中位数市净率系列（market-index-pb，marketId 参数化）
status: candidate
markets: [ashare]
asset_classes: [equity, index]
horizon: 月频序列，中长期估值温度计
related: [in-0006, in-0007, kn-0003]
formula: |
  equalWeightAveragePB = 股票池等权平均市净率
  middlePB = 股票池市净率中位数
  weightingAveragePB = 加权平均市净率（样本中恒为 0.0，疑似未提供，禁用）
data_source: |
  legulegu 端点 /api/stock-data/market-index-pb?marketId=<市场/指数代码>&token=（all-pb 页，React 族）。
  频率：月频（月末采样；实测 000300.XSHG 260 点 2005-04-29→2026-11-27，000010.XSHG/000016.XSHG 各 263 点 2005-01-31 起，
  000015.XSHG 251 点 2006-01-25 起，000009.XSHG 193 点 2010-11-30 起）。
  字段：equalWeightAveragePB/middlePB/weightingAveragePB/close。
  页面定位：全部A股等权重&中位数市净率（站点自述"基于A股PB中位数的估值温度计"，2005 至今）；
  页面默认全A实例参数（候选 marketId=ALL）未测。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 market-index-pb:000300.XSHG:middlePB（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 选 marketId（参数表见口径说明；全A实例须先探测确认）；
  2. GET /api/stock-data/market-index-pb?marketId=<id>&token=<MD5(当天 YYYY-MM-DD)>；
  3. 取 middlePB 为主口径、equalWeightAveragePB 作对照；weightingAveragePB 样本恒 0，不得参与计算；
  4. 历史分位自行重算并注明窗口；
  5. 输出附 marketId、口径、区间与数据日期。
unit: PB 为倍（无量纲）。
sources:
  - title: 乐咕乐股网：全部A股等权重&中位数市净率走势图（all-pb）
    url: https://www.legulegu.com/stockdata/all-pb
    date: 2026-11-28
intended_use: A 股整体（或指定指数池）PB 估值温度的月频度量，与 PE 温度计（in-0007）组合判断估值与盈利质量。
limitations: |
  candidate 未验证。实测参数仅 000009.XSHG/000010.XSHG/000015.XSHG/000016.XSHG/000300.XSHG；
  000852.XSHG/000902.XSHG/000903.XSHG/000905.XSHG/000906.XSHG/399324.XSHE/marketId=ALL 未测——
  页面标题所指的"全部A股"实例参数未获数据，现有样本是指数池口径，不得当作全A读数引用。
  weightingAveragePB 在全部样本行恒为 0.0（疑似字段未提供），任何使用该字段的计算都会失真；
  净资产口径与负净资产处理未声明；月频滞后；站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 全A等权/中位数市净率系列（market-index-pb）

## 口径说明

- 页面 all-pb 提供等权平均与中位数 PB（站点自述 2005 至今的"PB 中位数估值温度计"）。
- 参数化族：marketId 选择股票池。参数表（catalog.json 2026-11-28 实测）：

| marketId | 行数 | 覆盖区间 |
| --- | --- | --- |
| 000009.XSHG | 193 | 2010-11-30→2026-11-27 |
| 000010.XSHG | 263 | 2005-01-31→2026-11-27 |
| 000015.XSHG | 251 | 2006-01-25→2026-11-27 |
| 000016.XSHG | 263 | 2005-01-31→2026-11-27 |
| 000300.XSHG | 260 | 2005-04-29→2026-11-27 |
| 000852/000902/000903/000905/000906.XSHG、399324.XSHE、ALL | 未测 | — |

- 样本示例（marketId=000300.XSHG）：2005-04-29 middlePB=1.73、equalWeightAveragePB=1.94；2021-11-30 middlePB=2.95、equalWeightAveragePB=5.09（样本截断至前 200 点）。
- **weightingAveragePB 全部样本行恒为 0.0**：疑似该字段未提供数据，禁止使用。
- 频率以接口日期序列为准：月频。
- ClickHouse 映射：`legulegu.series`，series_id=`market-index-pb:<marketId>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 选 marketId；全A实例（候选 ALL）须先探测，未确认前只用已验证指数池。
2. 带当天 token 请求端点，解析月末序列。
3. 以 middlePB 为主口径，equalWeightAveragePB 作对照；跳过 weightingAveragePB。
4. 自算历史分位，注明窗口。
5. 输出附 marketId、口径、区间、数据日期。

## 解读注意

- PB 中位数比整体法 PB（in-0006）更少受金融大权重影响；等权平均高于中位数提示小票净资产溢价/壳价值。
- PB 温度计须与盈利联用：PB 低而 ROE 趋势下行是价值陷阱，不是便宜。
- 月频滞后；当月点随最新交易日漂移。
- 与 PE 温度计（in-0007）同向抬升才是全面过热信号；单口径抬升可能只是结构变化。
- 本条目 candidate，引用须标注未验证；现有样本为指数池口径，不是全A读数。
