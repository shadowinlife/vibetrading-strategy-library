---
id: in-0012
type: indicator
title: 恒生系列指数市盈率与股息率（hs，indexCode 参数化，月频）
status: candidate
markets: [hk]
asset_classes: [equity, index]
horizon: 月频序列，长期估值与股息收入解读
related: [in-0013, kn-0003]
formula: |
  pe = 指数市盈率（整体法口径未声明）
  dvRatio = 指数股息率（%）
  close = 指数收盘价（部分指数早期行缺失）
data_source: |
  legulegu 端点 /api/stockdata/hs?indexCode=<恒生系列代码>&token=（market/hscei、market/hsci、market/hsf、market/hsp、market/hsu 页共用）。
  频率：月频（月末采样；实测 HSCEI 301 点 2001-10-31→2026-10-30，HSCI/HSF/HSP/HSU 各 490 点 1986-01-31→2026-10-30）。
  字段：pe/dvRatio/close（close 仅部分指数/后期行提供）。
  样本事实：五个页面的样本文件均为 indexCode=HSU 的响应（探测覆盖写），HSCEI/HSCI/HSF/HSP 的行数与区间来自 catalog 实测记录。
  HSU 样本：1986-01-31 pe=16.92、dvRatio=0.0（早期缺失）；2002-08-31 pe=12.8、dvRatio=5.05、close=22408.98。
  HSI（恒生指数本体）参数未测：market/hsi 页自有端点 hsi-data 返回 404；页面 meta 给出 HSI PE=13.04、
  股息率=3.14（2026-10-30），自述序列起始 1973-05——页面文案事实，接口未验证。
  ClickHouse 映射：legulegu.series，series_id 约定 <endpoint_slug>:<param>:<field>，
  如 hs:HSU:pe、hs:HSCEI:dvRatio（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 选 indexCode（HSCEI/HSCI/HSF/HSP/HSU 已实测；HSI 须先探测）；
  2. GET /api/stockdata/hs?indexCode=<code>&token=<MD5(当天 YYYY-MM-DD)>；
  3. dvRatio=0.0 的早期行按缺失处理；close 缺失不影响 pe/dvRatio 使用；
  4. 历史分位自行重算并注明窗口（序列最长自 1986 年）；
  5. 输出附代码、区间、缺失处理与数据日期。
unit: pe 为倍；dvRatio 为 %；close 为指数点。
sources:
  - title: 乐咕乐股网：恒生中国企业指数市盈率/股息率（market/hscei，hs 端点族）
    url: https://www.legulegu.com/stockdata/market/hscei
    date: 2026-11-28
  - title: 乐咕乐股网：恒生指数市盈率页（market/hsi，页面 meta：PE=13.04@2026-10-30，接口未验证）
    url: https://www.legulegu.com/stockdata/market/hsi
    date: 2026-11-28
intended_use: 港股恒生系列指数的月频估值与股息率度量，长历史（1986 起）供港股长期估值分位与股息配置判断。
limitations: |
  candidate 未验证。HSI 本体接口未验证（hsi-data 404，hs?indexCode=HSI 未测），13.04/3.14 仅为页面 meta 文案。
  五个页面样本同为 HSU 响应，其他指数的数值未采样；dvRatio 早期 0.0 为缺失；
  序列末端 2026-10-30（10 月末），11 月点未出——月频发布滞后。
  PE 整体法/剔除规则未声明；恒生系列分类（金融/地产/公用等）行业集中，估值不可与宽基直接比较。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 恒生系列指数市盈率与股息率（hs）

## 口径说明

- 参数化族：`/api/stockdata/hs?indexCode=<code>`，一个端点覆盖恒生系列五个已实测指数。
- 参数表（catalog.json 2026-11-28 实测；指数名称按站点股息率页标题）：

| indexCode | 站点页面名称 | 行数 | 覆盖区间 |
| --- | --- | --- | --- |
| HSCEI | 恒生中国企业指数 | 301 | 2001-10-31→2026-10-30 |
| HSCI | 恒生工商指数（站点标题；通常 HSCI 指恒生综合指数，口径待核） | 490 | 1986-01-31→2026-10-30 |
| HSF | 恒生金融指数 | 490 | 1986-01-31→2026-10-30 |
| HSP | 恒生地产指数 | 490 | 1986-01-31→2026-10-30 |
| HSU | 恒生公共指数 | 490 | 1986-01-31→2026-10-30 |
| HSI | 恒生指数（本体） | 未测 | 页面自述 1973-05 起；meta PE=13.04、股息率=3.14（2026-10-30） |

- 字段：pe/dvRatio/close；dvRatio 早期 0.0 为缺失（HSU 1986-01-31），close 后期才出现（HSU 2002-08-31=22408.98）。
- 频率以接口日期序列为准：月频，末端 2026-10-30。
- ClickHouse 映射：`legulegu.series`，series_id=`hs:<indexCode>:<field>`（管道建设中，仅引用约定）。

## 计算步骤

1. 选 indexCode；HSI 须先探测 hs?indexCode=HSI，未确认前只引用页面 meta 并标注。
2. 带当天 token 请求端点，解析月末序列。
3. dvRatio=0.0 早期行按缺失剔除。
4. 自算历史分位（窗口注明；长序列注意 1997/2008 等体制变化）。
5. 输出附代码、区间、缺失处理与数据日期。

## 解读注意

- 行业分类指数（金融/地产/公用）估值由行业周期主导，与宽基估值分位不可比。
- 股息率是港股长期回报的重要组成，dvRatio 高分位 + pe 低分位组合才是收入型配置信号。
- 月频滞后约一个月；短期港股情绪须配其他日频源。
- HSCI 的站点标题与通用指数命名存在歧义，引用前核对成分口径。
- 本条目 candidate，引用须标注未验证；HSI 数值目前只有页面文案，无接口证据。
