---
id: in-0026
type: indicator
title: 中观景气度指标（middle-indicators，申万二/三级净利润同比增长率中位数）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 季度（盈利数据，未采样核实）
related: [in-0001]
formula: |
  行业景气度 = 申万行业分类内成分股"归属母公司股东的净利润同比增长率(%)"的中位数（页面 meta 口径）
  参数化：indexCodes 选择申万二级/三级行业
data_source: |
  legulegu 端点 /api/stockdata/middle-indicators?indexCodes=<申万行业代码>&token=
  （middle-avg-indicator/sec-level 与 middle-avg-indicator/third-level 两页共用）。
  响应 dict（330966 字节，未采样内部值），顶层键（catalog.json 2026-11-28 实测）：
  indexCodeOfXAis/middleIndicatorItemMap。
  页面 meta：景气度指标_净利润增长率(申万二级/三级)与申万行业分类归属母公司股东的净利润同比增长率(%)中位数对比分析，
  展示各行业该指标的数值分布与历史变化趋势。
  频率：未采样（盈利指标按财报季推断季频，须以实际响应核实）。
  indexCodes 具体取值未测（探测 URL 参数为空）。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 middle-indicators:<申万行业代码>:netProfitYoYMedian（字段名待采样定；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 选申万二级/三级行业代码（indexCodes 取值须先探测确认）；
  2. GET /api/stockdata/middle-indicators?indexCodes=<codes>&token=<MD5(当天 YYYY-MM-DD)>；
  3. 采样 middleIndicatorItemMap 确定行业×期×中位数字段结构；
  4. 中位数同比序列的拐头/分位自行计算（窗口注明）；
  5. 输出附行业分类版本、频率待验证与数据日期。
unit: "%（净利润同比增长率中位数）"
sources:
  - title: 乐咕乐股网：景气度指标_净利润增长率(申万二级)（middle-avg-indicator/sec-level）
    url: https://www.legulegu.com/stockdata/middle-avg-indicator/sec-level
    date: 2026-11-28
  - title: 乐咕乐股网：景气度指标_净利润增长率(申万三级)（middle-avg-indicator/third-level）
    url: https://www.legulegu.com/stockdata/middle-avg-indicator/third-level
    date: 2026-11-28
intended_use: 行业中观盈利景气的位置与拐头度量，中位数口径规避行业内大权重股扭曲，供行业比较与盈利周期判断。
limitations: |
  candidate 未验证。响应内部值未采样，字段结构待确认；indexCodes 取值未测；频率未核实（季频推断）。
  净利润同比受基数效应主导（去年亏损/微利使同比爆炸），中位数缓解但不消除；
  财报发布滞后 1–4 个月，景气拐头确认晚于股价；申万分类版本修订使历史不可比。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 中观景气度指标（申万二/三级净利润增长中位数）

## 口径说明

- 页面 meta 口径：行业内成分股归母净利润同比增长率(%)的**中位数**，二级/三级两个粒度共用端点，indexCodes 参数化。
- 顶层键：indexCodeOfXAis/middleIndicatorItemMap（catalog.json 实测）；内部结构未采样。
- 中位数 vs 整体法：中位数刻画"典型公司"的盈利景气，规避行业内权重股扭曲（与 in-0001 整体法估值互补）。
- ClickHouse 映射：`legulegu.series`，series_id=`middle-indicators:<行业代码>:<field>`（字段待采样定名；管道建设中，仅引用约定）。

## 计算步骤

1. 探测确定 indexCodes 取值（申万行业代码格式）。
2. 带当天 token 请求端点。
3. 采样 middleIndicatorItemMap，确定行业×报告期×中位数结构。
4. 自算拐头与分位（窗口注明）；基数效应异常期标注。
5. 输出附分类版本与频率待验证声明。

## 解读注意

- 盈利景气拐头向上 + 估值低分位（in-0001）= 戴维斯双击候选；景气下行 + 估值高分位 = 双杀风险。
- 同比中位数在基数异常期（疫情/亏损年）失真，须结合绝对利润水平。
- 季频滞后：财报季集中发布使序列阶梯状跳变，不是连续信号。
- 三级行业样本少（成分股 ≤5 时中位数噪声大，参照 in-0001 小样本警示）。
- 本条目 candidate 且内部值未采样，引用须标注未验证。
