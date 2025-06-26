#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
市场监测报告生成器
自动执行市场分析并生成一份完整的PDF报告

主要功能：
1. 市场指数表现分析：监测主要市场指数（如上证指数、深证成指、沪深300等）的涨跌幅情况
2. 行业资金流向分析：分析各行业资金净流入/流出情况，识别热门与冷门行业
3. 热点个股资金流向分析：深入分析热点行业中的个股资金流向情况
   - 先使用同花顺行业资金流向(THS)API获取行业ts_code
   - 使用指数成分和权重API获取对应成分股列表(con_code)
   - 使用个股资金流向(THS)API获取每支股票的单日资金净流入数据
   - 按净流入金额排序后，取前十名绘制柱状图
4. 全市场个股资金净流入分析：分析全市场资金净流入最高的股票
   - 拉取全市场个股的当日资金净流入数据，排序后取前十名，柱状图展示
5. 量价背离指数：筛选当日涨幅前50但资金净流出的个股占比，反应市场虚涨风险
   - 计算过去20个交易日每天的量价背离指数，折线图展示
   - 占比大于30%警示回调可能性
6. 资金集中度指标：前10%个股的资金净流入占全市场比例
   - 计算过去20个交易日的数据，折线图展示
   - 集中度越高说明市场情绪越分化
7. 上涨/下跌股票比值：计算市场上涨股票数与下跌股票数的比值
   - 计算过去20个交易日的数据，折线图展示
   - 比值小于1表示下跌家数多于上涨家数，市场整体偏弱
   - 比值大于2表示上涨家数远多于下跌家数，可能处于强势上涨中
8. 技术指标分析：计算MACD、RSI等技术指标，预测市场顶部和底部
   - 基于上证指数计算各项技术指标
   - 生成技术指标图表，用于判断市场趋势
9. 涨停板晋级率分析：计算涨停板1进2、2进3晋级率
   - 计算过去30个交易日的晋级率数据，折线图展示
   - 晋级率越高表示市场热度越高，赚钱效应越强
10. 新高/新低股票分析：分析创52周新高和新低的股票数量
11. 创新高优质股票筛选：筛选创新高且满足特定条件的优质股票
    - 满足市值要求、相对位置要求、波动率要求、趋势性要求等条件
    - 生成股票列表，用于辅助投资决策
12. 自动生成PDF报告：整合所有分析结果成一份完整报告
13. 清理临时文件：报告生成后清理过程中生成的图片文件
"""

import os
import sys
import glob
import pandas as pd
from datetime import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
from cycler import cycler
import tushare as ts
from plot_index_performance import plot_index_performance
from plot_industry_moneyflow import plot_industry_moneyflow
# 注释掉热点行业个股分析的导入
# from analyze_top_industry_stocks import get_top_stocks_by_industry
from analyze_market_moneyflow import analyze_market_moneyflow
from analyze_price_volume_divergence import analyze_price_volume_divergence
from analyze_capital_concentration import analyze_capital_concentration
from create_pdf_report import create_pdf_report
# 导入上涨/下跌比值分析功能
from get_market_up_down_stocks import analyze_up_down_ratio
# 导入技术指标分析模块
from market_technical_indicators import analyze_market_trend
# 导入涨停板晋级率分析模块
from analyze_limit_promotion_rate import analyze_limit_stocks
# 导入新高/新低股票数分析模块
from analyze_high_low_stocks import analyze_high_low
# 导入创新高优质股票筛选模块
from new_high_stock_strategy import filter_stocks_for_report, generate_filtered_stocks_plot

# 设置统一的图表样式
def set_global_chart_style():
    """设置全局统一的图表样式"""
    # 设置字体和全局样式
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体为黑体
    plt.rcParams['axes.unicode_minus'] = False    # 正确显示负号
    
    # 设置图表样式
    plt.style.use('ggplot')
    
    # 设置全局配色方案（蓝色系为主）
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    mpl.rcParams['axes.prop_cycle'] = cycler(color=colors)
    
    # 设置线宽和标记尺寸
    plt.rcParams['lines.linewidth'] = 2
    plt.rcParams['lines.markersize'] = 8
    
    # 设置网格线样式
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # 设置轴标签和标题字体大小
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['axes.titlesize'] = 16
    
    # 设置刻度标签大小
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    
    # 其他设置
    plt.rcParams['figure.figsize'] = (12, 6)  # 默认图表大小
    plt.rcParams['figure.dpi'] = 100         # 默认DPI
    plt.rcParams['savefig.dpi'] = 120        # 保存图表的DPI

def generate_market_report(date=None, top_industry_count=3, top_stock_count=10, token=None, days=20, promotion_days=30, high_low_days=30):
    """
    生成完整的市场监测报告
    
    参数:
    date: 要分析的日期，格式为'YYYYMMDD'，若为None则使用最近交易日
    top_industry_count: 要分析的行业数量，默认为3
    top_stock_count: 每个行业要显示的股票数量，默认为10
    token: tushare API token，若为None则使用默认token
    days: 要分析的历史天数，用于量价背离指数和资金集中度指标，默认为20
    promotion_days: 涨停板晋级率分析的天数，默认为30
    high_low_days: 新高/新低分析的天数，默认为30
    
    返回:
    str: 生成的PDF报告路径
    """
    # 设置默认token
    if token is None:
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
    
    # 设置统一的图表样式
    set_global_chart_style()
    
    # 确保matplotlib不显示图形，仅保存到文件
    plt.ioff()  # 关闭交互模式
    
    print("\n" + "="*50)
    print("市场监测报告生成工具")
    print("="*50)
    print(f"开始生成报告，分析日期: {date if date else '最近交易日'}")
    print(f"分析热点行业数量: {top_industry_count}")
    print(f"每个行业分析热门股票数量: {top_stock_count}")
    print(f"历史分析天数: {days}天")
    print(f"涨停板晋级率分析天数: {promotion_days}天")
    print(f"新高/新低分析天数: {high_low_days}天")
    
    start_time = datetime.now()
    print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取日期范围
    if date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    else:
        end_date = date
    
    # 1. 生成大盘指数表现图
    print("\n[1/10] 正在生成市场指数表现图...")
    
    # 定义指数名称字典
    index_names = {
        '399300.SZ': '沪深300',
        '000001.SH': '上证指数',
        '399001.SZ': '深证成指',
        '000688.SH': '科创50',
        '399006.SZ': '创业板指',
        '399905.SZ': '中证500',
        '399852.SZ': '中证1000'
    }
    
    # 获取大盘指数表现
    df_index = plot_index_performance(index_names, end_date, end_date, save_fig=True, show_fig=False)
    print(f"市场指数表现图生成完成")
    
    # 2. 生成行业资金流向图
    print("\n[2/10] 正在生成行业资金流向图...")
    df_industry = plot_industry_moneyflow(token=token, date=end_date, top_n=10, save_fig=True, show_fig=False)
    print(f"行业资金流向图生成完成")
    
    # 注释掉热点行业个股分析部分
    """
    # 3. 生成热点行业个股分析图
    print("\n[3/9] 正在分析热点行业个股资金流向...")
    # 通过以下步骤实现：
    # - 获取行业资金流向数据，获取净流入最高的行业及其ts_code
    # - 使用指数成分和权重API获取行业成分股列表
    # - 使用个股资金流向(THS)API获取每支股票的资金净流入数据
    # - 排序后取前N名，生成柱状图
    industry_stocks = get_top_stocks_by_industry(token=token, date=end_date, 
                                              top_industry_count=top_industry_count, 
                                              top_stock_count=top_stock_count,
                                              save_fig=True, show_fig=False)
    
    print(f"热点行业个股分析完成")
    """
    
    # 3. 分析全市场个股资金净流入情况
    print("\n[3/10] 正在分析全市场个股资金净流入情况...")
    # 只获取资金净流入排行，不再获取资金净流入率排行
    net_inflow_top, _ = analyze_market_moneyflow(token=token, date=end_date, 
                                            top_n=top_stock_count, 
                                            save_fig=True, show_fig=False,
                                            only_net_inflow=True)  # 设置参数只获取净流入排行
    
    print(f"全市场个股资金净流入分析完成")
    
    # 4. 分析量价背离指数
    print("\n[4/10] 正在分析量价背离指数...")
    # 通过以下步骤实现：
    # - 计算过去N个交易日的量价背离指数
    # - 绘制折线图展示结果
    df_divergence = analyze_price_volume_divergence(token=token, days=days, 
                                                 top_n=50, save_fig=True, show_fig=False,
                                                 date=end_date)
    
    print(f"量价背离指数分析完成")
    
    # 5. 分析资金集中度指标
    print("\n[5/10] 正在分析资金集中度指标...")
    # 通过以下步骤实现：
    # - 计算过去N个交易日的资金集中度指标
    # - 绘制折线图展示结果
    df_concentration = analyze_capital_concentration(token=token, days=days, 
                                                  top_percent=10, save_fig=True, show_fig=False,
                                                  date=end_date)
    
    print(f"资金集中度指标分析完成")
    
    # 6. 分析上涨/下跌股票比值
    print("\n[6/10] 正在分析上涨/下跌股票比值...")
    # 通过以下步骤实现：
    # - 计算过去N个交易日的上涨/下跌股票比值
    # - 绘制折线图展示结果
    df_ratio = analyze_up_down_ratio(end_date=end_date, days=days, 
                                 token=token, save_fig=True, show_fig=False)
    
    print(f"上涨/下跌股票比值分析完成")
    
    # 7. 生成技术指标分析图
    print("\n[7/10] 正在分析技术指标...")
    # 分析市场趋势并生成技术指标图表
    tech_prediction, tech_fig_path = analyze_market_trend(
        market_code='000001.SH',   # 分析上证指数
        days=90,                  # 分析最近90天数据
        end_date=end_date,        # 使用指定结束日期
        save_fig=True,            # 保存图表
        show_fig=False            # 不显示图表
    )
    
    print(f"RSI技术指标分析完成")
    
    # 8. 分析涨停板晋级率
    print("\n[8/10] 正在分析涨停板晋级率...")
    # 分析涨停板晋级率并生成趋势图
    df_promotion = analyze_limit_stocks(
        token=token,
        end_date=end_date,
        days=promotion_days,
        save_fig=True,
        show_fig=False
    )
    
    print(f"涨停板晋级率分析完成")
    
    # 9. 分析新高/新低股票数量
    print("\n[9/10] 正在分析新高/新低股票数量...")
    # 分析新高/新低股票数量并生成趋势图
    df_52w, df_26w = analyze_high_low(
        token=token,
        end_date=end_date,
        days=high_low_days,
        force_update=False,  # 只在需要时更新数据
        save_fig=True,
        show_fig=False
    )
    
    print(f"新高/新低股票数分析完成")
    
    # 10. 筛选创新高优质股票
    print("\n[10/10] 正在筛选创新高优质股票...")
    # 使用新高股票策略筛选符合条件的股票
    filtered_stocks = filter_stocks_for_report(
        date=end_date,
        trade_days=300,           # 分析过去300个交易日的新高
        market_value=100,         # 筛选100亿市值以上的股票
        rebound=0.4,             # 相对位置不超过0.4（即当前价格在历史最低点到最高点之间的前40%区域内）
        volatility=0.04,          # 总体波动率阈值为4%
        recent_volatility=0.05,   # 最近五日波动率阈值为5%
        history_years=4,          # 使用最近4年的数据计算历史最高/最低点
        use_adj_price=True        # 使用前复权价格
    )
    
    # 生成筛选结果图表
    filtered_stocks_fig = None
    if filtered_stocks:
        filtered_stocks_fig = generate_filtered_stocks_plot(
            filtered_stocks,
            save_path="filtered_stocks.png",
            show_fig=False
        )
        print(f"找到 {len(filtered_stocks)} 只符合条件的创新高优质股票")
        
        # 保存为CSV，方便查看
        df_filtered = pd.DataFrame(filtered_stocks)
        df_filtered.to_csv(f"filtered_stocks_{end_date}.csv", index=False, encoding='utf-8-sig')
    else:
        print("未找到符合条件的创新高优质股票")
    
    print(f"创新高优质股票筛选完成")
    
    # 11. 生成PDF报告
    print("\n正在生成PDF报告...")
    report_filename = f"Stock_Market_Monitor_{end_date}.pdf"
    # 创建reports目录（如果不存在）
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    # 准备筛选股票数据（用于PDF报告）
    filtered_stocks_data = {
        'stocks': filtered_stocks,
        'figure_path': filtered_stocks_fig
    }
    
    # 在reports目录下生成报告
    report_path = os.path.join(reports_dir, report_filename)
    create_pdf_report(output_filename=report_path, filtered_stocks=filtered_stocks_data)
    
    # 12. 清理临时图片文件
    print("\n清理临时图片文件...")
    clean_temp_files(end_date)
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n报告生成完成!")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {duration.total_seconds():.2f} 秒")
    print(f"报告文件: {os.path.abspath(report_path)}")
    
    return report_path

def clean_temp_files(current_date):
    """
    清理生成报告过程中产生的临时图片文件
    
    参数:
    current_date: 当前日期，格式为'YYYYMMDD'，用于保留当前日期的PDF报告
    """
    try:
        # 删除所有PNG文件
        png_files = glob.glob("*.png")
        for file in png_files:
            try:
                os.remove(file)
                print(f"已删除临时文件: {file}")
            except Exception as e:
                print(f"删除文件 {file} 时出错: {str(e)}")
        
        # 删除根目录下旧的PDF文件，但保留当前日期的和reports目录中的文件
        pdf_files = glob.glob("*.pdf")
        current_report = f"Stock_Market_Monitor_{current_date}.pdf"
        
        for file in pdf_files:
            # 跳过当前日期的报告
            if file == current_report:
                continue
                
            try:
                os.remove(file)
                print(f"已删除旧报告: {file}")
            except Exception as e:
                print(f"删除文件 {file} 时出错: {str(e)}")
                
        print("临时文件清理完成")
    except Exception as e:
        print(f"清理临时文件时发生错误: {str(e)}")

def main():
    """
    主函数，处理命令行参数并执行报告生成
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='生成市场监测报告')
    parser.add_argument('--date', '-d', type=str, help='分析日期，格式为YYYYMMDD，默认为最近交易日')
    parser.add_argument('--industries', '-i', type=int, default=3, help='分析热点行业数量，默认为3')
    parser.add_argument('--stocks', '-s', type=int, default=10, help='每个行业分析热门股票数量，默认为10')
    parser.add_argument('--days', '-n', type=int, default=20, help='历史分析天数，用于量价背离指数和资金集中度指标，默认为20')
    parser.add_argument('--promotion-days', '-p', type=int, default=30, help='涨停板晋级率分析天数，默认为30')
    parser.add_argument('--high-low-days', '-hl', type=int, default=30, help='新高/新低分析天数，默认为30')
    parser.add_argument('--token', '-t', type=str, help='tushare API token')
    
    args = parser.parse_args()
    
    # 使用命令行参数生成报告
    generate_market_report(
        date='20250626',  # 使用命令行参数指定的日期
        top_industry_count=args.industries, 
        top_stock_count=args.stocks,
        token=args.token,
        days=args.days,
        promotion_days=args.promotion_days,
        high_low_days=args.high_low_days
    )

if __name__ == "__main__":
    main() 