# Stock Market Monitor System / 股票市场监测系统

<div align="center">
  <img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/assets/logo.png" alt="Stock Market Monitor Logo" width="200"/>
  <br>
  <p><i>🚀 一站式A股市场监测分析系统 / One-stop A-share Market Monitoring and Analysis System</i></p>
  <p>
    <a href="#功能亮点-features">功能/Features</a> •
    <a href="#示例输出-example-outputs">示例/Examples</a> •
    <a href="#安装说明-installation">安装/Installation</a> •
    <a href="#使用方法-usage">使用/Usage</a> •
    <a href="#贡献指南-contribution">贡献/Contribution</a>
  </p>
  
  <p>
    <img alt="GitHub stars" src="https://img.shields.io/github/stars/yourusername/Stock-Market-Monitor?style=for-the-badge">
    <img alt="GitHub forks" src="https://img.shields.io/github/forks/yourusername/Stock-Market-Monitor?style=for-the-badge">
    <img alt="GitHub issues" src="https://img.shields.io/github/issues/yourusername/Stock-Market-Monitor?style=for-the-badge">
    <img alt="Python Version" src="https://img.shields.io/badge/python-3.8%2B-blue?style=for-the-badge">
    <img alt="License" src="https://img.shields.io/github/license/yourusername/Stock-Market-Monitor?style=for-the-badge">
  </p>
</div>

## 📊 项目介绍 / Project Introduction

股票市场监测系统是一个强大的自动化市场分析工具，旨在帮助投资者实时监控市场动态。通过整合多种数据源和分析方法，系统能够提供全面的市场洞察，支持投资决策。

*The Stock Market Monitor System is a powerful automated market analysis tool designed to help investors monitor market dynamics in real-time. By integrating multiple data sources and analytical methods, the system provides comprehensive market insights to support investment decisions.*

> 💡 **市场研判从未如此简单！** 告别繁琐的数据收集和分析过程，一键获取专业级市场报告。
> 
> *Market analysis has never been easier! Say goodbye to tedious data collection and analysis processes, and get professional market reports with just one click.*

## ✨ 为什么选择本系统？/ Why Choose This System?

- **全面的市场分析**: 同时覆盖宏观指数、行业板块和个股层面
  
  *Comprehensive Market Analysis: Covers macro indices, industry sectors, and individual stocks simultaneously*

- **实时数据更新**: 通过Tushare API获取最新市场数据
  
  *Real-time Data Updates: Obtains the latest market data through Tushare API*

- **多维度分析指标**: 资金流向、量价背离、资金集中度等多维指标
  
  *Multi-dimensional Analysis Indicators: Capital flow, price-volume divergence, capital concentration, and other multi-dimensional indicators*

- **自动化报告生成**: 一键生成专业PDF分析报告
  
  *Automated Report Generation: One-click generation of professional PDF analysis reports*

- **高度可定制**: 灵活的参数设置，满足不同分析需求
  
  *Highly Customizable: Flexible parameter settings to meet different analysis needs*

- **开箱即用**: 简洁的安装和使用流程
  
  *Ready to Use: Simple installation and usage process*

## 🔍 功能亮点 / Features

1. **市场指数表现分析**: 实时监测主要市场指数的涨跌幅，提供直观的趋势图表。
   
   *Market Index Performance Analysis: Real-time monitoring of major market index gains and losses, providing intuitive trend charts.*

2. **行业资金流向分析**: 识别热门与冷门行业，分析资金净流入/流出情况。
   
   *Industry Capital Flow Analysis: Identify hot and cold industries, analyze net capital inflow/outflow.*

3. **热点个股资金流向分析**: 深入分析热点行业中的个股资金流向，识别市场热点。
   
   *Hot Stock Capital Flow Analysis: In-depth analysis of capital flow in hot industry stocks, identify market hotspots.*

4. **全市场个股资金净流入分析**: 筛选资金净流入最高的股票，提供投资参考。
   
   *Market-wide Stock Net Inflow Analysis: Filter stocks with the highest net capital inflow, providing investment references.*

5. **量价背离指数**: 评估市场虚涨风险，分析涨幅前50股票中资金净流出占比，当指数超过30%时警示潜在回调可能性。
   
   *Price-Volume Divergence Index: Evaluate market false rally risks by analyzing the percentage of stocks with net capital outflow among the top 50 gainers. When the index exceeds 30%, it alerts to potential market pullback possibilities.*

6. **资金集中度指标**: 分析市场资金分布，识别市场情绪。
   
   *Capital Concentration Indicator: Analyze market capital distribution, identify market sentiment.*

7. **技术指标分析**: 使用MACD和RSI等指标预测市场顶部和底部。
   
   *Technical Indicator Analysis: Use indicators such as MACD and RSI to predict market tops and bottoms.*

8. **晋级率分析**: 计算涨停板晋级率，评估市场热度。
   
   *Advancement Rate Analysis: Calculate limit-up board advancement rates, evaluate market heat.*

9. **新高/新低股票数统计**: 追踪市场新高新低股票数，分析市场健康度。
   
   *New High/Low Stock Count: Track the number of stocks making new highs and lows, analyze market health.*

10. **新高优质股票筛选**: 筛选创新高且满足市值、趋势、波动率、相对位置等特定条件的优质股票，辅助投资决策。
   
    *Quality New High Stock Filter: Screen for stocks that reach new highs and meet specific criteria including market value, trend, volatility, and relative position to support investment decisions.*

11. **自动生成PDF报告**: 整合所有分析结果，生成专业的PDF报告。
    
    *Automatic PDF Report Generation: Integrate all analysis results to generate professional PDF reports.*

<details>
  <summary><b>🔄 更多功能详情 / More Features</b></summary>
  
  - **智能日期处理**: 自动识别交易日和非交易日
    
    *Intelligent Date Processing: Automatically identify trading and non-trading days*
  
  - **数据异常处理**: 优雅处理缺失数据和异常值
    
    *Data Anomaly Handling: Elegantly handle missing data and anomalies*
  
  - **批量数据处理**: 高效处理和分析大量股票数据
    
    *Batch Data Processing: Efficiently process and analyze large volumes of stock data*
  
  - **自定义分析周期**: 灵活设置分析的时间周期
    
    *Custom Analysis Periods: Flexibly set time periods for analysis*
  
  - **数据可视化**: 生成直观易读的图表
    
    *Data Visualization: Generate intuitive and readable charts*
  
  - **结果持久化**: 自动保存分析结果和图表
    
    *Result Persistence: Automatically save analysis results and charts*
</details>

## 🖼️ 示例输出 / Example Outputs

<div align="center">
  <p><b>市场指数表现分析 / Market Index Performance Analysis</b></p>
  <img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/index_performance.png" alt="市场指数表现分析" width="700"/>
  
  <p><b>行业资金流向分析 / Industry Capital Flow Analysis</b></p>
  <img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/industry_moneyflow.png" alt="行业资金流向分析" width="700"/>
  
  <details>
    <summary><b>🔍 查看更多示例图片 / View More Example Images</b></summary>
    <p><b>热点个股资金流向 / Hot Stock Capital Flow</b></p>
    <img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/hot_stocks.png" alt="热点个股资金流向" width="700"/>
    
    <p><b>量价背离指数趋势 / Price-Volume Divergence Index Trend</b></p>
    <img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/divergence_index.png" alt="量价背离指数趋势" width="700"/>
  </details>
  
  <p><b>🌟 PDF报告预览 / PDF Report Preview</b></p>
  <img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/report_preview.png" alt="PDF报告预览" width="700"/>
</div>

## 🛠️ 技术栈 / Tech Stack

- **Python**: 核心编程语言 / Core programming language
- **Tushare API**: 金融数据接口 / Financial data interface
- **Pandas**: 数据处理与分析 / Data processing and analysis
- **Matplotlib**: 数据可视化 / Data visualization
- **ReportLab**: PDF报告生成 / PDF report generation

## 📥 安装说明 / Installation

1. 克隆项目到本地 / Clone the project locally:
   ```bash
   git clone https://github.com/yourusername/Stock-Market-Monitor.git
   cd Stock-Market-Monitor
   ```

2. 安装所需依赖 / Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   或手动安装 / Or install manually:
   ```bash
   pip install tushare pandas matplotlib reportlab requests numpy
   ```

3. 获取Tushare API Token / Get Tushare API Token:
   - 在[Tushare官网](https://tushare.pro/)注册并获取API Token / Register and get API Token at [Tushare official website](https://tushare.pro/)
   - 在配置文件中设置Token或通过命令行参数传入 / Set the Token in the configuration file or pass it via command line parameter

## 📚 使用方法 / Usage

### 生成完整市场报告 / Generate Complete Market Report

```bash
python market_monitor_report.py --date 20250325 --industries 3 --stocks 10 --days 20 --promotion-days 30 --high-low-days 30
```

<details>
  <summary><b>📋 参数详解 / Parameter Details</b></summary>
  
  - `--date` 或 `-d`: 分析日期，格式为YYYYMMDD，默认为最近交易日 / Analysis date, format YYYYMMDD, defaults to the most recent trading day
  - `--industries` 或 `-i`: 分析的热点行业数量，默认为3个 / Number of hot industries to analyze, default is 3
  - `--stocks` 或 `-s`: 每个行业分析的热门股票数量，默认为10个 / Number of hot stocks in each industry to analyze, default is 10
  - `--token` 或 `-t`: Tushare API Token，可选参数 / Tushare API Token, optional parameter
  - `--days` 或 `-n`: 历史分析天数，默认为20天 / Number of historical days to analyze, default is 20 days
  - `--promotion-days` 或 `-p`: 涨停板晋级率分析天数，默认为30天 / Number of days for limit-up board promotion rate analysis, default is 30 days
  - `--high-low-days` 或 `-hl`: 新高/新低分析天数，默认为30天 / Number of days for new high/low stock analysis, default is 30 days
  - `--output` 或 `-o`: 输出目录，默认为当前目录下的reports文件夹 / Output directory, default is the reports folder in the current directory
</details>

### 快速开始 / Quick Start

对于首次使用，我们推荐 / For first-time users, we recommend:

```bash
# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 生成最新的市场报告 / Generate the latest market report
python market_monitor_report.py

# 报告将保存在 ./reports/ 目录下 / The report will be saved in the ./reports/ directory
```

## 📊 实际应用案例 / Application Cases

<div align="center">
  <table>
    <tr>
      <td align="center"><img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/case1.png" width="200"/></td>
      <td align="center"><img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/case2.png" width="200"/></td>
      <td align="center"><img src="https://raw.githubusercontent.com/yourusername/Stock-Market-Monitor/main/examples/case3.png" width="200"/></td>
    </tr>
    <tr>
      <td align="center">📈 <b>市场热点追踪 / Market Hotspot Tracking</b></td>
      <td align="center">💰 <b>资金流向分析 / Capital Flow Analysis</b></td>
      <td align="center">🔍 <b>市场健康度评估 / Market Health Assessment</b></td>
    </tr>
  </table>
</div>

## 👥 贡献指南 / Contribution

我们欢迎所有形式的贡献，无论是新功能、文档改进还是bug修复！

*We welcome all forms of contribution, whether it's new features, documentation improvements, or bug fixes!*

1. Fork 本仓库 / Fork this repository
2. 创建您的特性分支 / Create your feature branch: `git checkout -b feature/amazing-feature`
3. 提交您的更改 / Commit your changes: `git commit -m '添加一些特性 / Add some feature'`
4. 推送到分支 / Push to the branch: `git push origin feature/amazing-feature`
5. 提交拉取请求 / Submit a pull request

查看[贡献指南](CONTRIBUTING.md)了解更多详情 / See [Contribution Guidelines](CONTRIBUTING.md) for more details.

## 🌟 用户反馈 / User Feedback

> "这个工具极大地提高了我的市场分析效率，每天都能快速获取市场全貌。" - 某基金经理
> 
> *"This tool greatly improved my market analysis efficiency, allowing me to quickly get a complete picture of the market every day." - Fund Manager*

> "量价背离和资金集中度指标帮助我及时发现了市场风险，避免了重大损失。" - 个人投资者
> 
> *"The price-volume divergence and capital concentration indicators helped me discover market risks in time, avoiding significant losses." - Individual Investor*

## 📄 许可证 / License

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

*This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.*

## 📞 联系与支持 / Contact & Support

- 提交Issue / Submit Issues: [GitHub Issues](https://github.com/yourusername/Stock-Market-Monitor/issues)
- 电子邮件 / Email: your.email@example.com
- 微信公众号 / WeChat Official Account: 市场监测助手 (Market Monitor Assistant)

---

<div align="center">
  <p>如果这个项目对您有帮助，请考虑给它一个⭐️！/ If this project helps you, please consider giving it a ⭐️!</p>
  <p>Made with ❤️ by Your Name</p>
</div>