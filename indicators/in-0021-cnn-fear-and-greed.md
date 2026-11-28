---
id: in-0021
type: indicator
title: CNN恐惧贪婪指数（cnn-fear-and-greed，转引，日频）
status: candidate
markets: [us]
asset_classes: [equity, index]
horizon: 日频
related: [in-0017]
formula: |
  score = CNN Fear & Greed Index（0–100，综合 7 个市场情绪分项的加权指数；原始算法见 CNN 官方说明）
  close = 标普500指数收盘价（对照序列，样本 2021-01-04=3700.65 与标普量级一致）
data_source: |
  legulegu 转引端点 /api/stockdata/cnn-fear-and-greed?token=（cnn-fear-and-greed 页，React 族）。
  原始来源：CNN Business Fear & Greed Index（https://edition.cnn.com/markets/fear-and-greed）。
  频率：日频（实测 1483 点，2021-01-04→2026-11-25；转引窗口自 2021 年起，更早历史未提供）。
  字段：date/score/close。样本 2021-01-04 score=50.0；2021-10-18 score=47.0。
  ClickHouse 映射：legulegu.series，无参数端点 param 段为 -（占位，不省略），series_id 如
  cnn-fear-and-greed:-:score（转引系列落库须带原始来源标签；ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. GET /api/stockdata/cnn-fear-and-greed?token=<MD5(当天 YYYY-MM-DD)>；
  2. 解析日频 score 序列；
  3. 按 CNN 通用分区解读（0–25 极度恐惧 / 25–45 恐惧 / 45–55 中性 / 55–75 贪婪 / 75–100 极度贪婪；分区为 CNN 公开口径，未在本库验证）；
  4. 与 close 对照观察情绪与价格背离；
  5. 输出附转引来源、窗口起点与末端日期（转引滞后核对）。
unit: score 为 0–100 指数点；close 为指数点。
thresholds: "CNN 通用分区：<25 极度恐惧，>75 极度贪婪（公开口径，未验证；极端读数作反向参考）"
sources:
  - title: 乐咕乐股网：CNN恐惧贪婪指数（转引页）
    url: https://www.legulegu.com/stockdata/cnn-fear-and-greed
    date: 2026-11-28
  - title: CNN Business Fear & Greed Index（原始来源）
    url: https://edition.cnn.com/markets/fear-and-greed
    date: 2026-11-28
intended_use: 美股市场情绪的日频温度计，极端恐惧/贪婪作反向参考，供跨市场情绪对照（A 股宽度见 in-0017）。
limitations: |
  candidate 未验证。转引系列：原始算法与分项权重以 CNN 官方为准，legulegu 不保证转引准确（站点免责声明）；
  转引窗口自 2021-01-04 起（约 5 年），长期分位不可算；末端 2026-11-25，相对 A 股系列（2026-11-27）滞后 2 天，
  用作当前读数须核对。情绪指数是反向参考而非择时信号，极端读数可长期钝化（强趋势市）。
created: 2026-11-28
updated: 2026-11-28
---

# CNN恐惧贪婪指数（转引）

## 口径说明

- 转引系列纪律：原始来源 CNN Business Fear & Greed Index，legulegu 仅为转引渠道；引用必须同时给出原始来源。
- score 0–100，综合市场动量/宽度/波动/避险需求等 7 分项（CNN 公开口径）；close 为标普500对照。
- 频率以接口日期序列为准：日频，2021-01-04→2026-11-25（1483 点）；转引窗口约 5 年。
- ClickHouse 映射：`legulegu.series`，series_id=`cnn-fear-and-greed:-:<field>`（带原始来源标签；管道建设中，仅引用约定）。

## 计算步骤

1. 带当天 token 请求端点。
2. 解析 score/close 日频序列，核对末端日期。
3. 按 CNN 通用分区标注情绪状态（分区未在本库验证）。
4. 自算窗口内分位（注明仅约 5 年）。
5. 输出附转引声明与数据日期。

## 解读注意

- 极度恐惧（<25）历史上常对应阶段性底部区域，极度贪婪（>75）对应过热——反向参考，不是精确信号。
- 强趋势市中情绪可长期停留在贪婪区，机械反向操作会逆势。
- 美股情绪对 A 股是外溢变量，传导有时滞，不能直接平移阈值。
- 转引滞后与窗口限制使"当前读数"和"历史分位"都须附保留声明。
- 本条目 candidate，引用须标注未验证。
