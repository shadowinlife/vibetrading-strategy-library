---
id: in-0017
type: indicator
title: 赚钱效应日内趋势（market-activity-trend-data，涨跌家数/涨跌停/涨跌幅分布）
status: candidate
markets: [ashare]
asset_classes: [equity]
horizon: 日内（当日 50 个时点，无历史序列）
related: [in-0003, in-0018]
formula: |
  市场宽度 = totalUp / total（上涨家数占比）
  涨停强度 = limitUp / total；赚钱效应分布 = up0To3/up3To5/up5To7/up7To10/up10To20 各档家数
  字段：total/totalUp/totalDown、limitUp/realLimitUp/onceLimitUp/stLimitUp（跌停对称）、
  up/down 各涨跌幅档、priceStop/pricePaused、description（等级标签）
data_source: |
  legulegu 端点 /stockdata/market-activity-trend-data?token=（market-activity-trend 页"赚钱效应日内趋势"，
  亦为 market-activity 页"赚钱效应分布"的数据源；jQuery 族共享组件）。
  频率：日内——实测 50 个时点，date 为 epoch 毫秒，2026-11-27 09:30→15:00（Asia/Shanghai）；仅当日，无历史。
  样本末点（收盘）：total=5224、totalUp=5025、totalDown=181、limitUp=435、realLimitUp=425、stLimitUp=9、
  up0To3=648、up3To5=844、up5To7=1061、up7To10=1276、up10To20=1196、description="SSS"。
  与 market-activity 页 meta（2026-11-27：435 家涨停/5025 家上涨/181 家下跌）逐项一致——日度页展示的是收盘快照。
  历史日度序列端点 marketData/getHistoryData?marketId=... 未测（untested_cap）。
  ClickHouse 映射：legulegu.series，无参数端点省略 param 段，series_id 如
  market-activity-trend-data:totalUp（日内序列落库须带时点；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /stockdata/market-activity-trend-data?token=<MD5(当天 YYYY-MM-DD)>；
  2. epoch 毫秒转 Asia/Shanghai 时点；
  3. 宽度 = totalUp/total；涨停家数区分 limitUp/realLimitUp/stLimitUp 口径（含 ST 关系未声明，样本 435 vs 425+9 差 1，不得假设精确包含关系）；
  4. 涨跌幅分布各档家数除以 total 得结构占比；
  5. 输出附时点（日内读数随时点变化，收盘点才是日度快照）。
unit: 家数（只）；宽度/占比为 %；date 为 epoch 毫秒。
sources:
  - title: 乐咕乐股网：赚钱效应日内趋势（market-activity-trend）
    url: https://www.legulegu.com/stockdata/market-activity-trend
    date: 2026-11-28
  - title: 乐咕乐股网：A股赚钱效应分布（market-activity，收盘快照同源）
    url: https://www.legulegu.com/stockdata/market-activity
    date: 2026-11-28
intended_use: A 股当日市场宽度与赚钱效应的日内刻画，供情绪 extremes 识别与日度宽度序列的收盘快照来源。
limitations: |
  candidate 未验证。仅当日日内序列（50 点），历史日度宽度序列端点未测——本端点不能构建历史分位。
  description 字段样本值"SSS"，等级体系未声明（疑似赚钱效应分级），不得当作已验证信号。
  realLimitUp/onceLimitUp/priceStop/pricePaused 语义按字段名推断（real=剔除 ST？once=曾触及？priceStop 首点 847→末点 13，
  疑似未开盘/停牌相关计数），均未声明；涨跌停口径含 ST/北交所与否未声明（total=5224 的池范围未声明）。
  站点免责声明：第三方自动采集不保证准确。
created: 2026-11-28
updated: 2026-11-28
---

# 赚钱效应日内趋势（market-activity-trend-data）

## 口径说明

- 当日日内 50 时点（09:30→15:00，epoch 毫秒），收盘点即 market-activity 页的日度分布快照（已逐项核对一致）。
- 字段族：涨跌家数（total/totalUp/totalDown）、涨跌停（limitUp/realLimitUp/onceLimitUp/stLimitUp 及跌停对称）、
  涨跌幅分档（up0To3…up10To20、down0To3…down10To20）、priceStop/pricePaused、description。
- 样本收盘点（2026-11-27）：5224 只中 5025 涨/181 跌，涨停 435（realLimitUp=425、stLimitUp=9），上涨 10%~20% 档 1196 只——极端普涨日样本。
- description="SSS"：等级标签，体系未声明。
- ClickHouse 映射：`legulegu.series`，series_id=`market-activity-trend-data:<field>`（日内时点须保留；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 时点转北京时间；取收盘点作日度快照。
3. 宽度 = totalUp/total；分档占比 = 档内家数/total。
4. 涨停口径并列报告 limitUp/realLimitUp/stLimitUp，不假设包含关系。
5. 历史宽度序列须另测 marketData/getHistoryData，未测前不得宣称有历史。

## 解读注意

- 宽度极端高（>90% 上涨）与极端低都是情绪 extremes，反向参考而非顺势信号；单日读数噪声大。
- 涨停家数须区分含 ST 口径，跨源比较先对口径。
- 日内早段读数（如首点 priceStop=847）受开盘进程影响，不能与收盘点直接比较。
- 本端点无历史，做历史分位必须换源并声明。
- 本条目 candidate，引用须标注未验证。
