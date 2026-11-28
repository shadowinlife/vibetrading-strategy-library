---
id: in-0010
type: indicator
title: 股债风险溢价系列（hs300-tcjr-risk-premium，沪深300口径）
status: candidate
markets: [ashare]
asset_classes: [equity, index, bond]
horizon: 日频序列，中长期股债性价比判断
related: [in-0009, in-0011]
formula: |
  riskPremium = 股票风险溢价（ERP，%；推断为盈利收益率 − 无风险利率，具体公式未随接口声明）
  close = 沪深300指数收盘价（对照序列）
data_source: |
  legulegu 端点 /api/stockdata/hs300-tcjr-risk-premium?token=（无参数；a-risk-premium 与 hsi-risk-premium 两页共用）。
  频率：日频（实测 5014 点，2006-03-01→2026-10-16）。
  字段：date/close/riskPremium。样本 2006-03-01：close=1056.62、riskPremium=3.7138；2006-12-19：close=1921.44、riskPremium=1.1366。
  参数事实：a-risk-premium 与 hsi-risk-premium 两页探测到同一端点同一响应（样本逐字节同构），
  恒指变体的区分参数未被捕获——本条目仅覆盖已验证的沪深300序列，恒指风险溢价未验证。
  端点名中 tcjr 含义未随接口声明。另有 /download 端点返回非 JSON（57823 字节），未采用。
  ClickHouse 映射：legulegu.series，无参数端点 param 段为 -（占位，不省略），series_id 如
  hs300-tcjr-risk-premium:-:riskPremium（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/hs300-tcjr-risk-premium?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析日频 date/close/riskPremium 序列；
  3. 历史分位/滚动 z-score 自行计算并注明窗口；
  4. 与指数 close 对照观察溢价与价格的背离；
  5. 输出附覆盖区间与数据日期（注意序列末端滞后）。
unit: riskPremium 为百分点（%）；close 为指数点。
sources:
  - title: 乐咕乐股网：A股风险溢价（a-risk-premium）
    url: https://www.legulegu.com/stockdata/a-risk-premium
    date: 2026-11-28
  - title: 乐咕乐股网：恒指风险溢价页（hsi-risk-premium，探测捕获同一沪深300端点，恒指序列未验证）
    url: https://www.legulegu.com/stockdata/hsi-risk-premium
    date: 2026-11-28
intended_use: A 股（沪深300）相对无风险利率的风险溢价日频度量，供股债性价比与长期回报预期判断使用。
limitations: |
  candidate 未验证。序列末端 2026-10-16，落后其他日频系列（2026-11-27）约 6 周——存在更新滞后，
  用作"当前"读数前必须核对最新日期。ERP 公式未声明（盈利收益率−无风险利率为推断），
  无风险利率取哪个期限未声明；tcjr 含义未声明（是否剔除金融等口径调整未知）。
  恒指风险溢价页存在但其序列参数未捕获，不得把本序列当作恒指 ERP。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 股债风险溢价系列（hs300-tcjr-risk-premium）

## 口径说明

- 无参数端点，a-risk-premium 与 hsi-risk-premium 两页共用；两页样本完全相同（沪深300序列），恒指变体参数未捕获。
- 字段：riskPremium（%，样本点 3.7138/1.1366）、close（沪深300收盘，2006-03-01=1056.62 与指数历史量级一致）。
- 覆盖：5014 点日频，2006-03-01→2026-10-16。**末端滞后约 6 周**（相对其他系列的 2026-11-27）。
- ERP 具体公式（盈利收益率口径、无风险利率期限、tcjr 是否口径调整）未随接口声明，均为待验证项。
- ClickHouse 映射：`legulegu.series`，series_id=`hs300-tcjr-risk-premium:-:riskPremium`（无参数端点 param 段为 -（占位，不省略）；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 解析日频序列，先检查末端日期是否滞后。
3. 自算历史分位或滚动 z-score（窗口注明）。
4. 与 close 对照：指数新高而溢价走低 = 估值扩张驱动，风险补偿变薄。
5. 输出附区间、末端日期与口径待验证声明。

## 解读注意

- 溢价高 = 持股相对债券的补偿厚，长期回报预期好；溢价被压到低位 = 风险补偿薄，回撤脆弱性高。
- 溢价下行可以由利率上行或估值抬升驱动，含义不同，须拆端。
- 与股债利差（in-0009）同族不同口径：本序列是 ERP（推断盈利收益率口径），in-0009 含股息率口径，数值不可互换。
- 更新滞后是本序列的硬伤：引用"当前溢价"必须附实际末端日期。
- 本条目 candidate，引用须标注未验证；不得外推到恒指。
