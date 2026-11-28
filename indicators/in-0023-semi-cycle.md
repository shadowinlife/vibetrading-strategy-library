---
id: in-0023
type: indicator
title: 半导体周期（semi-cycle，出货量3月均线与SMH相关同比）
status: candidate
markets: [us]
asset_classes: [equity, index]
horizon: 月度/周期级（dates 数组未采样）
formula: |
  shipment3MA = 半导体出货量（销售额）3 个月移动平均（按字段名推断，全球口径，来源未声明）
  smhXlpYoY = SMH（VanEck 半导体 ETF，美股上市）相关同比字段（Xlp 含义未声明，按字段名推断为同比序列）
data_source: |
  legulegu 端点 /api/stockdata/semi-cycle?token=（semi-cycle 页，React 族）。
  响应 dict（15435 字节，未采样内部值），顶层键（catalog.json 2026-11-28 实测）：
  dates/latestDate/shipment3MA/smhXlpYoY/user/vip。
  频率：未采样（出货量为月度统计，推断月频；须以 dates 数组核实）。
  markets 标签说明：shipment 为全球半导体统计、SMH 为美股 ETF，闭集内取 us；对 A 股半导体板块为间接周期参照。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  semi-cycle:shipment3MA（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/semi-cycle?token=<MD5(当天 YYYY-MM-DD)>；
  2. 采样 dates/shipment3MA/smhXlpYoY 确定频率与字段语义；
  3. 周期定位：3MA 同比拐头方向（自算同比）；
  4. 与 SMH 价格序列（另源）对照验证量级；
  5. 输出附字段语义待验证声明与数据日期。
unit: shipment3MA 单位未声明（推断为销售额，百万/十亿美元级）；smhXlpYoY 推断为 %。
sources:
  - title: 乐咕乐股网：半导体周期（semi-cycle）
    url: https://www.legulegu.com/stockdata/semi-cycle
    date: 2026-11-28
intended_use: 全球半导体景气周期的位置度量，供半导体板块（含 A 股）盈利周期判断的宏观参照。
limitations: |
  candidate 未验证。响应内部值未采样，字段语义全部按字段名推断；出货量来源（SIA/WSTS 等）未声明，
  不得虚构原始来源；smhXlpYoY 的 Xlp 含义未知；频率未核实。
  半导体周期是滞后确认指标（出货统计发布滞后），拐点识别晚于价格；
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 半导体周期（semi-cycle）

## 口径说明

- 复合 dict：dates + shipment3MA（出货量 3 月均线，推断）+ smhXlpYoY（SMH 相关同比，推断）+ latestDate。
- 顶层键来自 catalog.json 实测；内部值未采样，一切字段级语义待验证。
- 出货量统计通常为月度（SIA 全球半导体销售口径常见），本接口来源未声明。
- ClickHouse 映射：`legulegu.series`，series_id=`semi-cycle:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 先采样确定 dates 频率与字段量纲。
3. 自算 shipment3MA 同比，定位周期方向（上行/下行/拐头）。
4. 与 SMH 价格（另源）交叉核对。
5. 输出附语义待验证声明。

## 解读注意

- 半导体是典型 3–4 年库存周期，3MA 平滑后拐点确认仍滞后于股价 1–2 个季度。
- 出货量同比拐头向上 + 价格已大涨 = 周期兑现段，追高风险；同比下行 + 价格深跌 = 左侧区域。
- 对 A 股半导体是间接参照，国产替代逻辑与全球周期不完全同步。
- 字段语义未验证前，任何数值引用都必须标注推断口径。
- 本条目 candidate，引用须标注未验证。
