---
id: in-0022
type: indicator
title: 金银比（gold-silver-ratio，国际金银价格比，日频长历史）
status: candidate
markets: [us]
asset_classes: [commodity]
horizon: 日频，长期宏观解读
formula: |
  ratio = gold / silver（金价/银价）
  验证：样本 1968-04-01 gold=37.7、silver=2.259 → 37.7/2.259=16.6888 与 ratio 一致；
  1969-01-20 42.2/1.994=21.1635 一致
data_source: |
  legulegu 端点 /api/stockdata/gold-silver-ratio?token=（gold-silver-ratio 页，React 族）。
  频率：日频（实测 14716 点，1968-04-01→2026-11-27，约 58 年）。
  字段：date/gold/silver/ratio。样本 gold=37.7（1968-04-01）为美元/盎司量级（布雷顿森林体系末期官方价区间），
  推断为国际现货金银价（美元/盎司）；底层价格来源未随接口声明。
  markets 标签说明：指标本体为国际贵金属（美元计价），schema 闭集内取 us 标签，非美股专属指标。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  gold-silver-ratio:ratio（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/gold-silver-ratio?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析日频 gold/silver/ratio；
  3. ratio 已提供，无需自算；缺失行可用 gold/silver 重算并标注；
  4. 长历史分位自算（注明窗口与体制变化：1971 年布雷顿森林解体前后价格机制不同）；
  5. 输出附价格来源待验证声明与数据日期。
unit: ratio 为无量纲比值；gold/silver 推断为美元/盎司。
sources:
  - title: 乐咕乐股网：金银比（gold-silver-ratio）
    url: https://www.legulegu.com/stockdata/gold-silver-ratio
    date: 2026-11-28
intended_use: 宏观避险/工业需求相对强弱的长历史度量：金银比抬升提示避险主导（金强银弱），回落提示工业/通胀交易主导。
limitations: |
  candidate 未验证。底层金银价格来源未声明（美元/盎司为量级推断）；
  1968–1971 为官方价/双轨制时期，与自由浮动时期不可直接比较，全历史分位须分段；
  金银比受白银工业需求（光伏/电子）结构变化影响，历史中枢漂移；
  markets 闭集限制下取 us 标签，实际为全球宏观指标。站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 金银比（gold-silver-ratio）

## 口径说明

- ratio = gold/silver，已用样本两点验证（16.6888=37.7/2.259；21.1635=42.2/1.994）。
- 频率以接口日期序列为准：日频，1968-04-01→2026-11-27（14716 点，约 58 年）。
- 价格量级推断为国际现货美元/盎司；底层来源未声明。
- 1968–1971 官方价时期与浮动汇率时期机制不同，跨体制比较须分段。
- ClickHouse 映射：`legulegu.series`，series_id=`gold-silver-ratio:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 解析 gold/silver/ratio 日频序列。
3. 分位自算，窗口与体制分段注明。
4. 与美元指数/实际利率等宏观变量对照（另源）。
5. 输出附来源待验证声明与数据日期。

## 解读注意

- 金银比高 = 避险情绪浓（金相对银强）；极端高位历史上常对应危机时段，但均值回归时点不可预测。
- 白银工业需求占比上升会趋势性压低金银比中枢，历史阈值需重校准。
- 对 A 股资源板块是间接宏观变量，传导滞后，不构成板块择时信号。
- 58 年序列含多种货币体制，"全历史分位"不注明分段即是误用。
- 本条目 candidate，引用须标注未验证。
