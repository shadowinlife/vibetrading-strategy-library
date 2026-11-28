---
id: in-0020
type: indicator
title: 破净股统计（below-net-asset-statistics-data，marketId 参数化，日频）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日频
related: [in-0006, in-0008, kn-0003]
formula: |
  belowNetAsset = 池内破净（PB<1）个股家数
  破净比例 = belowNetAsset / totalCompany
data_source: |
  legulegu 端点 /stockdata/below-net-asset-statistics-data?marketId=<市场代码>&token=（below-net-asset-statistics 页，jQuery 族；
  亦为多页共享组件）。
  频率：日频（实测 marketId=000016.SH 5318 点、空 marketId 5307 点，均 2005-01-05→2026-11-27）。
  字段：belowNetAsset/totalCompany/close/date。
  参数事实：marketId=000016.SH 池 totalCompany=49（2005-01-05，上证50 量级）；
  空 marketId 池 totalCompany=1352（2005-01-05，全A量级）——两池行数差 11 点，覆盖略有差异。
  页面变体：marketId=000016.SH/000300.XSHG/000905.SH/1（后三个未测）。
  页面 meta（2026-11-27）：全部A股破净股数量 615；站点称破净比例"一定程度反映市场交易热度，是市场的先行指标"。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 below-net-asset-statistics-data:000016.SH:belowNetAsset、below-net-asset-statistics-data::belowNetAsset（空参实例；
  ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 选 marketId（已验证：000016.SH 与空值全A池；其他变体须先探测）；
  2. GET 端点带当天 token；
  3. 破净比例 = belowNetAsset/totalCompany；
  4. 比例序列历史分位自算（2005 起长窗口可用）；
  5. 输出附池口径、区间与数据日期。
unit: 家数（只）；比例为 %。
sources:
  - title: 乐咕乐股网：全部A股破净股统计（below-net-asset-statistics）
    url: https://www.legulegu.com/stockdata/below-net-asset-statistics
    date: 2026-11-28
intended_use: 市场底部区域的结构度量：破净比例历史高位提示大面积跌破净资产（情绪悲观/价值区域），供 kn-0003 组合使用。
limitations: |
  candidate 未验证。仅 marketId=000016.SH 与空值两实例实测；000300.XSHG/000905.SH/1 未测。
  空 marketId 的池口径（全A是否含北交所/ST）未声明；两实例覆盖差 11 点，拼接须对齐。
  破净判定用最新财报净资产，财报滞后使破净判定在报告期切换时跳变；
  站点"先行指标"措辞是站点观点，未验证。站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 破净股统计（below-net-asset-statistics-data）

## 口径说明

- 破净 = PB<1；接口给家数（belowNetAsset）与池总数（totalCompany），比例自算。
- 参数表（catalog.json 2026-11-28 实测）：

| marketId | 行数 | 覆盖区间 | 池量级（2005-01-05） |
| --- | --- | --- | --- |
| 000016.SH | 5318 | 2005-01-05→2026-11-27 | totalCompany=49（上证50 量级） |
| （空） | 5307 | 2005-01-05→2026-11-27 | totalCompany=1352（全A量级） |
| 000300.XSHG / 000905.SH / 1 | 未测 | — | 页面变体 |

- 样本：000016.SH 池 2005-01-05 belowNetAsset=1/49；全A池同日 36/1352。页面 meta 2026-11-27 全A破净 615 家。
- 站点观点（引用其口径）：破净比例一定程度反映交易热度，"是市场的先行指标"——未验证。
- ClickHouse 映射：`legulegu.series`，series_id=`below-net-asset-statistics-data:<marketId>:<field>`（空参实例 param 段为空；管道建设中，仅引用约定）。

## 计算步骤

1. 选池（默认空 marketId 全A池；指数池先探测）。
2. 带当天 token 请求端点。
3. 比例 = belowNetAsset/totalCompany，自算历史分位（长窗口 2005 起）。
4. 财报切换期的跳变标注。
5. 输出附池口径与数据日期。

## 解读注意

- 破净比例历史高位（如 2005/2008/2018 底部区域）是悲观出清的结构证据，但"先行"不等于精确择时。
- 破净集中在银行/地产/周期时，比例抬升可能是行业基本面恶化而非全市场便宜——须与行业估值（in-0001）联看。
- 净资产财报滞后：报告期切换时破净家数跳变，不是市场变化。
- 池口径差异（49 只 vs 全A）使比例不可跨池比较。
- 本条目 candidate，引用须标注未验证。
