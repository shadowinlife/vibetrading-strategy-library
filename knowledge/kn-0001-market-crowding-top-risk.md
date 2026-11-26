---
id: kn-0001
type: knowledge
title: 市场拥挤/过热与顶部风险（A 股）
status: research_only
markets: [ashare]
asset_classes: [equity]
horizon: 数周至数月（顶部预警窗口）
indicators: [in-0003]
related: [kn-0003]
sources:
  - title: 镜像仓 escape-top-microstructure 技能文件（A 股顶部预警信号框架与验证状态纪律）
    url: https://github.com/shadowinlife/vibetrading-opencode-instruct/blob/main/skills/escape-top-microstructure/SKILL.md
    date: 2026-08-18
intended_use: A 股大盘与组合层面的顶部风险预警、拥挤度判断与仓位风控辅助；与估值类条目（kn-0003）组合使用。
limitations: 本条目整体为 research_only：集成框架（RED/YELLOW/GREEN）未在本库独立复验；2026-11-26 首轮验证仅对两融背离子信号做了沪市口径事件研究（触发日后 60 日指数平均 -1.80% vs 非触发日 +1.78%，方向支持，重叠事件/单市场/单信号族，非集成验证）；数据依赖 ClickHouse/Tushare（本环境无），免费源仅部分可得（见 in-0003 limitations）；仅适用 A 股；信号是决策辅助，不是交易指令。引用必须标注"未验证，仅供参考"。
created: 2026-11-25
updated: 2026-11-26
---

# 市场拥挤/过热与顶部风险（A 股）

## 主张

A 股成交集中度抬升、两融加杠杆与价格/成交出现背离等过热信号共振时，大盘顶部风险显著上升，应降低风险暴露而非追涨。

## 机制（为什么）

- **成交集中度**：成交额排名前 5% 个股占全市场成交额的份额抬升，说明资金向少数热门股抱团，市场宽度恶化，边际买家趋于枯竭，一旦抱团瓦解容易引发连锁回撤。
- **两融背离**：融资余额或融资买入额继续创新高，而指数或两市成交额不再创新高，说明杠杆资金在高位接盘、上涨动能衰竭，是典型的顶部区域特征。
- **波动扩张**：顶部区域常伴随恐慌性换手与波动率放大，与拥挤信号互为印证。

镜像仓 escape-top 框架将约 15 个信号族经 7 门验证（覆盖度/选择性/方向性/统计分离/稳健性/子周期/相关性）分级后，集成输出 RED/YELLOW/GREEN 市场状态判定。

**验证状态（引用纪律）**：其子信号两融背离（margin_divergence）/波动扩张（volatility_atr_expansion）已在镜像仓通过 7 门验证，证据见来源链接的[技能文件](https://github.com/shadowinlife/vibetrading-opencode-instruct/blob/main/skills/escape-top-microstructure/SKILL.md)；其余信号族为 RESEARCH_ONLY 或 BLOCKED_BY_DATA（如 winner_rate_pressure 依赖的 stk_cyq_perf 已停止同步），引用时必须标注其验证分类。本条目作为集成框架整体未在本库独立复验，故标 research_only。

## 验证记录（2026-11-26，research_only 维持）

- **做了什么**：对两融背离子信号（in-0003 沪市序列，2018-08→2026-11，244 个触发日）做事件研究：触发日后 20 日指数平均 -0.31% vs 非触发日 +0.49%（差 -0.80pp）；后 60 日 -1.80% vs +1.78%（差 -3.58pp，触发日后负收益占比 67.6% vs 44.0%）。方向支持"背离→顶部风险"含义。
- **没做什么**：集成框架（约 15 信号族 7 门分级 + RED/YELLOW/GREEN）未独立复验；成交集中度族无历史序列（免费源限制）；事件研究为重叠事件、单市场、单信号族，naive 对照不构成显著性证明。
- **判定**：维持 research_only。子信号方向证据已存档（[evidence/kn-0001/](../evidence/kn-0001/)），集成主张仍待完整数据与独立复验。

## 用法

1. 用 [in-0003](../indicators/in-0003-turnover-concentration-margin-divergence.md) 计算成交集中度与两融背离，取得当前读数与数据覆盖区间。
2. 与估值分位（[kn-0003](kn-0003-valuation-percentile-mean-reversion.md) / in-0001）交叉印证：过热 + 高估值分位共振时顶部风险置信度提高；信号冲突时必须显式呈现，不得只挑有利证据。
3. 任何信号输出必须附带其验证分类与数据覆盖区间；数据不可达时明说，不得静默降级为中性结论。

## 失效情形

- 强趋势市中过热信号可能长期钝化，早预警预设下误报率高（宁缺毋滥的 strong 预设与早预警的 early 预设取舍不同）。
- 数据缺失或停更（如 stk_cyq_perf 停止同步）导致部分信号族不可用。
- 市场杠杆结构变化（两融占成交比重趋势性下降）会削弱两融背离信号的含义。
- 信号是决策辅助，不是交易指令；不能单独作为买卖依据。
