# Stock Market Monitor System

## 项目介绍

股票市场监测系统是一个自动化的市场分析工具，能够帮助投资者监控市场指数表现、行业资金流向以及热点个股资金流向。系统通过Tushare API获取最新的市场数据，并生成直观的可视化图表和完整的PDF格式分析报告。

## 主要功能

1. **市场指数表现分析**：监测主要市场指数（如上证指数、深证成指、沪深300、科创50等）的涨跌幅情况
2. **行业资金流向分析**：分析各行业资金净流入/流出情况，识别热门与冷门行业
3. **热点个股资金流向分析**：深入分析热点行业中的个股资金流向情况
拉取热点行业个股每日的资金净流入金额，识别热点行业中的热门个股，配合行业数据进行交叉验证
先根据Tushare的同花顺行业资金流向（THS）返回的行业对应的ts_code，使用Tushare的指数成分和权重API接口获取对应的成分股列表，获取成分股的con_code，
再利用con_code，使用Tusahre的个股资金流向（THS）API接口获取每支股票的单日资金净流入数据
根据净流入数据排序之后，取前十名画柱状图展示结果
4. **全市场个股资金净流入分析**：分析全市场资金净流入最高的股票
拉取全市场个股的当日资金净流入数据，排序之后取前十名，柱状图展示
计算全市场每个股票的资金流入率=（资金净流入/当日成交额）*100%，排序后取最高的前十名，柱状图展示
5. **量价背离指数**：筛选当日涨幅前50但资金净流出的个股占比，反应市场虚涨风险，占比大于30%警示回调可能性
计算过去20个交易日每天的量价背离指数
分别拉取每天全市场涨幅前50的股票，并拉取他们的资金净流入/流出情况，计算量价背离指数
将过去20天的数据画折线图展示
6. **资金集中度指标**：前10%个股的资金净流入占全市场比例
计算过去20个交易日的数据
每个交易日拉取所有股票的当日资金净流入数据，对10%求和同时对整体求和，计算前10%占总体的比例
将过去20个交易的数据画折线图展示

5. **自动生成PDF报告**：将所有分析结果整合成一份专业的PDF格式报告

## 技术栈

- **Python**：核心编程语言
- **Tushare API**：金融数据接口
- **Pandas**：数据处理与分析
- **Matplotlib**：数据可视化
- **ReportLab**：PDF报告生成

## 安装说明

1. 克隆项目到本地：
   ```
   git clone https://github.com/yourusername/Stock-Market-Monitor.git
   ```

2. 安装所需依赖：
   ```
   pip install tushare pandas matplotlib reportlab
   ```

3. 获取Tushare API Token：
   - 在[Tushare官网](https://tushare.pro/)注册并获取API Token
   - 或使用系统默认提供的Token（默认Token使用限制会降低访问频率）

## 使用方法

### 生成完整市场报告

```
python market_monitor_report.py --date 20250325 --industries 3 --stocks 10
```

参数说明：
- `--date` 或 `-d`：分析日期，格式为YYYYMMDD，默认为最近交易日
- `--industries` 或 `-i`：分析的热点行业数量，默认为3个
- `--stocks` 或 `-s`：每个行业分析的热门股票数量，默认为10个
- `--token` 或 `-t`：Tushare API Token，可选参数

### 单独生成市场指数表现图

```
python plot_index_performance.py
```

### 单独生成行业资金流向图

```
python plot_industry_moneyflow.py
```

### 单独生成热点行业个股分析图

```
python analyze_top_industry_stocks.py
```

## 输出文件

- **[日期]_index_performance.png**：市场指数表现图
- **[日期]_industry_moneyflow_top_bottom.png**：行业资金流向图
- **[日期]_industry_[行业名称]_stocks.png**：热点行业个股资金流向图
- **Stock_Market_Monitor_[日期].pdf**：完整的市场分析PDF报告

## 示例输出

系统将生成类似以下命名的文件：
- `index_performance_20250325.png`
- `industry_moneyflow_top_bottom_20250325.png`
- `industry_医药制造_stocks_20250325.png`
- `Stock_Market_Monitor_20250325.pdf`

## 联系与支持

如有问题或建议，请提交Issue或联系项目维护者。