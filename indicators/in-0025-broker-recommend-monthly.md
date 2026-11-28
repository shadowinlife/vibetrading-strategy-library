---
id: in-0025
type: indicator
title: 券商金股组合月度回归（broker-recommend-regression-month，月份索引端点）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 月频
related: [in-0001]
formula: |
  页面口径（meta）：汇总各大券商月度金股组合表现，对比当月收益、超额收益、最佳金股及胜率。
  已验证端点仅返回月份索引列表（80 个 YYYYMM 字符串，202003→202611），
  当月收益/超额收益/胜率等绩效字段未验证（其数据端点未被探测捕获）。
data_source: |
  legulegu 端点 /api/stockdata/broker-recommend-regression-month?token=（broker-recommend-monthly-regression 页）。
  实测响应：80 个字符串的列表，"202611"（首）→"202003"（末），即 2020-03→2026-11 共 80 个月。
  频率：月频（月份索引）。
  statistics 子页（券商金股组合月度汇总）自有数据端点未验证——探测捕获的是共享组件
  （below-net-asset-statistics-data / market-turn-over-ratio-statistics-data），不属于本指标。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  broker-recommend-regression-month:month（绩效字段待补测后扩展；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/broker-recommend-regression-month?token=<MD5(当天 YYYY-MM-DD)>；
  2. 得可用月份清单（YYYYMM）；
  3. 逐月绩效数据须另找端点（未验证），本条目不提供绩效计算步骤的已验证路径；
  4. 如后续补测到绩效端点：按券商×月份聚合当月收益/超额收益/胜率，超额基准须声明；
  5. 输出附"绩效字段未验证"声明。
unit: 月份索引为 YYYYMM 字符串；绩效字段（未验证）预期为 %。
sources:
  - title: 乐咕乐股网：券商十大金股组合（broker-recommend-monthly-regression）
    url: https://www.legulegu.com/stockdata/broker-recommend-monthly-regression
    date: 2026-11-28
  - title: 乐咕乐股网：券商金股组合月度汇总（statistics 子页，自有端点未验证）
    url: https://www.legulegu.com/stockdata/broker-recommend-monthly-regression/statistics
    date: 2026-11-28
intended_use: 卖方月度金股组合表现的追踪入口：月份索引已验证，供后续补测绩效端点后评估卖方推荐胜率与超额收益。
limitations: |
  candidate 未验证。本批仅验证月份索引端点（80 个月，2020-03→2026-11），核心绩效字段（收益/超额/胜率）不可得，
  不得宣称可计算券商金股表现。金股组合是卖方营销产物：发布滞后、选择偏差（只宣传命中组合）、
  等权/加权口径未声明；超额收益基准未声明。statistics 子页数据端点未验证。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 券商金股组合月度回归（月份索引端点）

## 口径说明

- 页面 meta：汇总各大券商月度金股组合表现，对比当月收益、超额收益、最佳金股及胜率。
- 已验证端点只返回月份索引：80 个 YYYYMM（202611→202003，降序），覆盖 2020-03→2026-11。
- 绩效数据端点未被捕获；statistics 子页探测到的是全站共享组件，不是金股数据。
- ClickHouse 映射：`legulegu.series`，series_id=`broker-recommend-regression-month:month`（绩效字段待补测；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求月份索引端点。
2. 解析 YYYYMM 清单，确定可用月份范围。
3. 绩效端点补测前，本条目止步于月份索引；不得用其他数据冒充金股绩效。
4. 补测后：按券商×月份聚合，声明超额基准与组合加权口径。
5. 输出附未验证声明。

## 解读注意

- 卖方金股存在发布滞后与选择偏差，"胜率"统计口径（等权/规模加权/是否含失败组合）决定结论。
- 金股组合表现好 ≠ 可跟单：发布时点与可交易时点不同，冲击成本未计。
- 本条目当前是"入口登记"性质，绩效结论一律不可引用。
- 本条目 candidate，引用须标注未验证。
