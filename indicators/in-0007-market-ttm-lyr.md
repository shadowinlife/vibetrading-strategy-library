---
id: in-0007
type: indicator
title: 全A等权/中位数市盈率系列（market-ttm-lyr，marketId 参数化）
status: candidate
markets: [ashare]
asset_classes: [equity, index]
horizon: 月频序列，中长期估值温度计
related: [in-0005, in-0008, kn-0003]
formula: |
  averagePETTM / averagePELYR = 股票池等权平均 TTM/静态市盈率
  middlePETTM / middlePELYR = 股票池 TTM/静态市盈率中位数
  （等权平均 = 成分股 PE 的算术平均；中位数 = 成分股 PE 的中位值；亏损股处理规则未随接口声明）
data_source: |
  legulegu 端点 /api/stock-data/market-ttm-lyr?marketId=<市场/指数代码>&token=（a-ttm-lyr 页，React 族）。
  频率：月频（月末采样；实测 000300.XSHG 260 点 2005-04-29→2026-11-27，000010.XSHG/000015.XSHG/000016.XSHG 各 263 点 2005-01-31 起，000009.XSHG 193 点 2010-11-30 起）。
  字段：averagePETTM/averagePELYR/middlePETTM/middlePELYR/close。
  页面定位：全部A股等权重市盈率/中位数市盈率（站点称"基于A股PE中位数的估值温度计"）；
  但本次实测参数均为指数代码，页面默认的全A实例参数（候选 marketId=5）未测。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 market-ttm-lyr:000300.XSHG:middlePETTM（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 选 marketId（参数表见口径说明；全A实例参数须先探测确认）；
  2. GET /api/stock-data/market-ttm-lyr?marketId=<id>&token=<MD5(当天 YYYY-MM-DD)>；
  3. 取中位数（middlePETTM/middlePELYR）为稳健口径，等权平均作对照；
  4. 历史分位自行重算并注明窗口；
  5. 输出附 marketId、口径、区间与数据日期。
unit: PE 为倍（无量纲）。
sources:
  - title: 乐咕乐股网：全部A股等权重市盈率 中位数市盈率（a-ttm-lyr）
    url: https://www.legulegu.com/stockdata/a-ttm-lyr
    date: 2026-11-28
intended_use: A 股整体（或指定指数池）估值温度的月频度量，中位数口径规避大权重股扭曲，供 kn-0003 估值分位判断使用。
limitations: |
  candidate 未验证。实测参数仅 000009.XSHG/000010.XSHG/000015.XSHG/000016.XSHG/000300.XSHG；
  000852.XSHG/000902.XSHG/000903.XSHG/000905.XSHG/000906.XSHG/399324.XSHE/marketId=5 未测——
  页面标题所指的"全部A股"实例参数未获数据，现有样本是指数池口径，不得当作全A读数引用。
  等权平均受亏损股负 PE 与极端值影响（剔除规则未声明）；月频滞后；
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 全A等权/中位数市盈率系列（market-ttm-lyr）

## 口径说明

- 页面 a-ttm-lyr 提供等权平均与中位数两种 PE 口径（TTM 与静态并列），站点自述为"基于A股PE中位数的估值温度计"。
- 参数化族：marketId 选择股票池。参数表（catalog.json 2026-11-28 实测）：

| marketId | 行数 | 覆盖区间 |
| --- | --- | --- |
| 000009.XSHG | 193 | 2010-11-30→2026-11-27 |
| 000010.XSHG | 263 | 2005-01-31→2026-11-27 |
| 000015.XSHG | 263 | 2005-01-31→2026-11-27 |
| 000016.XSHG | 263 | 2005-01-31→2026-11-27 |
| 000300.XSHG | 260 | 2005-04-29→2026-11-27 |
| 000852/000902/000903/000905/000906.XSHG、399324.XSHE、5 | 未测 | — |

- 样本示例（marketId=000300.XSHG）：2005-04-29 middlePETTM=20.08、averagePETTM=32.98、middlePELYR=20.66、averagePELYR=33.43；2021-11-30 middlePETTM=24.14、averagePETTM=36.52（样本截断至前 200 点）。
- 等权平均显著高于中位数（样本差约 12–13 倍 PE），说明池内存在高 PE/亏损极端值——等权口径的解释力弱于中位数。
- 频率以接口日期序列为准：月频。
- ClickHouse 映射：`legulegu.series`，series_id=`market-ttm-lyr:<marketId>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 选 marketId；全A实例（候选 marketId=5）须先探测，未确认前只用已验证指数池。
2. 带当天 token 请求端点，解析月末序列。
3. 以 middlePETTM 为主口径，averagePETTM 作对照，两者同时报告。
4. 自算历史分位，注明窗口。
5. 输出附 marketId、口径、区间、数据日期。

## 解读注意

- 中位数 PE 是"典型股票"的估值，比整体法（in-0005）更少受大权重股影响；但中位数低不等于市场便宜（小票流动性折价）。
- 等权平均被亏损股与极端值拉高，单独使用会系统性高估估值水平。
- 月频滞后，短期择时须配日频情绪/拥挤指标（in-0003 成交集中度）。
- 与 PB 温度计（in-0008）组合：PE 中位数低而 PB 中位数高时，提示盈利质量差而非便宜。
- 本条目 candidate，引用须标注未验证；现有样本为指数池口径，不是全A读数。
