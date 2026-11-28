---
id: in-0005
type: indicator
title: 指数市盈率系列（index-basic-pe，静态/TTM × 整体法/等权/中位数，indexCode 参数化）
status: candidate
markets: [ashare]
asset_classes: [equity, index]
horizon: 月频序列，中长期估值解读
related: [in-0001, in-0006, kn-0003]
formula: |
  lyrPe = 指数成分股静态市盈率（整体法，年报净利润口径）
  ttmPe = 指数成分股滚动市盈率（整体法，TTM 净利润口径）
  addLyrPe / addTtmPe = 等权平均静态/TTM 市盈率
  middleLyrPe / middleTtmPe = 中位数静态/TTM 市盈率
  lyrPeQuantile 等 *Quantile 字段 = 对应 PE 的历史分位（0–1）
  （字段语义按 legulegu 图表惯例与字段名推断，站点未随接口提供计算说明，整体法/等权的具体剔除规则未验证）
data_source: |
  legulegu 端点 /api/stockdata/index-basic-pe?indexCode=<指数代码>&token=（React 页族，token=MD5(当天日期)）。
  频率：月频（样本日期为月末采样，当月点为最新交易日；实测 indexCode=000009.SH 193 点，2010-11-30→2026-11-27）。
  字段：lyrPe/ttmPe/addLyrPe/addTtmPe/middleLyrPe/middleTtmPe/close/totalMv；近期行附 *Quantile 分位字段
  （如 2026-11-27：ttmPe=33.65、ttmPeQuantile=0.43041、middleTtmPe=22.38、middleTtmPeQuantile=0.32776），早期行无分位字段。
  totalMv 为成分股总市值（单位未随样本声明，量级推断为万元，使用前需核对）。
  覆盖页面：gz2000-ttm-lyr（国证2000市盈率）、sz000015-ttm-lyr（上证红利市盈率）等指数 PE 页。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 index-basic-pe:000009.SH:ttmPe、index-basic-pe:000009.SH:middleTtmPe（ch-legulegu-sync 管道并行建设中，此处仅引用约定，不引用既有表数据）。
computation: |
  1. 选定指数代码 indexCode（参数表见口径说明）；
  2. GET /api/stockdata/index-basic-pe?indexCode=<code>&token=<MD5(当天 YYYY-MM-DD)>，得月末日期序列；
  3. 按需取整体法（lyrPe/ttmPe）、等权（addLyrPe/addTtmPe）或中位数（middleLyrPe/middleTtmPe）口径；
  4. 分位直接取近期行的 *Quantile 字段（0–1），或自行对历史序列重算百分位（窗口须注明）；
  5. 输出序列附指数代码、口径、覆盖区间与数据日期。
unit: PE 为倍（无量纲）；分位为 0–1 比率；totalMv 单位未声明。
sources:
  - title: 乐咕乐股网：国证2000市盈率走势图（index-basic-pe 端点族）
    url: https://www.legulegu.com/stockdata/gz2000-ttm-lyr
    date: 2026-11-28
  - title: 乐咕乐股网：上证红利市盈率走势图（index-basic-pe 端点族）
    url: https://www.legulegu.com/stockdata/sz000015-ttm-lyr
    date: 2026-11-28
intended_use: A 股宽基/风格指数的月频估值贵贱与历史位置度量，供估值分位均值回归（kn-0003）与指数比较使用。
limitations: |
  candidate 未验证。参数覆盖不全：仅 indexCode=000009.SH 实测返回数据（193 点）；
  000010.SH/000015.SH/000016.SH 探测返回 429、000300.SH 返回 504（探测期限流/超时，非权限结论）；
  000852.SH/000903.SH/000905.SH/000906.SH/399303.SZ/399324.SZ/399330.SZ/399673.SZ 未测。
  页面自身指数参数（如国证2000、上证红利对应代码）未被本次探测覆盖，样本数值属于 000009.SH，不得当作页面标题所指数的数值引用。
  分位字段仅近期行出现，历史窗口定义未声明；整体法/等权的亏损股剔除规则未声明；月频对短期择时滞后。
  站点免责声明：数据来自第三方自动采集，不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 指数市盈率系列（index-basic-pe）

## 口径说明

- 一个端点族覆盖多个指数 PE 页面（参数化族）：`/api/stockdata/index-basic-pe?indexCode=<code>`。
- 三种口径并列：整体法（lyrPe/ttmPe）、等权平均（addLyrPe/addTtmPe）、中位数（middleLyrPe/middleTtmPe）。静态（LYR）用年报净利润，TTM 用滚动四季净利润（按字段名与 legulegu 图表惯例推断，站点未随接口声明剔除规则）。
- 参数表（catalog.json 2026-11-28 实测记录）：

| indexCode | 探测结果 | 覆盖区间 | 备注 |
| --- | --- | --- | --- |
| 000009.SH | 200，193 点 | 2010-11-30→2026-11-27 | 有样本；上证380（代码常识，未随接口声明） |
| 000010.SH / 000015.SH / 000016.SH | 429 | — | 探测期限流，未获数据 |
| 000300.SH | 504 | — | 探测期超时，未获数据 |
| 000852.SH / 000903.SH / 000905.SH / 000906.SH / 399303.SZ / 399324.SZ / 399330.SZ / 399673.SZ | 未测 | — | 后续批次补测 |

- 频率以接口日期序列为准：月频（月末采样，当月点为最新交易日），不是页面文案宣称的日频。
- 样本示例（indexCode=000009.SH）：2010-11-30 lyrPe=70.81、ttmPe=53.68、middleLyrPe=56.26；2026-11-27 lyrPe=37.16、ttmPe=33.65、middleTtmPe=22.38、ttmPeQuantile=0.43041。
- ClickHouse 映射：`legulegu.series`，series_id=`index-basic-pe:<indexCode>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 选指数代码（默认先用已验证的 000009.SH；其他代码须先探测确认）。
2. 带当天 token 请求端点，解析月末日期序列。
3. 按分析目标选口径：整体法受大权重股影响，中位数对亏损股与极端值更稳健。
4. 分位优先取接口 *Quantile 字段（注明窗口未声明）；自算分位时注明窗口长度。
5. 输出附代码、口径、区间、数据日期；缺参数实例时明说，不得用其他指数的数值顶替。

## 解读注意

- 高分位提示未来收益承压（kn-0003），不等于立即下跌；低分位可能是盈利下修中的价值陷阱。
- 整体法 PE 在亏损股占比高时失真，改用中位数或 PB（in-0006）。
- 月频序列对短期事件滞后；当月点随最新交易日变动，月末定稿前读数会漂移。
- 等权/中位数/整体法三口径数值差异大（样本 2010-11-30：70.81 vs 45.93 vs 56.26），跨口径比较无效。
- 分位字段窗口未声明，与自算 10 年分位不可直接混用；本条目 candidate，引用须标注未验证。
