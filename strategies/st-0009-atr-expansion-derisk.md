---
id: st-0009
type: strategy
title: ATR 与已实现波动率联合扩张降仓（escape-top volatility_atr_expansion 操作化）
status: research_only
vt_artifact_id: art_54e4d3fd37ed
markets: [us, hk, crypto]
asset_classes: [equity, crypto]
horizon: 日度信号，数周至数月的仓位状态
related: [st-0001]
sources:
  - title: 镜像仓 escape-top-microstructure 技能文件（volatility_atr_expansion 信号族定义与 VALIDATED 分类；沿用 in-0003/kn-0001 的来源登记）
    url: https://github.com/shadowinlife/vibetrading-opencode-instruct/blob/main/skills/escape-top-microstructure/SKILL.md
    date: 2026-08-18
entry_rules: 基线满仓持有目标资产（目标权重 1.0）；当日收盘计算的联合扩张信号触发（ATR20 的 500 日滚动百分位 ≥80 且 250 日已实现波动率的 250 日滚动百分位 ≥80）时，次日开盘把目标权重降至 0.5。只做多，不加杠杆。
exit_rules: 联合扩张信号解除（两个百分位任一回落至 80 以下）时，次日开盘恢复目标权重 1.0；本条目不对标的设置止损/止盈（标的买入持有为对照基准）；前 500 个交易日暖机期信号未定义，维持目标权重 1.0。
position_sizing: 每市场单一代表标的（US=SPY.US、HK=0700.HK、crypto=BTC-USDT）；两态目标权重 1.0（正常）/0.5（扩张），降仓幅度 0.5 为操作化默认；不加杠杆、不摊平、不因信号连续触发而进一步减仓。
signal_definition: "TR_t = max(high_t - low_t, |high_t - close_{t-1}|, |low_t - close_{t-1}|)；ATR20_t = mean(TR_{t-19..t})（SMA 平滑，操作化默认）；atr_pct_t = 100 × count(ATR20_{t-499..t} < ATR20_t) / 500；RV_t = std(日收益率, 250 日) × sqrt(250)（crypto 年化因子取 365，百分位信号对年化因子不变）；vol_pct_t = 100 × count(RV_{t-249..t} < RV_t) / 250；expansion_t = (atr_pct_t >= 80) AND (vol_pct_t >= 80)。百分位定义与阈值 500/250/80 取自镜像实现 volatility_atr_expansion.py 与 joint_escape_top.py _CONDITION_DEFAULTS（signal_column=joint_vol_signal）。"
intended_use: 顶部风险风控 overlay：在波动扩张期把趋势/持有仓位减半，用于美股/港股/加密单一资产的回撤控制决策参考，与 st-0001 趋势框架互补。
limitations: research_only（2026-11-26 batch-1 验证，未转正）：信号与两态仓位已逐字实现并在三市场真实数据跑通，但"波动扩张降仓控制回撤"的迁移主张仅部分获支持——US（SPY）回撤控制显著：SMA 版 2016-08→2026-11 累计 +238.67%、最大回撤 -24.82%（买入持有 -33.72%）、Sharpe 0.92（买入持有 0.83），扩张期占评估 bar 18.8%，2022 -16.22% vs 买入持有 -18.65%；HK（0700.HK）边际：回撤 -69.08% vs 买入持有 -72.80%（仅降 3.7pp）、Sharpe 0.30 反低于买入持有 0.35、累计 +55.55% vs +82.06%；crypto（BTC-USDT）主回撤未控：最大回撤 -76.40% 与买入持有完全相同，2022 全年零扩张 bar（信号在崩盘后才触发，错过主跌），累计 +978.87% vs +1036.45%。Wilder(RMA) 平滑变体敏感性（必做已做）：US 差 -1.2pp（可忽略）、HK 差 +15.1pp、crypto 差 +57.4pp（US 外显著，平滑口径不可互换）。已知缺陷（保留）：镜像 7 门验证对象是上证综指前瞻回撤，本条目迁移到 US/HK/crypto 单一资产并映射 0.5/1.0 两态仓位，迁移有效性仅 US 获支持；0.5 降仓幅度为操作化默认未优化；500 日暖机使有效评估缩短（US/HK 自 2016-08/09、crypto 自 2019-04；ATR 百分位需 500 个已定义 ATR20 值，首个定义 bar 为第 519 根，暖机期维持 1.0）；每市场单一标的未测组合效应；80 百分位阈值与 500/250 窗口未做阈值敏感性；三市场均跑输买入持有绝对收益（价值在回撤控制，且仅 US 显著）。结论只适用于有界版本，不外推到"镜像信号在 A 股已验证 ⇒ 本仓位策略在 US/HK/crypto 有效"。引用必须标注"未验证，仅供参考"。
created: 2026-11-26
updated: 2026-11-26
---

# ATR 与已实现波动率联合扩张降仓（escape-top volatility_atr_expansion 操作化）

**验证声明：2026-11-26 batch-1 独立验证完成，判定 research_only（未转正）。信号与两态仓位在三市场跑通，但回撤控制迁移主张仅 US 显著获支持、HK 边际、crypto 主回撤未控（2022 零扩张 bar）；Wilder 平滑敏感性在 US 外显著。引用必须标注"未验证，仅供参考"。证据见 [evidence/st-0009/](../evidence/st-0009/)。**

本条目把镜像仓已通过 7 门验证的 `volatility_atr_expansion` 信号族操作化为免费数据可测的仓位策略。信号逻辑与阈值忠实取自镜像实现（本地 mymain@6b498a9 的 `OpencodeAgent/workspace/scripts/microstructure/volatility_atr_expansion.py` 与 `joint_escape_top.py`），数据输入替换为已实证可用的免费源；仓位映射是操作化新增，不是镜像结论。

## 验证记录（2026-11-26）

- **方法**：逐字实现 signal_definition——TR=max(高-低,|高-昨收|,|低-昨收|)；ATR20 取 20 日 SMA（操作化默认）与 Wilder(RMA) 变体；ATR 百分位=过去 500 日严格小于占比×100（用 rolling.rank(method='min') 精确复现 (rank-1)/n）；RV=日收益 250 日标准差×√250（crypto √365，百分位对年化因子不变）；RV 百分位=过去 250 日严格小于占比×100；扩张=两百分位均≥80。两态目标权重 1.0/0.5，暖机（百分位未定义）维持 1.0。VT 官方日线引擎，信号收盘计算次日开盘成交（内置 1 bar 延迟）；**执行机制**：`position_adjustment=rebalance` + 显式 ISO 日期 `rebalance_mask`=每个信号翻转的次一交易日（加首个评估日建仓），仅在翻转日执行、翻转间不做漂移再平衡——精确匹配条目两态语义（hold 模式会丢弃 1.0→0.5 同向 resize，故不用）。已验证：六次运行的成交日期全部落在 mask 内（除末日强制平仓），且用 run artifact 数据重算信号的翻转日与 mask 逐字一致。
- **标的与窗口**：SPY.US / 0700.HK（yfinance 复权）、BTC-USDT（OKX）。数据自 2014-09（US/HK）/2017-12（crypto），warmup_bars=500 扣除后评估自 2016-08-25（US）/2016-09-09（HK）/2019-04-15（crypto）至 2026-11。成本：US 5bps/边；HK 印花税 0.1%/边+佣金 0.015%+滑点 0.1%+征费/结算费、100 股/手假设；crypto taker/maker 0.1%+引擎默认滑点 0.05%（同 st-0001）。
- **结果（SMA 主口径）**：US +238.67%、回撤 -24.82%（B&H -33.72%）、Sharpe 0.92（B&H 0.83）、16 笔、扩张占 18.8%；HK +55.55%、回撤 -69.08%（B&H -72.80%）、Sharpe 0.30（B&H 0.35）、21 笔、扩张占 16.0%；crypto +978.87%、回撤 -76.40%（B&H -76.40%，相同）、Sharpe 0.84、12 笔、扩张占 10.2%。三市场均跑输 B&H 绝对收益（B&H：US +287.98%/HK +82.06%/crypto +1036.45%）。
- **关键失效（crypto）**：2022 全年零扩张 bar——扩张相位集中在 2019/2020-05/2021-01→06/2024，崩盘后才触发，主回撤（2021-11→2022-11）全程满仓，回撤控制目标在 crypto 落空。HK 回撤仅降 3.7pp 且 Sharpe 下降。US 2022 -16.22% vs B&H -18.65%、2020-03 回撤显著回避。
- **Wilder 敏感性（必做）**：US +239.87%（差 -1.2pp，可忽略）；HK +40.45%（差 +15.1pp）；crypto +921.46%（差 +57.4pp）——US 外平滑口径显著影响结果，SMA/Wilder 不可互换。
- **判定**：research_only——机制按规则运行，但三市场迁移主张未统一获支持（US 显著、HK 边际、crypto 主回撤未控），平滑敏感性 US 外显著。证据阶梯停留在 backtest 阶段。

## 规则详述

- **信号定义**（镜像 joint_vol_signal 口径）：
  1. ATR20：TR = max(当日高-低, |当日高-昨收|, |当日低-昨收|)，取 20 日 SMA（平滑方式为操作化默认，见边界条件节）。
  2. ATR 百分位：ATR20 当日值在过去 500 个交易日（含当日）中的严格小于占比 ×100（镜像 `_compute_rolling_percentile` 的逐字口径）。
  3. 已实现波动率 RV：日收益率 250 日滚动标准差 × √250（crypto 用 √365；年化因子是单调变换，不改变百分位信号）。
  4. RV 百分位：RV 当日值在过去 250 个交易日（含当日）中的严格小于占比 ×100。
  5. 扩张状态 = ATR 百分位 ≥80 且 RV 百分位 ≥80（镜像 `_CONDITION_DEFAULTS`：atr_rolling_days=500、atr_percentile=80、vol_rolling_days=250、vol_percentile=80、signal_column=joint_vol_signal）。
- **入场/降仓**：扩张状态当日收盘确认，次日开盘目标权重 1.0 → 0.5。
- **出场/恢复**：扩张状态解除（任一百百分位 <80）当日收盘确认，次日开盘 0.5 → 1.0。无独立止损止盈；标的买入持有为对照。
- **暖机**：前 500 个交易日 ATR 百分位未定义，维持权重 1.0（操作化默认）。
- **执行假设**：日线、信号收盘计算、次日开盘成交（VT 官方引擎内置 1 bar 延迟）；成本沿用首轮惯例：US 滑点 5bps/边零佣金；HK 印花税 0.1%/边+佣金 0.015%+滑点 0.1%；crypto taker 0.1%/边。
- **标的与窗口**：SPY.US / 0700.HK（yfinance 复权日线，2014-09→2026-11）、BTC-USDT（OKX 日线，2017-12→2026-11）；扣除暖机后有效评估约 10 年/7 年。

## 默认边界条件（操作化）

原始定性主张 → 有界可测版本映射：

| 原始主张（镜像/技能） | 有界版本（本条目） | 默认值依据 |
| --- | --- | --- |
| 上证综指 ATR（idx_factor_pro.atr_bfq，N=20）500 日百分位 ≥80 且 RV 250 日百分位 ≥80 联合预警 | 同一逻辑用于 SPY/0700.HK/BTC-USDT 的免费日线（yfinance 复权/OKX），ATR20 由 OHLC 现算 | 窗口/阈值 500/250/80：镜像实现默认值（已读源码核对）；标的迁移：操作化默认，非镜像结论 |
| ATR 字段 atr_bfq（平滑口径未注明） | TR 的 20 日 SMA | 操作化默认，非文献值；验证时做 Wilder(RMA) 变体敏感性 |
| 镜像输出 RED/YELLOW/GREEN 预警状态（决策辅助，非交易指令） | 两态仓位 1.0/0.5，扩张期减半 | 操作化默认，非文献值；0.5 幅度未优化 |
| RV 年化因子 250（A 股） | 股票 250、crypto 365 | 镜像默认 250；crypto 365 为 VT volatility 技能惯例；百分位对因子不变 |
| 暖机期无信号 | 暖机期维持权重 1.0 | 操作化默认 |

**验证结论只适用于上述有界版本，不外推到原始模糊主张**（尤其不外推到"镜像信号在 A 股已验证 ⇒ 本仓位策略在 US/HK/crypto 有效"）。

## 适用场景

- 波动聚集明显的资产（加密、港股龙头）与有长期趋势的美股大盘 ETF；作为持有/趋势仓位的回撤控制 overlay。
- 数据条件：yfinance 美/港股复权日线、OKX 加密日线均已实证可用（data-source-probes.md）；需 ≥500 交易日历史供热身。
- A 股版本（sina sh000001 日线已实证 8771 行）是自然扩展，本轮未纳入有界版本，见 harvest.md。

## 风险

- **迁移风险**：镜像验证仅覆盖上证综指前瞻回撤；US/HK/crypto 的波动结构不同，信号可能钝化或误报。
- **收益拖累**：扩张期减半仓位在 V 型反弹中显著跑输买入持有（st-0001 已证实趋势类策略绝对收益有限，本条目同样以回撤控制为目标而非收益最大化）。
- **口径风险**：ATR 平滑方式（SMA vs Wilder）与镜像字段口径可能不一致；yfinance 复权口径与镜像不复权 atr_bfq 不同，跨口径数值不可直接比较。
- **参数敏感**：80 百分位阈值与 500/250 窗口未做敏感性；暖机期长度影响有效样本。
- **执行风险**：日度翻转在震荡扩张期产生频繁 0.5↔1.0 切换，成本累积；港股印花税使切换成本显著高于美股。
