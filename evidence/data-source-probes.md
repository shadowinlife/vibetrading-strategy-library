# 数据源探测记录（2026-11-26，library-validate-001）

验证前对免费数据源逐一探测，结果如下。失败如实记录；后续取数一律走可用源。

## 可用

| 源 | 用途 | 探测结果 |
| --- | --- | --- |
| yfinance（Yahoo） | 美股/港股日线（复权）、指数、市值 | SPY 2015 年起、^GSPC 1970 年起、^SP500TR 1988 年起、0700.HK 等正常；st-0002 批量 503+85 只成功 |
| OKX（VT okx loader，history-candles） | 加密日线 | BTC-USDT 评估窗口自 2017-12 起可得 |
| 腾讯行情（proxy.finance.qq.com） | 港股/A 股日线、A 股全市场实时（总市值 zsz/PE_TTM） | 0700.HK 正常；A 股全市场 5581 只分页成功 |
| sina（akshare） | A 股全市场实时快照、上证指数日线、财务指标、分红明细 | 全 A 5580 行成功；sh000001 8771 行；每股净资产/分红正常 |
| 东方财富 datacenter（akshare） | 沪市两融汇总历史、深市两融按日、个股两融 | stock_margin_sse 2000 行（2018-08-24→2026-11-25，接口上限）；stock_margin_szse 按日成功 |
| cninfo（akshare stock_industry_pe_ratio_cninfo） | 官方行业静态 PE（整体法加权） | 最新 120 行业成功；历史可回溯至 2023-12（更早返回空） |
| 世界银行公开 API | GDP（NY.GDP.MKTP.CD）、市值（CM.MKT.LCAP.CD） | USA/CHN/HKG 均成功，lastupdated 2026-11-11；市值 USA 1975 年起 |
| Shiller 公开数据（econ.yale.edu） | CAPE 与实际总收益指数月度 1871-2023.09 | ie_data.xls 下载成功（1.6MB） |
| GitHub datasets / Wikipedia | S&P500 成分（503）、恒指成分（85） | constituents.csv 成功；Wikipedia 首次 403 限流，重试成功 |

## 受限 / 不可用

| 源 | 现象 | 影响与处置 |
| --- | --- | --- |
| FRED（fred.stlouisfed.org） | fredgraph.csv 与 /data/ 端点均超时 | Wilshire 5000 历史不可得；kn-0002 改用世界银行市值序列（同口径公开正典） |
| DBnomics（FRED 镜像） | 404 | 同上 |
| legulegu（akshare stock_index_pe_lg / stock_buffett_index_lg） | 页面改版/拦截，_csrf 令牌缺失 | 行业 PE 历史改用 cninfo 官方源（窗口深度约 3 年，如实标注） |
| 东方财富 push2 行情（clist 全市场分页） | 大页（pz≥2000）502；akshare 全市场快照触发 IP 临时限流（约 5-40 分钟） | 美股全市场实时市值合计未取到；in-0002 以世界银行 2024 口径为准，实时交叉核对用 yfinance 股票池；A 股全市场截面改走 sina/腾讯成功 |
| ClickHouse ashare 镜像 | 本环境无 | in-0001 日度 pe/pb 因子、in-0003 历史日度全市场成交截面不可得；改用免费源并写明窗口限制 |
| Tushare | 无 token | margin/margin_detail 不可用；两融改走东财 datacenter 免费汇总（沪市历史+深市按日） |
| baostock | venv 未安装 | 未使用 |
| akshare stock_margin_account_info（两市汇总历史） | 多次 "Response ended prematurely" | 两市两融历史序列不可得；in-0003 背离序列用沪市口径，两市当前快照用沪市历史端点+深市按日端点拼合（单位换算已注明） |

## 单位与口径备忘

- sina A 股成交额：元；腾讯 zsz/ltsz：亿元；腾讯 turnover：万元。
- 沪市两融（stock_margin_sse）：元；深市两融（stock_margin_szse）：亿元（×1e8 换算）。
- 世界银行市值/GDP：当年美元；CM.MKT.LCAP.CD 口径为"上市本国公司"（不含境外上市本国公司）。
- yfinance 日线为 split_dividend 复权；港股 0700.HK 在 st-0001 中强制走 yfinance 复权口径（auto 路由的 tencent 源为不复权）。