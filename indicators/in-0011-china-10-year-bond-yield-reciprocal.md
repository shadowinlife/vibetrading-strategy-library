---
id: in-0011
type: indicator
title: 十年期国债收益率倒数与A股PE中位数（china-10-year-bond-yield-data，股债性价比）
status: candidate
markets: [ashare]
asset_classes: [equity, bond, index]
horizon: 月频序列，中长期股债轮动参考
related: [in-0009, in-0010, kn-0003]
formula: |
  reciprocalRate = 100 / debtInterestRate（10年期国债收益率的倒数，视为"合理市盈率"参考线）
  marketPe = A股市盈率中位数（全A口径，推断）
  hs300PeMiddle = 沪深300市盈率中位数（早期行为 0.0 = 缺失）
  验证：100/4.9=20.408163 与样本 reciprocalRate 一致；100/2.873=34.806822 一致
data_source: |
  legulegu 端点 /stockdata/china-10-year-bond-yield-data?token=（china-10-year-bond-yield 页，jQuery 族）。
  频率：月频（实测 263 点，2005-01-31→2026-11-27，月末采样）。
  字段：debtInterestRate（10年期国债收益率，%）/reciprocalRate/marketPe/hs300PeMiddle。
  样本 2005-01-31：debtInterestRate=4.9、reciprocalRate=20.4082、marketPe=27.36、hs300PeMiddle=0.0（缺失）；
  2021-08-30：debtInterestRate=2.873、reciprocalRate=34.8068、marketPe=33.6、hs300PeMiddle=25.52。
  页面 meta（2026-11-27）：A股市盈率中位数 31.77，10年国债收益率 1.597。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  china-10-year-bond-yield-data:debtInterestRate（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /stockdata/china-10-year-bond-yield-data?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析月频序列；hs300PeMiddle=0.0 的行按缺失处理，不得当作真实零值；
  3. 比较 marketPe 与 reciprocalRate：低于参考线 = 股市相对低估（站点口径）；
  4. 差值/比值序列自行构建，历史分位注明窗口；
  5. 输出附区间、缺失处理与数据日期。
unit: debtInterestRate 为 %；reciprocalRate/marketPe/hs300PeMiddle 为倍（PE 量纲）。
sources:
  - title: 乐咕乐股网：十年期国债利率倒数与A股PE中位数走势（china-10-year-bond-yield）
    url: https://www.legulegu.com/stockdata/china-10-year-bond-yield
    date: 2026-11-28
intended_use: 经典股债轮动参考：以国债收益率倒数为"合理PE"锚，判断 A 股整体相对利率水平的高估/低估。
limitations: |
  candidate 未验证。月频（非日频），短期择时滞后；hs300PeMiddle 早期行恒 0.0（缺失），
  2005 年起始段不可用；marketPe 的全A口径与中位数计算规则未随接口声明（页面文案称 PE 中位数）。
  "利率倒数=合理PE"隐含盈利收益率与国债收益率直接可比的假设，忽略股权风险溢价与盈利增长，
  低利率环境下参考线被动抬升，会把"利率低"误读为"股票便宜"。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 十年期国债收益率倒数与A股PE中位数

## 口径说明

- 站点口径（页面说明文字）：利率倒数可视为市场"合理市盈率"参考线；A股PE中位数低于利率倒数时股市相对低估，反之高估；自称"经典的股债轮动量化分析工具"。
- 字段关系已用样本验证：reciprocalRate = 100/debtInterestRate（4.9→20.4082；2.873→34.8068）。
- marketPe 为 A 股 PE 中位数（页面 meta 2026-11-27 读数 31.77）；hs300PeMiddle 为沪深300 PE 中位数，早期行 0.0 是缺失不是零。
- 频率以接口日期序列为准：**月频**（263 点，2005-01-31→2026-11-27）。
- ClickHouse 映射：`legulegu.series`，series_id=`china-10-year-bond-yield-data:<field>`（无参数端点省略 param 段；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点，解析月频序列。
2. hs300PeMiddle=0.0 按缺失剔除。
3. 计算 marketPe − reciprocalRate（或比值）序列。
4. 自算历史分位，注明窗口。
5. 输出附区间、缺失说明与数据日期。

## 解读注意

- 参考线随利率下行被动抬升：2005 年 20.4 倍 → 2021 年 34.8 倍，同一 PE 在不同利率环境下结论相反——这是机制不是信号。
- 忽略股权风险溢价：盈利收益率与国债收益率直接可比只在"股票=永续债"假设下成立，成长性与风险补偿被抹掉。
- 月频滞后；与日频股债利差（in-0009）/ERP（in-0010）组合时注意频率对齐。
- 站点"低估/高估"措辞是相对参考线的描述，不构成买卖建议；本条目 candidate，引用须标注未验证。
