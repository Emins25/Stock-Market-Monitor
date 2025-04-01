#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新高新低股票数分析

功能：
1. 统计每天创52周新高和新低的股票数量
2. 统计每天创26周新高和新低的股票数量
3. 分别生成52周和26周新高新低趋势图
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tushare as ts
from datetime import datetime, timedelta
import time
from matplotlib.ticker import MaxNLocator

# 导入通用的Tushare工具模块
try:
    from tushare_utils import get_data_with_retry
except ImportError:
    # 如果导入失败，使用内部定义的版本
    def get_data_with_retry(func, max_tries=3, **kwargs):
        """
        带重试机制的数据获取函数
        
        参数:
        func: tushare接口函数
        max_tries: 最大重试次数，默认为3
        **kwargs: 传递给接口的参数
        
        返回:
        pd.DataFrame: 获取的数据
        """
        for i in range(max_tries):
            try:
                data = func(**kwargs)
                return data
            except Exception as e:
                error_msg = str(e)
                print(f"获取数据时出错 (尝试 {i+1}/{max_tries}): {error_msg}")
                
                # 检查是否是API访问频率限制错误
                if "每分钟最多访问该接口" in error_msg:
                    print(f"遇到API访问频率限制，暂停60秒后继续...")
                    time.sleep(60)  # 暂停60秒后继续尝试
                    continue  # 不增加retry计数，直接重试
                
                if i < max_tries - 1:  # 如果不是最后一次尝试，等待一段时间后重试
                    sleep_time = (i + 1) * 2  # 指数退避
                    print(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
        
        # 所有尝试都失败，返回空DataFrame
        print("所有尝试都失败，返回空数据")
        return pd.DataFrame()

# 全局变量
TUSHARE_TOKEN = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'

def get_trade_dates(pro, start_date, end_date):
    """
    获取指定日期范围内的交易日期
    
    参数:
    pro: tushare pro接口
    start_date: 开始日期，格式为'YYYYMMDD'
    end_date: 结束日期，格式为'YYYYMMDD'
    
    返回:
    list: 交易日期列表
    """
    try:
        df = get_data_with_retry(pro.trade_cal, exchange='SSE', 
                             start_date=start_date, end_date=end_date,
                             is_open='1')
        if df.empty:
            return []
        return sorted(df['cal_date'].tolist())
    except Exception as e:
        print(f"获取交易日期时出错: {e}")
        return []

def get_stock_price_data(pro, ts_code, start_date, end_date):
    """
    获取单只股票在指定日期范围内的价格数据
    
    参数:
    pro: tushare pro接口
    ts_code: 股票代码
    start_date: 开始日期，格式为'YYYYMMDD'
    end_date: 结束日期，格式为'YYYYMMDD'
    
    返回:
    pd.DataFrame: 股票价格数据
    """
    try:
        df = get_data_with_retry(pro.daily, ts_code=ts_code, 
                               start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        print(f"获取股票 {ts_code} 的价格数据时出错: {e}")
        return pd.DataFrame()

def get_all_stocks(pro):
    """
    获取所有A股股票列表
    
    参数:
    pro: tushare pro接口
    
    返回:
    pd.DataFrame: 股票基本信息
    """
    try:
        # 获取所有上市的A股
        stocks = get_data_with_retry(pro.stock_basic, exchange='', list_status='L',
                                 fields='ts_code,name,industry,market,list_date')
        return stocks
    except Exception as e:
        print(f"获取股票列表时出错: {e}")
        return pd.DataFrame()

def calculate_high_low_for_date(pro, trade_date, week_count, all_stocks):
    """
    计算指定交易日达到week_count周新高或新低的股票数量
    
    参数:
    pro: tushare pro接口
    trade_date: 交易日期，格式为'YYYYMMDD'
    week_count: 周数，例如52表示52周
    all_stocks: 所有股票的基本信息
    
    返回:
    tuple: (新高数量, 新低数量)
    """
    print(f"分析 {trade_date} 的{week_count}周新高新低...")
    
    # 计算week_count周对应的天数（约等于week_count * 7）
    days = week_count * 7
    
    # 计算开始日期
    date_obj = datetime.strptime(trade_date, '%Y%m%d')
    start_date = (date_obj - timedelta(days=days)).strftime('%Y%m%d')
    
    # 获取当日行情数据
    daily_data = get_data_with_retry(pro.daily, trade_date=trade_date)
    if daily_data.empty:
        print(f"获取 {trade_date} 行情数据失败")
        return 0, 0
    
    high_count = 0
    low_count = 0
    
    # 设置进度计数器
    total_stocks = len(all_stocks)
    processed_stocks = 0
    
    # 对于每只股票，检查是否创新高/新低
    for index, stock in all_stocks.iterrows():
        ts_code = stock['ts_code']
        
        # 更新进度
        processed_stocks += 1
        if processed_stocks % 50 == 0 or processed_stocks == total_stocks:
            print(f"处理进度: {processed_stocks}/{total_stocks} ({processed_stocks/total_stocks*100:.1f}%)")
        
        # 获取当日该股票的收盘价
        stock_daily = daily_data[daily_data['ts_code'] == ts_code]
        if stock_daily.empty:
            continue
        
        current_close = stock_daily['close'].values[0]
        
        # 获取历史价格数据
        hist_data = get_stock_price_data(pro, ts_code, start_date, trade_date)
        if hist_data.empty or len(hist_data) < 20:  # 确保有足够的历史数据
            continue
        
        # 排除当天的数据，只比较历史数据
        hist_data = hist_data[hist_data['trade_date'] < trade_date]
        if hist_data.empty:
            continue
        
        # 计算历史最高价和最低价
        hist_high = hist_data['high'].max()
        hist_low = hist_data['low'].min()
        
        # 判断是否创新高或新低
        if current_close >= hist_high:
            high_count += 1
        if current_close <= hist_low:
            low_count += 1
    
    print(f"{trade_date} {week_count}周新高数量: {high_count}, 新低数量: {low_count}")
    return high_count, low_count

def analyze_high_low(token=None, end_date=None, days=30, week_counts=[52, 26], save_fig=True, show_fig=False):
    """
    分析指定时间段内的新高新低股票数量
    
    参数:
    token: Tushare API token
    end_date: 结束日期，格式为'YYYYMMDD'，若为None则使用最近交易日
    days: 要分析的交易日天数，默认30天
    week_counts: 周数列表，默认[52, 26]表示分析52周和26周的新高新低
    save_fig: 是否保存图表，默认True
    show_fig: 是否显示图表，默认False
    
    返回:
    tuple: (52周新高新低DataFrame, 26周新高新低DataFrame)
    """
    if token:
        global TUSHARE_TOKEN
        TUSHARE_TOKEN = token
    
    # 初始化tushare接口
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    # 获取结束日期
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    # 获取所有A股股票
    all_stocks = get_all_stocks(pro)
    if all_stocks.empty:
        print("无法获取股票列表")
        return None, None
    
    # 计算开始日期（往前推days+10天，确保有足够的交易日）
    date_obj = datetime.strptime(end_date, '%Y%m%d')
    start_date = (date_obj - timedelta(days=days+10)).strftime('%Y%m%d')
    
    # 获取交易日列表
    trade_dates = get_trade_dates(pro, start_date, end_date)
    if not trade_dates:
        print("无法获取交易日期")
        return None, None
    
    # 只取最近days天的交易日
    recent_trade_dates = trade_dates[-days:] if len(trade_dates) >= days else trade_dates
    
    # 创建结果字典，用于存储每个周期的分析结果
    results = {}
    
    # 对每个周期进行分析
    for week_count in week_counts:
        print(f"\n开始分析{week_count}周新高新低...")
        
        # 存储该周期的结果
        week_results = []
        
        # 分析每个交易日
        for trade_date in recent_trade_dates:
            # 计算新高新低数量
            high_count, low_count = calculate_high_low_for_date(pro, trade_date, week_count, all_stocks)
            
            # 计算净新高（新高数 - 新低数）
            net_high = high_count - low_count
            
            # 保存结果
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            week_results.append({
                'trade_date': trade_date,
                'formatted_date': formatted_date,
                'high_count': high_count,
                'low_count': low_count,
                'net_high': net_high
            })
        
        # 创建DataFrame
        df_results = pd.DataFrame(week_results)
        
        # 保存结果
        results[week_count] = df_results
        
        # 绘制图表
        if not df_results.empty:
            plot_high_low_chart(df_results, week_count, end_date, save_fig, show_fig)
    
    # 返回结果
    return results.get(52), results.get(26)

def plot_high_low_chart(df, week_count, end_date, save_fig=True, show_fig=True):
    """
    绘制新高新低趋势图
    
    参数:
    df: 包含新高新低数据的DataFrame
    week_count: 周数，例如52表示52周
    end_date: 结束日期，用于文件命名
    save_fig: 是否保存图表，默认True
    show_fig: 是否显示图表，默认True
    
    返回:
    str: 如果保存图表，返回图表文件路径；否则返回None
    """
    # 创建图表
    plt.figure(figsize=(12, 6), dpi=100)
    
    # 将日期转换为datetime格式以便于绘图
    df['date'] = pd.to_datetime(df['trade_date'])
    
    # 绘制新高数量
    plt.plot(df['date'], df['high_count'], 'g-o', label=f'{week_count}周新高数', linewidth=2)
    
    # 绘制新低数量
    plt.plot(df['date'], df['low_count'], 'r-s', label=f'{week_count}周新低数', linewidth=2)
    
    # 绘制净新高（新高数 - 新低数）
    plt.bar(df['date'], df['net_high'], alpha=0.3, color='blue', label='净新高数')
    
    # 添加零线
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
    
    # 设置图表标题和标签
    plt.title(f'{week_count}周新高新低趋势（过去{len(df)}个交易日）', fontsize=16, pad=15)
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('股票数量', fontsize=12)
    
    # 设置x轴日期格式
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m-%d'))
    
    # 如果数据点较多，减少x轴刻度数量
    if len(df) > 10:
        plt.gca().xaxis.set_major_locator(plt.matplotlib.dates.DayLocator(interval=len(df)//10))
    
    # 设置y轴
    plt.gca().yaxis.set_major_locator(MaxNLocator(nbins=10))
    
    # 添加网格
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # 添加图例
    plt.legend(loc='best', fontsize=10)
    
    # 添加数据标签
    for i, row in df.iterrows():
        if i % (len(df) // 5 + 1) == 0:  # 选择性地添加标签以避免拥挤
            plt.text(row['date'], row['high_count'] + 3, f"{row['high_count']}", 
                    ha='center', va='bottom', fontsize=8, color='green')
            plt.text(row['date'], row['low_count'] - 3, f"{row['low_count']}", 
                    ha='center', va='top', fontsize=8, color='red')
    
    # 添加说明文字
    note_text = f"说明：\n" \
                f"新高：当日收盘价达到{week_count}周最高\n" \
                f"新低：当日收盘价达到{week_count}周最低\n" \
                f"净新高：新高数量减去新低数量"
    plt.figtext(0.5, 0.01, note_text, fontsize=9, ha='center')
    
    # 调整布局
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    
    # 保存图表
    fig_path = None
    if save_fig:
        filename = f"high_low_{week_count}w_{end_date}.png"
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        fig_path = os.path.abspath(filename)
        print(f"{week_count}周新高新低趋势图已保存至: {fig_path}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()
    
    return fig_path

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='分析新高新低股票数量')
    parser.add_argument('--token', '-t', type=str, help='Tushare API Token')
    parser.add_argument('--date', '-d', type=str, help='分析结束日期，格式为YYYYMMDD，默认为最近交易日')
    parser.add_argument('--days', '-n', type=int, default=30, help='分析的天数，默认30天')
    parser.add_argument('--show', '-s', action='store_true', help='是否显示图表')
    
    args = parser.parse_args()
    
    # 使用指定的token或默认token
    token = args.token if args.token else TUSHARE_TOKEN
    
    print(f"开始分析新高新低股票数量，结束日期: {args.date or '最近交易日'}, 分析天数: {args.days}天")
    
    # 分析新高新低
    df_52w, df_26w = analyze_high_low(
        token=token,
        end_date=args.date,
        days=args.days,
        save_fig=True,
        show_fig=args.show
    )
    
    if df_52w is not None and df_26w is not None:
        print(f"新高新低分析完成，共计算了 {len(df_52w)} 个交易日的数据")

if __name__ == "__main__":
    main() 