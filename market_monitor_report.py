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
   - 计算全市场每个股票的资金流入率=(资金净流入/当日成交额)*100%，排序后取最高的前十名，柱状图展示
5. 自动生成PDF报告：整合所有分析结果成一份完整报告
"""

import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import tushare as ts
from plot_index_performance import plot_index_performance
from plot_industry_moneyflow import plot_industry_moneyflow
from analyze_top_industry_stocks import get_top_stocks_by_industry
from analyze_market_moneyflow import analyze_market_moneyflow
from create_pdf_report import create_pdf_report

def generate_market_report(date=None, top_industry_count=3, top_stock_count=10, token=None):
    """
    生成完整的市场监测报告
    
    参数:
    date: 要分析的日期，格式为'YYYYMMDD'，若为None则使用最近交易日
    top_industry_count: 要分析的行业数量，默认为3
    top_stock_count: 每个行业要显示的股票数量，默认为10
    token: tushare API token，若为None则使用默认token
    
    返回:
    str: 生成的PDF报告路径
    """
    # 设置默认token
    if token is None:
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
    
    # 确保matplotlib不显示图形，仅保存到文件
    plt.ioff()  # 关闭交互模式
    
    print("\n" + "="*50)
    print("市场监测报告生成工具")
    print("="*50)
    print(f"开始生成报告，分析日期: {date if date else '最近交易日'}")
    print(f"分析热点行业数量: {top_industry_count}")
    print(f"每个行业分析热门股票数量: {top_stock_count}")
    
    start_time = datetime.now()
    print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取日期范围
    if date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    else:
        end_date = date
    
    # 1. 生成大盘指数表现图
    print("\n[1/4] 正在生成市场指数表现图...")
    
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
    print("\n[2/4] 正在生成行业资金流向图...")
    df_industry = plot_industry_moneyflow(token=token, date=end_date, top_n=10, save_fig=True, show_fig=False)
    print(f"行业资金流向图生成完成")
    
    # 3. 生成热点行业个股分析图
    print("\n[3/4] 正在分析热点行业个股资金流向...")
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
    
    # 4. 分析全市场个股资金净流入情况
    print("\n[4/4] 正在分析全市场个股资金净流入情况...")
    # 通过以下步骤实现：
    # - 拉取全市场个股的当日资金净流入数据
    # - 分别按净流入金额和流入率排序，取前10名
    # - 生成两张柱状图
    net_inflow_top, inflow_rate_top = analyze_market_moneyflow(token=token, date=end_date, 
                                                            top_n=top_stock_count, 
                                                            save_fig=True, show_fig=False)
    
    print(f"全市场个股资金净流入分析完成")
    
    # 5. 生成PDF报告
    print("\n正在生成PDF报告...")
    report_filename = f"Stock_Market_Monitor_{end_date}.pdf"
    create_pdf_report(output_filename=report_filename)
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n报告生成完成!")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {duration.total_seconds():.2f} 秒")
    print(f"报告文件: {os.path.abspath(report_filename)}")
    
    return report_filename

def main():
    """
    主函数，处理命令行参数并执行报告生成
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='生成市场监测报告')
    parser.add_argument('--date', '-d', type=str, help='分析日期，格式为YYYYMMDD，默认为最近交易日')
    parser.add_argument('--industries', '-i', type=int, default=3, help='分析热点行业数量，默认为3')
    parser.add_argument('--stocks', '-s', type=int, default=10, help='每个行业分析热门股票数量，默认为10')
    parser.add_argument('--token', '-t', type=str, help='tushare API token')
    
    args = parser.parse_args()
    
    # 生成报告
    generate_market_report(date=args.date, 
                         top_industry_count=args.industries, 
                         top_stock_count=args.stocks,
                         token=args.token)

if __name__ == "__main__":
    main() 