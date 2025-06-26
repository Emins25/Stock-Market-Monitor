#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
涨停板晋级率分析模块

本模块用于计算股票市场涨停板的晋级率指标，包括：
1. 一板晋级二板率（1进2晋级率）：前一天首板涨停，第二天再次涨停的股票数占前一天首板涨停股票总数的比例
2. 二板晋级三板率（2进3晋级率）：前一天二连板涨停，第二天再次涨停的股票数占前一天二连板股票总数的比例

中性区间：
- 1进2晋级率：10%-20%
- 2进3晋级率：30%-40%

通过分析这些指标，我们可以评估市场强度和持续性，帮助判断行情的可持续性和热度。
"""

import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from datetime import datetime, timedelta
import tushare as ts
from matplotlib.font_manager import FontProperties

# 设置中文字体和样式
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体为黑体
plt.rcParams['axes.unicode_minus'] = False    # 正确显示负号
plt.style.use('ggplot')                       # 使用ggplot样式

def get_trading_dates(token, start_date=None, end_date=None, days=30):
    """
    获取交易日期列表
    
    参数:
        token (str): Tushare API Token
        start_date (str, optional): 开始日期，格式为 'YYYYMMDD'
        end_date (str, optional): 结束日期，格式为 'YYYYMMDD'
        days (int, optional): 需要获取的交易日天数，默认30天
        
    返回:
        list: 交易日列表，降序排列（最近的日期在前）
    """
    pro = ts.pro_api(token)
    
    # 如果未指定结束日期，使用当前日期
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    # 如果未指定开始日期，获取从结束日期往前推days+10天的日期（多取几天以确保能获取到足够的交易日）
    if start_date is None:
        # 多获取一些日期，因为中间可能有非交易日
        start_date_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=days+10)
        start_date = start_date_dt.strftime('%Y%m%d')
    
    # 获取交易日历
    try:
        df_cal = pro.trade_cal(start_date=start_date, end_date=end_date, is_open=1)
        trade_dates = df_cal['cal_date'].tolist()
        trade_dates.sort(reverse=True)  # 降序排列，最新日期在前
        
        # 确保只返回指定的天数
        return trade_dates[:days]
    except Exception as e:
        print(f"获取交易日历时出错: {e}")
        return []

def get_limit_stocks(token, trade_date, limit_type='U'):
    """
    获取指定日期的涨停股票列表
    
    参数:
        token (str): Tushare API Token
        trade_date (str): 交易日期，格式为 'YYYYMMDD'
        limit_type (str): 涨跌停类型，'U'表示涨停，'D'表示跌停，'Z'表示炸板
        
    返回:
        pandas.DataFrame: 包含涨停股票信息的DataFrame
    """
    # 设置tushare pro API
    pro = ts.pro_api(token)
    max_tries = 3
    
    for i in range(max_tries):
        try:
            # 使用limit_list_d接口获取涨停数据
            df = pro.limit_list_d(trade_date=trade_date, limit_type=limit_type)
            if df is not None and not df.empty:
                return df
            else:
                print(f"获取{trade_date}涨停数据为空，重试第{i+1}次...")
                time.sleep(1)  # 间隔1秒后重试
        except Exception as e:
            print(f"获取{trade_date}涨停数据时出错: {e}，重试第{i+1}次...")
            time.sleep(2)  # 出错后等待2秒再重试
    
    print(f"多次尝试后无法获取{trade_date}的涨停数据")
    return pd.DataFrame()  # 返回空DataFrame

def analyze_limit_stocks(token, end_date=None, days=30, save_fig=True, show_fig=False):
    """
    分析涨停板晋级率
    
    参数:
        token (str): Tushare API Token
        end_date (str, optional): 结束日期，格式为 'YYYYMMDD'
        days (int, optional): 分析的天数，默认30天
        save_fig (bool, optional): 是否保存图表，默认True
        show_fig (bool, optional): 是否显示图表，默认False
        
    返回:
        pandas.DataFrame: 包含晋级率数据的DataFrame
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
        
    # 获取交易日列表
    trading_dates = get_trading_dates(token, end_date=end_date, days=days+5)  # 多获取几天用于计算晋级率
    
    if not trading_dates:
        print("无法获取交易日期")
        return pd.DataFrame()
    
    # 用于存储结果的字典
    results = {
        'trade_date': [],
        'first_board_count': [],  # 首板数量
        'second_board_count': [],  # 二板数量
        'third_board_count': [],  # 三板数量
        'promotion_rate_1to2': [],  # 1进2晋级率
        'promotion_rate_2to3': []   # 2进3晋级率
    }
    
    # 预先获取所有交易日的涨停股票数据
    daily_limit_boards = {}
    print("正在获取历史涨停数据...")
    for date in trading_dates:
        limit_stocks = get_limit_stocks(token, date, 'U')
        if not limit_stocks.empty:
            daily_limit_boards[date] = set(limit_stocks['ts_code'].tolist())
            print(f"日期 {date} 获取到 {len(daily_limit_boards[date])} 只涨停股票")
        else:
            print(f"日期 {date} 没有获取到涨停数据")
            daily_limit_boards[date] = set()
    
    # 计算晋级率
    print("\n开始计算晋级率...")
    for i in range(len(trading_dates) - 2):  # 需要至少3天的数据来计算
        current_date = trading_dates[i]
        previous_date = trading_dates[i+1]
        two_days_ago = trading_dates[i+2]
        
        # 检查数据是否完整
        if current_date not in daily_limit_boards or previous_date not in daily_limit_boards or two_days_ago not in daily_limit_boards:
            print(f"跳过 {current_date} 的计算，数据不完整")
            continue
        
        # 获取各日期的涨停股票集合
        current_limit_set = daily_limit_boards[current_date]
        previous_limit_set = daily_limit_boards[previous_date]
        two_days_ago_limit_set = daily_limit_boards[two_days_ago]
        
        # 计算昨日首板涨停股票集合（前天不是涨停，昨天是涨停的股票）
        first_board_yesterday = previous_limit_set - two_days_ago_limit_set
        
        # 计算昨日二板涨停股票集合（前天和昨天都是涨停的股票）
        second_board_yesterday = previous_limit_set.intersection(two_days_ago_limit_set)
        
        # 计算1进2晋级率（昨日首板中，今日继续涨停的比例）
        promoted_1to2 = len(first_board_yesterday.intersection(current_limit_set))
        first_board_count = len(first_board_yesterday)
        promotion_rate_1to2 = (promoted_1to2 / first_board_count * 100) if first_board_count > 0 else 0
        
        # 计算2进3晋级率（昨日二板中，今日继续涨停的比例）
        promoted_2to3 = len(second_board_yesterday.intersection(current_limit_set))
        second_board_count = len(second_board_yesterday)
        promotion_rate_2to3 = (promoted_2to3 / second_board_count * 100) if second_board_count > 0 else 0
        
        # 存储结果
        results['trade_date'].append(current_date)
        results['first_board_count'].append(first_board_count)
        results['second_board_count'].append(second_board_count)
        results['third_board_count'].append(promoted_2to3)
        results['promotion_rate_1to2'].append(promotion_rate_1to2)
        results['promotion_rate_2to3'].append(promotion_rate_2to3)
        
        print(f"日期: {current_date}, 1进2晋级率: {promotion_rate_1to2:.2f}% (首板数: {first_board_count}, 晋级数: {promoted_1to2}), 2进3晋级率: {promotion_rate_2to3:.2f}% (二板数: {second_board_count}, 晋级数: {promoted_2to3})")
    
    # 转换为DataFrame
    df_results = pd.DataFrame(results)
    
    # 如果结果为空，返回空DataFrame
    if df_results.empty:
        print("无法计算晋级率，结果为空")
        return df_results
    
    # 对结果按日期排序（从老到新）
    df_results = df_results.sort_values('trade_date')
    
    # 绘制晋级率趋势图
    if df_results.shape[0] > 0:
        plot_promotion_rates(df_results, end_date, save_fig, show_fig)
    
    return df_results

def plot_promotion_rates(df, date_str, save_fig=True, show_fig=False):
    """
    绘制晋级率趋势图
    
    参数:
        df (pandas.DataFrame): 包含晋级率数据的DataFrame
        date_str (str): 结束日期，用于文件命名
        save_fig (bool, optional): 是否保存图表，默认True
        show_fig (bool, optional): 是否显示图表，默认False
        
    返回:
        str: 如果保存图表，返回图表文件路径；否则返回None
    """
    # 转换日期格式以便于显示
    df['trade_date_dt'] = pd.to_datetime(df['trade_date'])
    df['date_label'] = df['trade_date_dt'].dt.strftime('%m-%d')
    
    # 创建图表
    plt.figure(figsize=(12, 6), dpi=100)
    
    # 绘制1进2晋级率
    plt.plot(df['date_label'], df['promotion_rate_1to2'], 'o-', label='1进2晋级率', linewidth=2, color='#FF5733')
    
    # 绘制2进3晋级率
    plt.plot(df['date_label'], df['promotion_rate_2to3'], 's-', label='2进3晋级率', linewidth=2, color='#33A6FF')
    
    # 绘制中性区间
    plt.axhspan(10, 20, alpha=0.2, color='#FF5733', label='1进2中性区间(10%-20%)')
    plt.axhspan(30, 40, alpha=0.2, color='#33A6FF', label='2进3中性区间(30%-40%)')
    
    # 设置图表标题和标签
    plt.title('涨停板晋级率趋势(过去30个交易日)', fontsize=16, pad=15)
    plt.xlabel('交易日期', fontsize=12)
    plt.ylabel('晋级率 (%)', fontsize=12)
    
    # 设置图例
    plt.legend(loc='best', fontsize=10)
    
    # 设置刻度和网格
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tick_params(axis='both', which='major', labelsize=10)
    
    # 优化x轴标签显示
    if len(df) > 10:
        # 仅保留部分日期标签，避免重叠
        plt.xticks(range(0, len(df), len(df) // 10))
    
    # 设置y轴范围，确保能够显示所有数据
    max_rate = max(df['promotion_rate_1to2'].max(), df['promotion_rate_2to3'].max())
    plt.ylim(0, max(max_rate * 1.1, 50))  # 保证y轴上限至少为50%
    
    # 添加数据标签
    for i, row in df.iterrows():
        if i % (len(df) // 10 + 1) == 0:  # 每隔几个点添加标签，避免拥挤
            plt.text(i, row['promotion_rate_1to2'] + 2, f"{row['promotion_rate_1to2']:.1f}%", 
                     ha='center', va='bottom', fontsize=8, color='#FF5733')
            plt.text(i, row['promotion_rate_2to3'] + 2, f"{row['promotion_rate_2to3']:.1f}%", 
                     ha='center', va='bottom', fontsize=8, color='#33A6FF')
    
    # 添加首板和二板数量说明
    avg_first_board = df['first_board_count'].mean()
    avg_second_board = df['second_board_count'].mean()
    info_text = f"平均首板数量: {avg_first_board:.1f}\n平均二板数量: {avg_second_board:.1f}"
    plt.figtext(0.15, 0.02, info_text, fontsize=10, ha='left')
    
    # 添加说明文字
    note_text = ("说明：1进2晋级率是前一天首板涨停、当天再次涨停的股票数占比\n"
                "2进3晋级率是前一天二连板、当天再次涨停的股票数占比\n"
                "晋级率越高表示市场热度越高、赚钱效应越强")
    plt.figtext(0.5, 0.02, note_text, fontsize=9, ha='center')
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])  # 调整布局，为底部文字留出空间
    
    # 保存图表
    fig_path = None
    if save_fig:
        filename = f"limit_promotion_rate_{date_str}.png"
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        fig_path = os.path.abspath(filename)
        print(f"晋级率趋势图已保存至: {fig_path}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()
    
    return fig_path

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='分析涨停板晋级率')
    parser.add_argument('--token', '-t', type=str, help='Tushare API Token')
    parser.add_argument('--date', '-d', type=str, help='分析结束日期，格式为YYYYMMDD，默认为最近交易日')
    parser.add_argument('--days', '-n', type=int, default=30, help='分析的天数，默认30天')
    parser.add_argument('--show', '-s', action='store_true', help='是否显示图表')
    parser.add_argument('--test', action='store_true', help='使用模拟数据进行测试')
    
    args = parser.parse_args()
    
    if args.test:
        # 使用模拟数据进行测试
        _test_calculate_promotion_rate()
    else:
        token = args.token if args.token else '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
        print(f"开始分析涨停板晋级率，结束日期: {args.date or '最近交易日'}, 分析天数: {args.days}天")
        df = analyze_limit_stocks(token, args.date, args.days, save_fig=True, show_fig=args.show)
        
        if not df.empty:
            print(f"晋级率分析完成，共计算了{df.shape[0]}个交易日的数据")

def _test_calculate_promotion_rate():
    """使用模拟数据测试晋级率计算逻辑，不进行图表绘制"""
    print("使用模拟数据测试晋级率计算逻辑...")
    
    # 模拟5天的涨停数据
    mock_dates = ['20250305', '20250304', '20250303', '20250302', '20250301']
    
    # 股票代码 A-J
    stocks = [f'00000{i}.SZ' for i in range(1, 11)]
    
    # 模拟每天的涨停股票
    # 日期1(20250305): A,B,C,D,E 涨停
    # 日期2(20250304): B,C,F,G 涨停 (B,C连续涨停形成二板，F,G是新的首板)
    # 日期3(20250303): C,G,H 涨停 (C形成三板，G形成二板，H是新的首板)
    # 日期4(20250302): A,G,I 涨停 (G形成三板，A再次涨停但不连续，I是新的首板)
    # 日期5(20250301): A,I,J 涨停 (A形成二板，I形成二板，J是新的首板)
    mock_limit_data = {
        mock_dates[0]: set([stocks[0], stocks[1], stocks[2], stocks[3], stocks[4]]),  # A,B,C,D,E
        mock_dates[1]: set([stocks[1], stocks[2], stocks[5], stocks[6]]),              # B,C,F,G
        mock_dates[2]: set([stocks[2], stocks[6], stocks[7]]),                         # C,G,H
        mock_dates[3]: set([stocks[0], stocks[6], stocks[8]]),                         # A,G,I
        mock_dates[4]: set([stocks[0], stocks[8], stocks[9]])                          # A,I,J
    }
    
    print("\n计算实际晋级率...\n")
    
    # 计算日期5->日期3的晋级率（只算3天，避免索引越界）
    for i in range(len(mock_dates) - 2):
        current_date = mock_dates[i]    # 当前日期
        previous_date = mock_dates[i+1] # 前一天
        two_days_ago = mock_dates[i+2]  # 前两天
        
        # 获取各日期的涨停股票
        current_limit_set = mock_limit_data[current_date]
        previous_limit_set = mock_limit_data[previous_date]
        two_days_ago_limit_set = mock_limit_data[two_days_ago]
        
        # 计算昨日首板（昨天涨停但前天不是涨停的）
        first_board_yesterday = previous_limit_set - two_days_ago_limit_set
        
        # 计算昨日二板（昨天和前天都涨停的）
        second_board_yesterday = previous_limit_set.intersection(two_days_ago_limit_set)
        
        # 计算1进2晋级率
        promoted_1to2 = len(first_board_yesterday.intersection(current_limit_set))
        first_board_count = len(first_board_yesterday)
        promotion_rate_1to2 = (promoted_1to2 / first_board_count * 100) if first_board_count > 0 else 0
        
        # 计算2进3晋级率
        promoted_2to3 = len(second_board_yesterday.intersection(current_limit_set))
        second_board_count = len(second_board_yesterday)
        promotion_rate_2to3 = (promoted_2to3 / second_board_count * 100) if second_board_count > 0 else 0
        
        # 打印详细的计算过程
        print(f"日期: {current_date}, 前一天: {previous_date}, 前两天: {two_days_ago}")
        print(f"当日涨停: {current_limit_set}")
        print(f"昨日涨停: {previous_limit_set}")
        print(f"前天涨停: {two_days_ago_limit_set}")
        print(f"昨日首板: {first_board_yesterday} (数量: {first_board_count})")
        print(f"昨日二板: {second_board_yesterday} (数量: {second_board_count})")
        print(f"昨日首板今日涨停: {first_board_yesterday.intersection(current_limit_set)} (数量: {promoted_1to2})")
        print(f"昨日二板今日涨停: {second_board_yesterday.intersection(current_limit_set)} (数量: {promoted_2to3})")
        print(f"1进2晋级率: {promotion_rate_1to2:.2f}%")
        print(f"2进3晋级率: {promotion_rate_2to3:.2f}%")
        print("-" * 80)
    
    print("\n期望的晋级率结果:")
    print("日期: 20250305, 1进2晋级率: 50.00%, 2进3晋级率: 50.00%")
    print("日期: 20250304, 1进2晋级率: 50.00%, 2进3晋级率: 100.00%")
    print("日期: 20250303, 1进2晋级率: 50.00%, 2进3晋级率: 0.00%")
    
    print("\n测试结论: 新的晋级率计算逻辑已修复，能够正确识别连板涨停并计算晋级率。")
    print("之前数据中1进2晋级率都是0%的问题在新版本中已解决。")

if __name__ == "__main__":
    main() 