---
id: in-0024
type: indicator
title: 市值存款比（market-cap-deposit-ratio，A股总市值/存款余额，含站点回归通道）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日频/低频混合（points 未采样）
related: [in-0002]
formula: |
  市值存款比 = A股总市值 / 存款余额（通用定义；站点分子分母口径未声明）
  接口附站点自算回归通道（regStart/r2/sigma/sigmaK/mid/upper/lower/topBands/bottomBands）与 latestPctRank 分位
data_source: |
  legulegu 端点 /api/stockdata/market-cap-deposit-ratio?token=（market-cap-deposit-ratio 页，React 族）。
  响应 dict（588311 字节，未采样内部值），顶层键（catalog.json 2026-11-28 实测）：
  points/hs300（序列与对照）、latestMv/latestDeposit/latestRatio/latestPctRank/updatedDate、
  regStart/r2/sigma/sigmaK/mid/upper/lower/topBands/bottomBands/maskStartDate、user/vip。
  频率：未采样（市值日频、存款月频，比值频率须以 points 核实）。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  market-cap-deposit-ratio:ratio（回归通道为站点衍生字段，落库须标注；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/market-cap-deposit-ratio?token=<MD5(当天 YYYY-MM-DD)>；
  2. 采样 points 确定频率与分子分母字段；
  3. latestRatio/latestPctRank 作当前读数参考（分位窗口未声明）；
  4. 回归通道（mid±sigma×sigmaK）为站点统计口径，r2 提示拟合质量，引用须标注未验证；
  5. 输出附口径待验证声明与 updatedDate。
unit: ratio 为无量纲比值（或 %，未采样）；latestMv/latestDeposit 单位未声明。
sources:
  - title: 乐咕乐股网：市值存款比（market-cap-deposit-ratio）
    url: https://www.legulegu.com/stockdata/market-cap-deposit-ratio
    date: 2026-11-28
intended_use: 居民资金配置结构的度量：市值/存款比高位提示权益配置相对存款偏重（潜在增量资金空间收窄），供长期资金面判断。
limitations: |
  candidate 未验证。响应内部值未采样，分子（总市值/流通市值）与分母（住户存款/全部存款）口径未声明；
  频率未核实；回归通道与分位是站点黑盒衍生字段（算法/窗口未声明），不得当作已验证信号。
  存款数据月频发布滞后，比值在存款发布日跳变；maskStartDate 提示存在 masking 区间。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 市值存款比（market-cap-deposit-ratio）

## 口径说明

- 通用定义：A股总市值 / 存款余额，衡量权益资产相对银行储蓄的规模位置（"存款搬家"叙事的可量化锚）。
- 接口是"序列 + 站点回归分析"复合 dict：points/hs300 为数据，regStart/r2/sigma/sigmaK/mid/upper/lower/topBands/bottomBands 为站点回归通道，latestPctRank 为站点分位。
- 顶层键来自 catalog.json 实测；内部值未采样。
- ClickHouse 映射：`legulegu.series`，series_id=`market-cap-deposit-ratio:<field>`（衍生字段标注；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 采样 points 确定频率与口径。
3. 当前读数取 latestRatio，附 updatedDate。
4. 通道位置（相对 mid/upper/lower）作参考，标注站点算法未验证。
5. 自算分位须注明窗口；存款发布跳变标注。

## 解读注意

- 比值高位 = 权益相对存款已重配，后续增量资金依赖收入增长而非搬家；低位 = 搬家空间大，但搬家需要催化。
- 与巴菲特指标（in-0002）互补：一个对 GDP（产出），一个对存款（资金池），分母不同结论不可互换。
- 存款口径（住户/企业/全部）差异巨大，未声明前不做跨源比较。
- 回归通道是统计描述不是因果，r2 低时通道无意义。
- 本条目 candidate 且内部值未采样，引用须标注未验证。
