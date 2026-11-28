---
id: in-0003
type: indicator
title: 成交集中度与两融余额背离（A 股）
status: research_only
vt_artifact_id: art_9f05c5ff897b
markets: [ashare]
asset_classes: [equity]
horizon: 日度
related: [kn-0001, in-0014]
formula: |
  成交集中度 = 成交额排名前 5% 个股的成交额之和 / 全市场成交额 × 100%
  两融背离 = 融资余额（或融资买入额）趋势与指数/两市成交趋势的背离：
  融资序列创新高而指数或成交额未创新高（或滚动增速差持续为负）记为背离触发。
data_source: |
  镜像环境 ClickHouse ashare 仓库（个股日成交额、指数行情）+ Tushare margin / margin_detail
  （融资融券每日汇总/明细，2010 年起，交易所每日更新）。
  注意：当前 worker 环境无 ClickHouse，本指标计算受限；镜像环境可用。
  legulegu 现成序列（2026-11-28 补录，成交集中度分量的替代来源）：
  /api/stockdata/ashares-congestion?token=（大盘拥挤度）与 /api/stockdata/cyshares-congestion?token=（创业板拥挤度），
  日频（ACCESS.md：2011 起），响应 dict{items,user,vip}；站点口径=成交额前5%个股成交额占比，
  页面 meta 2026-11-27：大盘 45.66%、创业板 49.10%，站点预警阈值 50%。深证分量（szshares-congestion）未验证。
  两融分量替代来源：/stockdata/margin-trading-data?token=（分交易所日频，金额亿元/融券卖出量万股，
  匿名窗口实测 2025-09-01→2026-11-26；详见 in-0014）。
  ClickHouse 映射：legulegu.series，无参数端点 param 段为 -（占位，不省略），series_id 如 ashares-congestion:-:<field>、
  cyshares-congestion:-:<field>、margin-trading-data:<exchangeId>:rzye（ch-legulegu-sync 管道并行建设中，仅引用约定）。
computation: |
  1. 取全市场个股日成交额，降序排序，取前 5% 个股成交额求和，除以全市场成交额得集中度；
  2. 取两融融资余额/融资买入额日度序列（Tushare margin 汇总或镜像 ClickHouse 表）；
  3. 对比融资序列与指数/两市成交序列的滚动新高状态与增速差，标记背离触发；
  4. 输出集中度序列与背离标记，附数据覆盖区间；数据不可达时明说（fail loud），不得静默降级。
unit: 成交集中度为 %；背离为布尔触发标记，增速差为百分点。
sources:
  - title: 镜像仓 escape-top-microstructure 技能文件（成交集中度/两融背离信号族定义与验证状态）
    url: https://github.com/shadowinlife/vibetrading-opencode-instruct/blob/main/skills/escape-top-microstructure/SKILL.md
    date: 2026-08-18
  - title: Tushare 融资融券交易明细接口文档（margin_detail，含融资余额/融资买入额字段与单位说明）
    url: https://tushare.pro/document/2?doc_id=59
    date: 2026-11-25
  - title: 乐咕乐股网：大盘拥挤度（ashares-congestion，top5%成交占比，站点阈值50%）
    url: https://www.legulegu.com/stockdata/ashares-congestion
    date: 2026-11-28
  - title: 乐咕乐股网：创业板拥挤度（cyshares-congestion，创业板口径同定义）
    url: https://www.legulegu.com/stockdata/cyshares-congestion
    date: 2026-11-28
intended_use: A 股拥挤度与杠杆资金动能的日度度量，供 kn-0001（市场拥挤/过热与顶部风险）使用。
limitations: research_only（2026-11-26 首轮验证，部分可算，未达完整口径）：已用免费源算出真实样本——全 A 单日成交集中度（sina 5577 只，top5% 占 44.5%）、沪市两融背离日度序列（2018-08→2026-11，244 个触发日）、两市两融当前快照（2.11 万亿元）；但完整口径不可达——历史日度全市场成交截面免费源不可得（东财 push2 限流、无 ClickHouse/Tushare/baostock），集中度只有单日样本无时间序列；两融背离序列仅沪市口径（深市汇总历史需逐日调用、两市汇总历史端点多次失败）；解锁完整验证需要：ClickHouse ashare 镜像（个股日成交额）或 Tushare margin 积分权限，或可持续的东财全市场分页访问。两融背离子信号已在镜像仓验证（引用纪律见正文），成交集中度为研究级；不得用估算冒充。引用必须标注"未验证，仅供参考"。legulegu 补充来源（2026-11-28）：拥挤度现成序列为站点第三方自动采集（不保证准确），items 内部字段未采样；创业板分量与大盘分量池口径不同不可直接比较；两融替代来源匿名窗口仅约 15 个月（in-0014），长历史背离序列仍需 Tushare/镜像仓。
created: 2026-11-25
updated: 2026-11-28
---

# 成交集中度与两融余额背离（A 股）

## 口径说明

- **成交集中度**：escape-top 框架定义为 top5% 个股成交额占全市场成交额份额。份额抬升 = 资金抱团、市场宽度恶化。
- **两融背离**：融资余额/融资买入额与指数或两市成交的趋势背离。镜像仓已验证子信号 `margin_divergence` 即属此类。
- **验证状态（引用纪律）**：其子信号两融背离（margin_divergence）/波动扩张（volatility_atr_expansion）已在镜像仓通过 7 门验证（证据：来源技能文件链接）；成交集中度信号族为研究级（RESEARCH_ONLY）。本指标条目整体标 candidate：口径整理自镜像技能与公开接口文档，未在本库独立复验。
- **数据可用性（如实标注）**：计算依赖镜像环境 ClickHouse ashare 仓库与 Tushare 两融接口；**当前 worker 环境无 ClickHouse，计算受限**。Tushare margin/margin_detail 需相应积分权限。2026-11-26 首轮验证改用免费源算出部分真实样本（见验证记录），但完整日度两市口径仍不可达。数据不可达时必须明说，不得静默降级为中性结论。
- **legulegu 现成序列（2026-11-28 补录）**：成交集中度分量可直接取 legulegu 拥挤度日频序列（ashares-congestion 大盘 / cyshares-congestion 创业板，2011 起），定义与本条目 top5% 口径一致，不另立条目；站点预警阈值 50%（页面 meta：2026-11-27 大盘 45.66%、创业板 49.10%）。两融分量可取 margin-trading-data（in-0014，匿名窗口约 15 个月）。CH 映射 legulegu.series（管道建设中仅引用约定）。

## 验证记录（2026-11-26，research_only）

- **成交集中度（单日样本）**：sina 全 A 实时快照 5577 只有效成交额，全市场成交 1.18 万亿元，top5%（279 只）占 44.5%、top1% 占 20.1%、top10 占 7.8%。数值合理（资金向头部集中）。**历史日度全市场截面免费源不可得，无集中度时间序列**——这是与完整口径的主要差距。
- **两融背离（沪市序列）**：沪市融资余额（东财 datacenter 免费汇总，2018-08-24→2026-11-25，2000 日）vs 上证综指，120 日新高背离触发 244 日；最新未触发，20 日增速差 -4.29pp。两市当前融资余额快照 2.11 万亿元（沪 1.109 万亿+深 1.005 万亿，单位换算已注明）。**深市汇总历史与两市汇总历史端点不可得，序列仅沪市口径**。
- **子信号事件研究**：背离触发日后 60 日指数平均 -1.80% vs 非触发日 +1.78%（差 -3.58pp），方向支持顶部风险含义（重叠事件、单市场、单信号族，见 kn-0001）。
- **判定**：research_only——机制部分跑通、有真实样本，但完整日度两市口径受数据限制未达。解锁条件见 limitations。证据：[evidence/in-0003/](../evidence/in-0003/)。

## 计算步骤

1. 全市场个股日成交额降序排序，前 5% 个股成交额求和 / 全市场成交额 × 100%。
2. 取融资余额（rzye）与融资买入额（rzmre）日度序列（Tushare margin 汇总或镜像表；单位：元，注意千元/万元换算规则）。
3. 计算融资序列与指数/成交序列的滚动新高状态与增速差，标记背离。
4. 输出序列 + 触发标记 + 数据覆盖区间。

## 解读注意

- 集中度与背离是顶部风险的辅助证据，需与估值分位（in-0001）等组合印证，不单独作为买卖依据。
- 两融占成交比重趋势性下降时，背离信号含义减弱。
- 强趋势市中信号可能长期钝化；早预警与高选择性预设的取舍见 kn-0001。
- 单位换算（千元/万元/元、手/股）必须遵守数据源登记规则，不得绕过。
