---
id: in-0013
type: indicator
title: 恒生系列估值快照（hsi-overview，最新PE/股息率与分页 segments）
status: candidate
markets: [hk]
asset_classes: [equity, index]
horizon: 快照（无历史序列）
related: [in-0012]
formula: |
  快照型指标：恒生指数、恒生科技、恒生医疗保健、恒生创新药等指数的最新市盈率/股息率
  （self-valuation 返回 groups/total；列表端点返回 segments/nextOffset/total；字段内部结构未采样）
data_source: |
  legulegu 端点（hsi-overview 页，React 族）：
  1. /api/stockdata/hsi-overview/self-valuation?token= → dict{groups, total}（5758 字节）；
  2. /api/stockdata/hsi-overview?offset=<n>&token= → dict{segments, nextOffset, total}（8893 字节，分页）。
  页面 meta：恒生指数、恒生科技、恒生医疗保健指数、恒生创新药指数、最新市盈率、股息率。
  频率：快照（接口无日期序列字段记录；更新时点未声明）。
  ClickHouse 映射：legulegu.series 约定上快照类可落为最新值行，series_id 如
  self-valuation:<group>:<field>（slug 取端点 URL 最后路径段；结构未采样，映射为预案；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET self-valuation 端点取 groups/total；
  2. 需要明细时按 offset 分页拉取 segments 直至 nextOffset 耗尽；
  3. 解析各指数最新 PE/股息率（字段名须以实际响应为准，本条目未采样内部结构）；
  4. 与 hs 月频序列（in-0012）交叉核对量级；
  5. 输出附抓取时点（快照无数据日期字段时以抓取时间标注）。
unit: PE 为倍；股息率为 %（按页面 meta 口径）。
sources:
  - title: 乐咕乐股网：恒生指数 overview（hsi-overview，最新市盈率/股息率快照）
    url: https://www.legulegu.com/stockdata/hsi-overview
    date: 2026-11-28
intended_use: 港股核心指数最新估值的快速快照，供盘中/日度检查与 hs 月频序列（in-0012）的当前值对照。
limitations: |
  candidate 未验证。仅确认端点可达与顶层键（groups/total/segments/nextOffset），内部字段结构未采样，
  字段语义按页面 meta 推断；快照无历史序列，不能做分位；更新时点未声明，可能滞后于行情。
  覆盖指数清单以页面 meta 为准（恒生指数/恒生科技/恒生医疗保健/恒生创新药），是否含更多指数未验证。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 恒生系列估值快照（hsi-overview）

## 口径说明

- 快照型条目：与 in-0012（月频历史序列）互补，提供最新 PE/股息率读数。
- 两个端点：self-valuation（groups/total，自估值分组）与列表端点（segments/nextOffset/total，offset 分页）。
- 页面 meta 声明覆盖：恒生指数、恒生科技、恒生医疗保健指数、恒生创新药指数的最新市盈率、股息率。
- 顶层键来自 catalog.json 2026-11-28 实测；内部结构未采样，一切字段级语义待验证。
- ClickHouse 映射为预案（快照落最新值行），管道建设中，仅引用约定。

## 计算步骤

1. 带当天 token 请求 self-valuation，记录 groups/total。
2. 明细需求按 offset 分页遍历 segments。
3. 以实际响应确定字段名后提取 PE/股息率；与 in-0012 序列末端交叉核对。
4. 输出附抓取时点与"快照非历史"声明。

## 解读注意

- 快照只能回答"现在贵不贵"的当前读数，不能回答"历史什么位置"——分位必须用 in-0012 序列。
- 恒生科技/创新药等成长指数 PE 对盈利波动极敏感，单点读数噪声大。
- 快照与月频序列末端可能不一致（更新时点不同），冲突时以带日期的序列为准。
- 本条目 candidate 且字段结构未采样，引用须标注未验证。
