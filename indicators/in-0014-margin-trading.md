---
id: in-0014
type: indicator
title: 两融余额与资金变动（margin-trading-data，分交易所，日频）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日频
related: [in-0003, in-0015]
formula: |
  rzye = 融资余额；rzmre = 融资买入额；rzche = 融资偿还额
  rqye = 融券余额；rqmcl = 融券卖出量；rzrqye = 融资融券余额
  单位已交叉验证：金额字段为亿元，rqmcl 为万股（见口径说明）
  净融资买入 = rzmre − rzche（自算）
data_source: |
  legulegu 端点 /stockdata/margin-trading-data?token=（margin-trading 页，jQuery 族；ACCESS.md 记两融属部分免 token 端点）。
  频率：日频；匿名窗口实测 598 行 = 2 交易所 × 299 交易日，2025-09-01→2026-11-26（约 15 个月，全历史深度未验证）。
  字段：date/exchangeId/rzye/rzmre/rzche/rqye/rqmcl/rzrqye；样本按日期降序（最新在前）。
  exchangeId ∈ {0,1} 分交易所；与沪/深的对应关系未随样本声明，使用前须核对。
  单位交叉验证（rzrqye 页 meta 2026-11-26 vs 样本同日两所合计）：
  rzrqye 11197.32+10079.23=21276.55 亿 = 页面公布"融资融券余额 21276.55 亿"；
  rzmre 537.81+459.68=997.49 亿 = 页面"融资买入额 997.49 亿"；
  rqmcl 8388.68+5326.11=13714.79 万股 = 页面"融券卖出量 13714.79(万股)"。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 margin-trading-data:0:rzye、margin-trading-data:1:rzrqye（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /stockdata/margin-trading-data?token=<MD5(当天 YYYY-MM-DD)>；
  2. 按 exchangeId 分组、按 date 升序重排（原始降序）；
  3. 两市合计 = 同日期两所相加（合计口径与 rzrqye 页一致，已验证）；
  4. 净融资买入 = rzmre − rzche；融资余额增速/新高状态自行计算；
  5. 输出附交易所映射核对结果、窗口起点与数据日期。
unit: rzye/rzmre/rzche/rqye/rzrqye 为亿元；rqmcl 为万股。
sources:
  - title: 乐咕乐股网：融资融券资金变动（margin-trading）
    url: https://www.legulegu.com/stockdata/margin-trading
    date: 2026-11-28
  - title: 乐咕乐股网：融资融券余额(沪深)（rzrqye，页面 meta 用于单位交叉验证；其自有端点 rzrqye-data 404 未验证）
    url: https://www.legulegu.com/stockdata/rzrqye
    date: 2026-11-28
intended_use: A 股杠杆资金规模与动能的日频度量，供 in-0003 两融背离子信号与杠杆情绪判断使用。
limitations: |
  candidate 未验证。匿名窗口仅约 15 个月（2025-09-01 起），2010 年以来的完整历史不可得（全历史深度未验证，
  非会员时间窗限制疑似存在）；exchangeId 与沪/深映射未声明；rzrqye 页自有端点 404，合计口径靠页面 meta 交叉验证。
  融券字段（rqye/rqmcl）在 2024 年融券政策收紧后量级极小，历史比较须注意政策断点。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 两融余额与资金变动（margin-trading-data）

## 口径说明

- 分交易所日频序列：exchangeId ∈ {0,1}（沪/深映射未声明，须核对）；样本降序排列。
- 单位已用 rzrqye 页面 meta 交叉验证（2026-11-26）：金额亿元、融券卖出量万股，两所合计与页面公布值逐项一致。
- 样本最新行（2026-11-26）：exchangeId=0 rzye=11010.7、rzrqye=11197.32；exchangeId=1 rzye=9975.22、rzrqye=10079.23。
- 匿名窗口：2025-09-01→2026-11-26（598 行）；更早历史未验证。
- ClickHouse 映射：`legulegu.series`，series_id=`margin-trading-data:<exchangeId>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点（ACCESS.md 记两融属部分免 token 族，token 仍按配方携带）。
2. 按 exchangeId 分组，date 升序重排。
3. 核对交易所映射（与交易所官方公布值对照）后再标注沪/深。
4. 两市合计、净融资买入（rzmre−rzche）、余额滚动新高/增速自行计算。
5. 输出附窗口起点、映射核对与数据日期。

## 解读注意

- 融资余额创新高而指数不创新高 = 杠杆动能背离（in-0003 子信号），顶部风险辅助证据。
- 余额是存量，买入额是流量：存量高位+流量萎缩 = 杠杆盘钝化，信号含义减弱。
- 融券端政策断点（2024 收紧）使 rqye/rqmcl 历史不可比。
- 匿名窗口短，长期分位不可算；需要长历史时走交易所官方/Tushare 口径并声明来源切换。
- 本条目 candidate，引用须标注未验证。
