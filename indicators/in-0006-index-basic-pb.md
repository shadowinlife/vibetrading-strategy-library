---
id: in-0006
type: indicator
title: 指数市净率系列（index-basic-pb，整体法/等权/中位数，indexCode 参数化）
status: candidate
markets: [ashare]
asset_classes: [equity, index]
horizon: 月频序列，中长期估值解读
related: [in-0001, in-0005, kn-0003]
formula: |
  pb = 指数成分股市净率（整体法口径，推断）
  addPb = 等权平均市净率（推断）
  middlePb = 中位数市净率（推断）
  PB = 市值 / 净资产；字段语义按 legulegu 图表惯例与字段名推断，站点未随接口提供计算说明
data_source: |
  legulegu 端点 /api/stockdata/index-basic-pb?indexCode=<指数代码>&token=（React 页族）。
  频率：月频（月末采样，当月点为最新交易日；实测 000300.SH 260 点 2005-04-29→2026-11-27，
  000010.SH/000016.SH 各 263 点 2005-01-31 起，000015.SH 263 点，000009.SH 193 点 2010-11-30 起）。
  字段：pb/addPb/middlePb/close。
  覆盖页面（一族多实例）：shanghaiPB（上证市净率）、shenzhenPB（深证主板市净率）、cybPB（创业板市净率）、
  ke-chuang-ban-pb（科创板市净率）、gz2000-pb（国证2000市净率）、sz000015-pb（上证红利市净率）。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 index-basic-pb:000300.SH:middlePb（ch-legulegu-sync 管道并行建设中，仅引用约定，不引用既有表数据）。
computation: |
  1. 选定指数代码 indexCode（参数表见口径说明）；
  2. GET /api/stockdata/index-basic-pb?indexCode=<code>&token=<MD5(当天 YYYY-MM-DD)>；
  3. 取 pb（整体法）/addPb（等权）/middlePb（中位数）之一，口径须随读数声明；
  4. 历史分位自行对序列重算（接口未提供分位字段），注明窗口；
  5. 输出附代码、口径、覆盖区间与数据日期。
unit: PB 为倍（无量纲）。
sources:
  - title: 乐咕乐股网：创业板市净率走势图（index-basic-pb 端点族）
    url: https://www.legulegu.com/stockdata/cybPB
    date: 2026-11-28
  - title: 乐咕乐股网：上证市净率走势图（index-basic-pb 端点族）
    url: https://www.legulegu.com/stockdata/shanghaiPB
    date: 2026-11-28
  - title: 乐咕乐股网：科创板市净率走势图（index-basic-pb 端点族）
    url: https://www.legulegu.com/stockdata/ke-chuang-ban-pb
    date: 2026-11-28
intended_use: A 股板块/宽基指数月频 PB 估值度量，亏损股密集板块（创业板/科创板）PE 失真时的替代估值锚，供 kn-0003 使用。
limitations: |
  candidate 未验证。实测参数仅 000009.SH/000010.SH/000015.SH/000016.SH/000300.SH 五个通用指数代码；
  000852.SH/000903.SH/000905.SH/000906.SH/399303.SZ/399324.SZ/399330.SZ/399673.SZ 及数字型市场代码（1/2/4/7/11）未测。
  六个页面自身的指数参数（创业板指/科创50/国证2000 等对应代码）未被探测覆盖——样本文件虽以页面命名，
  内容实为通用代码（000300.SH 或 000015.SH）的响应，不得当作该页面标题所指板块的数值引用。
  净资产口径（最新一期财报/剔除负净资产）未声明；月频滞后；站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 指数市净率系列（index-basic-pb）

## 口径说明

- 参数化族：一个端点覆盖上证/深证主板/创业板/科创板/国证2000/上证红利等 PB 页面，实例由 indexCode 区分。
- 字段三口径：pb（整体法，推断）、addPb（等权平均，推断）、middlePb（中位数，推断）。
- 参数表（catalog.json 2026-11-28 实测）：

| indexCode | 行数 | 覆盖区间 |
| --- | --- | --- |
| 000009.SH | 193 | 2010-11-30→2026-11-27 |
| 000010.SH | 263 | 2005-01-31→2026-11-27 |
| 000015.SH | 263 | 2005-01-31→2026-11-27 |
| 000016.SH | 263 | 2005-01-31→2026-11-27 |
| 000300.SH | 260 | 2005-04-29→2026-11-27 |
| 000852.SH/000903.SH/000905.SH/000906.SH/399303.SZ/399324.SZ/399330.SZ/399673.SZ/1/2/4/7/11 | 未测 | — |

- 样本示例（indexCode=000300.SH）：2005-04-29 pb=1.92、addPb=1.89、middlePb=1.71；2021-11-30 pb=5.1、addPb=1.55、middlePb=2.96（样本截断至前 200 点，全序列至 2026-11-27）。
- 频率以接口日期序列为准：月频。
- ClickHouse 映射：`legulegu.series`，series_id=`index-basic-pb:<indexCode>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 选指数代码；页面标题所指板块的代码须先探测确认，不得假设。
2. 带当天 token 请求端点，解析月末序列。
3. 选口径（整体法/等权/中位数）并随读数声明。
4. 自算历史分位（接口无分位字段），注明窗口。
5. 输出附代码、口径、区间、数据日期。

## 解读注意

- PB 对亏损股密集板块比 PE 稳健，但净资产为负/接近零时 PB 失真，中位数口径更可靠。
- 整体法受金融等大权重净资产影响，与等权/中位数读数差异大（样本 2021-11-30：5.1 vs 1.55 vs 2.96），跨口径比较无效。
- 月频滞后；当月点随最新交易日漂移。
- 高分位不等于立即下跌，低分位可能是净资产质量恶化（减值预期）；与盈利趋势（in-0026）组合印证。
- 本条目 candidate，引用须标注未验证；样本数值属于通用指数代码，不代表页面标题板块。
