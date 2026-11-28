---
id: in-0009
type: indicator
title: 股债利差系列（equity-bond-spread，code 参数化，仅沪深300实测有数据）
status: candidate
markets: [ashare]
asset_classes: [equity, index, bond]
horizon: 日频序列，中长期股债性价比判断
related: [in-0010, in-0011, kn-0003]
formula: |
  peSpread = 盈利收益率利差（推断为 1/PE − 10年期国债收益率，小数表示；样本 2005-04-08 = 0.022656）
  dvSpread = 静态股息率利差（%，公式未随接口声明；样本 2005-04-08 = 2.26）
  dvTtmSpread = TTM 股息率利差（%，公式未声明；样本 2005-04-08 = 2.1）
  *Average / *StandardDeviation = 对应利差的均值/标准差（窗口未声明；首点均值等于首点值，疑似自序列起点扩张）
data_source: |
  legulegu 端点 /api/stockdata/equity-bond-spread?code=<指数代码>&token=（equity-bond-spread 页，React 族）。
  频率：日频（实测 code=000300.SH 5253 点，2005-04-08→2026-11-27）。
  字段：peSpread/dvSpread/dvTtmSpread 及各自 Average/StandardDeviation、close/code。
  参数事实：code=000300.SH 返回完整序列；code=000016.SH/000905.SH/000300.LG 返回 71 字节空结构
  （仅 sw/swLevel1/swLevel2/user/vip 键）——匿名访问下无数据，原因（权限/参数口径）未验证。
  另有 /download 端点返回非 JSON（57823 字节，疑似 CSV），未采用。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 equity-bond-spread:000300.SH:dvTtmSpread（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 取 code=000300.SH（唯一实测有数据实例；其他代码须先探测）；
  2. GET /api/stockdata/equity-bond-spread?code=000300.SH&token=<MD5(当天 YYYY-MM-DD)>；
  3. 单位归一：peSpread 为小数（×100 转 %），dvSpread/dvTtmSpread 已是 %，比较前必须统一；
  4. 利差位置 = 当前值相对均值/标准差字段（或自算滚动 z-score，窗口注明）；
  5. 输出附代码、字段口径、区间与数据日期。
unit: peSpread 为小数比率；dvSpread/dvTtmSpread 为百分点（%）；均值/标准差随对应字段单位。
sources:
  - title: 乐咕乐股网：股债利差（equity-bond-spread，沪深300股息率/盈利收益率 vs 国债收益率）
    url: https://www.legulegu.com/stockdata/equity-bond-spread
    date: 2026-11-28
intended_use: 股债相对性价比的日频度量，利差极端高位提示股票相对债券便宜（或债券收益率过低），供大类资产配置与 kn-0003 组合使用。
limitations: |
  candidate 未验证。仅 code=000300.SH 实测有数据；000016.SH/000905.SH/000300.LG 匿名返回空结构，
  不得宣称"4 标的可用"。利差公式未随接口声明（peSpread 的 1/PE−收益率 为字段名推断），
  均值/标准差窗口未声明；peSpread 与 dvSpread 单位不一致（小数 vs %），混用会差 100 倍。
  股息率利差受分红季节性与成分调整影响；低利率环境下利差中枢上移，历史阈值需重校准。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 股债利差系列（equity-bond-spread）

## 口径说明

- 端点族按 code 参数化，页面提供多个指数标的，但 2026-11-28 实测仅 **000300.SH（沪深300）** 返回数据（5253 点日频，2005-04-08→2026-11-27）；000016.SH/000905.SH/000300.LG 返回空结构（71 字节）。
- 三个利差字段：peSpread（盈利收益率利差，小数）、dvSpread（静态股息率利差，%）、dvTtmSpread（TTM 股息率利差，%）。公式未随接口声明，peSpread 按字段名与量级推断为 1/PE − 10年期国债收益率。
- 每个利差附 Average/StandardDeviation 字段：首点均值等于首点值（2005-04-08 dvSpreadAverage=2.26=dvSpread），疑似自起点扩张统计，窗口定义未声明。
- 样本示例：2005-04-08 peSpread=0.022656、dvSpread=2.26、dvTtmSpread=2.1；2005-09-02 peSpread=0.041161、dvSpread=1.27、dvSpreadAverage=1.540297。
- ClickHouse 映射：`legulegu.series`，series_id=`equity-bond-spread:<code>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 固定 code=000300.SH；其他标的先探测再引用。
2. 带当天 token 请求端点，解析日频序列。
3. 统一单位（peSpread×100 → %）后再做任何跨字段比较。
4. 用接口均值/标准差字段或自算滚动 z-score 定位当前利差（窗口注明）。
5. 输出附字段口径、区间、数据日期；空结构标的明说无数据。

## 解读注意

- 利差高位 = 股票相对债券便宜（或债券收益率被压得过低），两种成因的政策含义相反，须拆端看。
- 利差是中长期配置锚，短期预测力弱；极端读数可以持续很久（低利率体制）。
- 股息率利差受分红实施季节影响，TTM 口径（dvTtmSpread）比静态口径平滑。
- 与风险溢价（in-0010）、国债收益率倒数（in-0011）同族但口径不同，数值不可互换。
- 单位混用（小数 vs %）是本族最容易犯的错；本条目 candidate，引用须标注未验证。
