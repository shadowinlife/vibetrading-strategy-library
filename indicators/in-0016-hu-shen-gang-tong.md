---
id: in-0016
type: indicator
title: 沪深港通资金流向（hu-shen-gang-tong-data，北向成交额/南向净流入）
status: candidate
markets: [ashare, hk]
asset_classes: [equity]
horizon: 日频
related: [in-0014]
formula: |
  北向（沪股通+深股通）：2024-08-19 起为成交额口径，此前为历史净流入口径（两段不可直接拼接）
  南向（港股通沪+深）：净流入口径
  接口返回 items（资金序列）与 indexDailies（指数对照），内部字段未采样
data_source: |
  legulegu 端点 /stockdata/hu-shen-gang-tong-data?token=（hu-shen-gang-tong 页，jQuery 族；亦作为共享组件出现在
  china-10-year-bond-yield/market-activity/market-activity-trend 等页）。
  响应 dict（206874 字节，未采样内部值），顶层键：indexDailies/items/user/vip。
  页面 meta（2026-11-27）：北向成交额 2925.29 亿，南向净流入 552.11 亿；
  明示"北向2024年8月19日起为成交额，此前为历史净流入；南向展示净流入"。
  频率：日频（页面 meta 与 items 结构推断，未采样验证）。
  子页面 hu-gu-tong（沪股通）/shen-gu-tong（深股通）/gang-gu-tong-hu/shen（港股通分通道）未单独验证。
  ClickHouse 映射：legulegu.series，无参数端点 param 段为 -（占位，不省略），series_id 如
  hu-shen-gang-tong-data:<channel>:<field>（channel/field 待采样后定；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /stockdata/hu-shen-gang-tong-data?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析 items 与 indexDailies，先采样确定字段名与通道划分；
  3. 北向序列按 2024-08-19 切段：前段净流入、后段成交额，分别标注，禁止拼接成单一"净流入"序列；
  4. 南向净流入可直接累计；
  5. 输出附口径切段说明与数据日期。
unit: 亿元（页面 meta 口径）。
sources:
  - title: 乐咕乐股网：沪深港通净流入与成交额（hu-shen-gang-tong）
    url: https://www.legulegu.com/stockdata/hu-shen-gang-tong
    date: 2026-11-28
intended_use: 跨境资金动能度量：南向净流入观察内地资金配港意愿，北向成交额观察外资参与度（2024-08-19 后不再可得净流入）。
limitations: |
  candidate 未验证。核心口径断点：北向 2024-08-19 起从净流入改为成交额（官方披露规则变化），
  前后段量纲不同（净额 vs 总额），直接拼接或跨段比较都是误用。
  响应内部字段未采样；分通道子页面未验证；日频推断未采样确认。
  2024-08-19 后"北向净流入"在任何来源都不可得，不得用成交额冒充净流入。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 沪深港通资金流向（hu-shen-gang-tong-data）

## 口径说明

- 页面 meta（2026-11-27）实测读数：北向成交额 2925.29 亿、南向净流入 552.11 亿。
- **口径断点（必须写明）**：北向 2024-08-19 起为成交额，此前为历史净流入；南向始终为净流入。
- 接口顶层键：indexDailies/items/user/vip（catalog.json 实测）；内部字段未采样。
- 该端点同时是多个 jQuery 页的共享组件，页面归属以 hu-shen-gang-tong 为主。
- ClickHouse 映射：`legulegu.series`，series_id=`hu-shen-gang-tong-data:<channel>:<field>`（待采样定名；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 采样 items 确定字段与通道（沪股通/深股通/港股通沪/港股通深）。
3. 北向按 2024-08-19 切段存储，段标签随数据落库。
4. 南向净流入做滚动累计；北向成交额只做活跃度观察。
5. 输出附切段说明与数据日期。

## 解读注意

- 北向成交额上升 ≠ 外资看多（成交是双边总额，无方向）；2024-08-19 后任何"北向净买入"读数都要追问来源。
- 南向净流入对港股是增量资金信号，但受汇率与额度政策影响。
- 口径断点使北向长期序列不可比，历史回测跨越 2024-08-19 必须分段处理。
- 与两融（in-0014）组合观察内外杠杆资金共振。
- 本条目 candidate 且内部字段未采样，引用须标注未验证。
