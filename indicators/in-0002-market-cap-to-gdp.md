---
id: in-0002
type: indicator
title: 股市总市值/GDP（巴菲特指标）
status: validated
vt_artifact_id: art_8b8bd090044a
markets: [us, ashare, hk]
asset_classes: [equity]
horizon: 年度 GDP + 日度市值，长期解读
related: [kn-0002]
formula: 巴菲特指标 = 股市总市值 / 名义 GDP × 100%
data_source: |
  市值：VT 市值工具（screen_market 全市场榜单聚合，或 get_market_data / 财务工具的市值字段求和）；
  GDP：世界银行公开数据 NY.GDP.MKTP.CD（GDP, current US$），公开 API 可查
  （示例：https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json）。
computation: |
  1. 取目标市场全部上市公司总市值并求和（统一币种；注明总股本口径或自由流通口径）；
  2. 取同一国家/地区最近年度名义 GDP（世界银行 NY.GDP.MKTP.CD，统一换算为与市值相同币种）；
  3. 比率 = 总市值 / GDP × 100%；
  4. 如需历史序列：市值按日/月回溯，GDP 按年度对齐（注意 GDP 修订与发布滞后）；
  5. 输出当前比率与历史区间，附数据日期与口径说明。
unit: "%"
sources:
  - title: "Warren Buffett on the stock market（Fortune，2001-12-10；市值/GNP 比率论述与 70–80%/200% 经验区间）"
    url: https://fortune.com/2001/12/10/warren-buffett-stock-market/
    date: 2001-12-10
  - title: 世界银行公开 API：GDP (current US$)，NY.GDP.MKTP.CD（美国示例查询，数据更新至 2026-11-11）
    url: https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.CD?format=json
    date: 2026-11-25
intended_use: 市场整体长期估值贵贱的单一比率度量，供 kn-0002（巴菲特指标）与长期回报预期判断使用。
limitations: 已验证（2026-11-26，世界银行同口径完整样本）：市值端用 CM.MKT.LCAP.CD"上市本国公司"口径（不含境外上市本国公司、总股本口径），与条目 data_source 建议的 VT 全市场榜单聚合口径不同，数值会有差异；GDP 年度数据滞后且会修订（本次 lastupdated 2026-11-11）；跨国证券化率结构差异使横向比较失真（港股 1114% 为结构性高位，非异常）；原文为美国 GNP 口径，GDP 替代存在细微差异；实时全市场市值交叉核对受东财 push2 限流影响，美股用 S&P500 池（非全市场）、A 股用腾讯全市场快照，日期与世行 2024 年末不同，仅作量级核对。
evidence:
  - summary: "三市场完整样本（世界银行同口径，2024 年末，当年美元）：US=62.19T/29.30T=212.25%、CN=11.76T/18.73T=62.77%、HK=4.55T/0.408T=1114.12%；与公开口径量级一致（美国历史高位、中国中位、港股结构性极高）"
    artifact: evidence/in-0002/results.json
    date: 2026-11-26
  - summary: "实时交叉核对：S&P500 池 live 市值 68.86T USD（为世行 2024 美国总量的 110.7%，日期差+口径差，量级一致）；A 股腾讯全市场 live 总市值 109.69 万亿元（约 15T USD 量级，与世行中国 2024 11.76T 一致）"
    artifact: evidence/in-0002/results.json
    date: 2026-11-26
created: 2026-11-25
updated: 2026-11-26
---

# 股市总市值/GDP（巴菲特指标）

## 口径说明

- 巴菲特 2001 年 Fortune 原文使用"全部公开交易证券市值 / GNP"；现代常用 GDP 替代 GNP（两者差异为净要素收入，量级小但需注明）。
- 市值口径必须声明：总股本市值 vs 自由流通市值；是否含境外上市本国公司。不同口径数值差异可达数十个百分点。
- GDP 用名义值（current prices），与市值同为当期价格，无需平减。
- 世界银行 NY.GDP.MKTP.CD 为公开数据（来源 API 链接已核实可访问，返回美国 2020–2024 年 GDP 现值美元序列）；其目录页 data.worldbank.org/indicator/NY.GDP.MKTP.CD 对自动化抓取返回 403（访问受限），数据本身经 API 核实。

## 计算步骤

1. 市值端：用 VT 市值工具取目标市场全市场市值并求和（如 screen_market 榜单聚合），统一币种。
2. GDP 端：世界银行 API 取同国家/地区最近年度名义 GDP，换算为相同币种。
3. 比率 = 总市值 / GDP × 100%。
4. 历史对比：美股可回溯数十年（原文图表近 80 年）；其他市场注意证券化率结构变化。
5. 输出附数据日期、市值口径、GDP 年份与修订状态。

## 解读注意

- 经验区间（巴菲特 2001 年原文，美国）：70%–80% 区域买入大概率回报良好；接近 200% 是"玩火"。阈值为历史经验，非机械信号。
- 低利率体制与利润占 GDP 比重上移会抬升比率中枢，历史阈值需重新校准。
- 比率是长期（10 年以上）回报预期的锚，短期预测力弱。
- 本指标已于 2026-11-26 完成首轮独立计算复验（世界银行同口径三市场样本），status=validated；口径与交叉核对局限见 limitations。

## 验证记录（2026-11-26）

- **方法**：市值端与 GDP 端同取世界银行公开 API（CM.MKT.LCAP.CD / NY.GDP.MKTP.CD，当年美元，2024 年末），同口径相除无需换汇；另做实时市值量级交叉核对。
- **结果**：US 212.25%、CN 62.77%、HK 1114.12%；美国处历史极端高位（与 kn-0002 实证一致），港股为结构性高证券化率（大量内地公司上市+本地 GDP 小），数值合理。
- **交叉核对**：S&P500 池 live 市值 68.86T USD、A 股腾讯全市场 live 109.69 万亿元，与世行口径量级一致（日期/口径差异已注明）。
- **判定**：validated——可按口径稳定计算、数值可信、与公开口径对照一致。证据：[evidence/in-0002/](../evidence/in-0002/)。历史序列实证见 kn-0002。
