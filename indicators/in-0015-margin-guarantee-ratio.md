---
id: in-0015
type: indicator
title: 两融担保比例（margin-guarantee-ratio，含站点分位带与信号字段）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日频（推断，dates 数组未采样）
related: [in-0014, in-0003]
formula: |
  维持担保比例 = 担保物价值 / 融资融券债务（通用定义；站点计算口径未声明）
  接口返回 ratio 序列及站点自算的 percentile/upper/lower 分位带与 signals/verdict 信号字段
data_source: |
  legulegu 端点 /api/stockdata/margin-guarantee-ratio?token=（margin-guarantee-ratio 页，React 族）。
  响应为 dict（41428 字节，未采样内部值），顶层键（catalog.json 2026-11-28 实测）：
  ratio/dates/hs300Close（序列与对照）、latestRatio/latestDate、percentile、upper/lower/secondaryLower/secondaryAnchorDate、
  maxRatio/minRatio、change/trend/signals/verdict、maskFromDate/maskedDays、windowYears、vip。
  频率：日频（按两融族口径与 dates 字段推断，未采样验证）。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  margin-guarantee-ratio:ratio（分位带/信号为站点衍生字段，落库须标注衍生口径；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/margin-guarantee-ratio?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析 dates/ratio 序列与 hs300Close 对照；
  3. 站点 percentile/upper/lower 字段可作参考，但窗口（windowYears）与算法未声明，自算分位须注明窗口；
  4. maskFromDate/maskedDays 标记的缺口区间不得插值冒充；
  5. 输出附最新日期、缺口说明与数据日期。
unit: ratio 为 %（担保比例惯例，未随接口声明）；percentile 为 0–100 或 0–1（未采样，须核对）。
sources:
  - title: 乐咕乐股网：两融担保比例（margin-guarantee-ratio）
    url: https://www.legulegu.com/stockdata/margin-guarantee-ratio
    date: 2026-11-28
intended_use: 杠杆账户安全边际的度量：担保比例低位提示杠杆盘脆弱（强平风险），高位提示杠杆余量，供顶部/底部风险辅助判断。
limitations: |
  candidate 未验证。响应内部值未采样，字段语义按键名推断；percentile 量纲（0–1 vs 0–100）未核对。
  已知口径缺口：2015-05~06 官方未披露两融担保比例（ACCESS.md），接口 maskFromDate/maskedDays 字段与缺口 masking 一致——
  该区间无数据，任何插值都是编造。signals/verdict 是站点自算信号，算法未声明，不得当作已验证信号引用。
  担保比例是全市场杠杆账户的汇总口径，个体账户分布不可见；站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 两融担保比例（margin-guarantee-ratio）

## 口径说明

- 维持担保比例 = 担保物价值 / 融资融券债务（通用定义）；站点汇总口径与计算细节未声明。
- 接口是"序列 + 站点衍生分析"的复合 dict：ratio/dates/hs300Close 是数据，percentile/upper/lower/signals/verdict/trend 是站点自算衍生字段。
- **2015-05~06 官方未披露**（ACCESS.md 口径事实）；maskFromDate/maskedDays 键表明接口对缺口做了 masking。
- windowYears 键提示站点分位带使用滚动窗口，长度未采样。
- ClickHouse 映射：`legulegu.series`，series_id=`margin-guarantee-ratio:<field>`（衍生字段须标注；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 解析 dates/ratio，检查 latestDate 与 maskedDays。
3. 缺口区间（含 2015-05~06）保留为缺失，不插值。
4. 分位自算（窗口注明）；站点 percentile 仅作对照并声明其算法未知。
5. 与 hs300Close 对照：指数新高 + 担保比例下行 = 杠杆安全边际变薄。

## 解读注意

- 担保比例低 = 杠杆盘接近强平线，下跌自我强化风险高；但低位也可以持续很久（阴跌钝化）。
- 担保比例高 ≠ 看多信号，只说明杠杆余量充足。
- 站点 signals/verdict 是黑盒衍生字段，引用必须标注"站点自算、未验证"。
- 2015 年缺口恰在杠杆牛顶部区间，任何"全历史分位"在该段失真，须声明。
- 本条目 candidate 且内部值未采样，引用须标注未验证。
