#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
资金集中度指标计算模块

资金集中度指标：前10%个股的资金净流入占全市场比例
- 计算过去20个交易日的数据
- 每个交易日拉取所有股票的当日资金净流入数据，对10%求和同时对整体求和，计算前10%占总体的比例
- 将过去20个交易的数据画折线图展示
"""

import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import os
import warnings

# 抑制pandas警告信息
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings('ignore', message='.*SettingWithCopyWarning.*')

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

def get_data_with_retry(func, max_retries=5, retry_delay=2, extended_wait=True, **kwargs):
    """
    带有重试机制的数据获取函数
    
    参数:
    func: 要调用的函数
    max_retries: 最大重试次数
    retry_delay: 初始重试延迟(秒)
    extended_wait: 是否在多次重试失败后启用长时间等待再尝试
    kwargs: 传递给func的参数
    
    返回:
    func的返回结果或空DataFrame
    """
    for attempt in range(max_retries):
        try:
            result = func(**kwargs)
            # 检查结果是否为空DataFrame
            if isinstance(result, pd.DataFrame) and result.empty:
                if attempt == max_retries - 1:
                    if extended_wait:
                        # 如果所有重试都失败且启用了长时间等待，则等待1分钟后再试一次
                        print(f"尝试{max_retries}次后获取到空数据，等待60秒后进行最后一次尝试...")
                        time.sleep(60)  # 等待1分钟
                        try:
                            result = func(**kwargs)
                            if not (isinstance(result, pd.DataFrame) and result.empty):
                                print("在额外等待后成功获取数据")
                                return result
                        except Exception as e:
                            print(f"额外等待后尝试仍然失败: {e}")
                    
                    print(f"尝试{max_retries}次后获取到空数据")
                    return pd.DataFrame()
                    
                print(f"第{attempt+1}次请求返回空数据，{retry_delay:.1f}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # 指数退避策略
                continue
            
            return result
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                Exception) as e:
            if attempt == max_retries - 1:
                if extended_wait:
                    # 如果所有重试都失败且启用了长时间等待，则等待1分钟后再试一次
                    print(f"尝试{max_retries}次后仍然失败，等待60秒后进行最后一次尝试...")
                    time.sleep(60)  # 等待1分钟
                    try:
                        result = func(**kwargs)
                        print("在额外等待后成功获取数据")
                        return result
                    except Exception as e:
                        print(f"额外等待后尝试仍然失败: {e}")
                
                print(f"尝试{max_retries}次后仍然失败: {e}")
                return pd.DataFrame()
                
            print(f"第{attempt+1}次请求失败: {e}，{retry_delay:.1f}秒后重试...")
            time.sleep(retry_delay)
            retry_delay *= 1.5  # 指数退避策略
    
    return pd.DataFrame()

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

def get_stock_list(pro):
    """
    获取A股股票列表
    
    参数:
    pro: tushare pro接口
    
    返回:
    DataFrame: A股股票基本信息
    """
    print("获取A股股票列表...")
    try:
        # 获取所有上市股票
        df_stocks = get_data_with_retry(pro.stock_basic, exchange='', list_status='L', 
                                    fields='ts_code,name,industry,market,area')
        
        if df_stocks.empty:
            print("获取股票列表失败")
            return pd.DataFrame()
        
        print(f"共获取 {len(df_stocks)} 支股票的基本信息")
        return df_stocks
    
    except Exception as e:
        print(f"获取股票列表时出错: {e}")
        return pd.DataFrame()

def get_stocks_moneyflow(pro, stock_list, trade_date):
    """
    获取多支股票的资金流向数据
    使用优化方法：一次性获取当天所有股票的资金流向，然后筛选需要的股票
    
    参数:
    pro: tushare pro接口
    stock_list: 股票代码列表
    trade_date: 交易日期
    
    返回:
    DataFrame: 包含股票资金流向数据
    """
    print(f"获取 {trade_date} 日所有股票资金流向数据...")
    
    try:
        # 一次性获取当日所有股票的资金流向数据
        all_stocks_flow = get_data_with_retry(pro.moneyflow, trade_date=trade_date)
        
        if all_stocks_flow.empty:
            print(f"无法获取 {trade_date} 日所有股票的资金流向数据")
            return pd.DataFrame()
        
        print(f"成功获取 {len(all_stocks_flow)} 支股票的资金流向数据")
        
        # 如果提供了股票列表，筛选出需要的股票
        if stock_list:
            stock_set = set(stock_list)
            filtered_data = all_stocks_flow[all_stocks_flow['ts_code'].isin(stock_set)]
            print(f"在列表中找到 {len(filtered_data)}/{len(stock_list)} 支股票的资金流向数据")
            
            if len(filtered_data) == 0:
                print("警告: 未找到任何指定股票的资金流向数据，使用所有股票数据")
                filtered_data = all_stocks_flow
        else:
            # 如果没有提供股票列表，使用所有数据
            filtered_data = all_stocks_flow
        
        # 确保净流入金额列存在
        if 'net_mf_amount' in filtered_data.columns:
            filtered_data = filtered_data.copy()  # 创建副本避免警告
            filtered_data.loc[:, 'net_mf_amount'] = pd.to_numeric(filtered_data['net_mf_amount'], errors='coerce')
            filtered_data.loc[:, 'net_amount'] = filtered_data['net_mf_amount']
            print("已将net_mf_amount复制为net_amount以保持代码兼容性")
        elif 'buy_amount' in filtered_data.columns and 'sell_amount' in filtered_data.columns:
            filtered_data['net_amount'] = filtered_data['buy_amount'] - filtered_data['sell_amount']
            print("已计算net_amount (buy_amount - sell_amount)")
        
        # 获取股票名称等基本信息
        stock_basic_info = get_data_with_retry(pro.stock_basic, 
                                          fields='ts_code,name,industry,market,area',
                                          exchange='',
                                          list_status='L')
        
        if not stock_basic_info.empty:
            filtered_data = pd.merge(filtered_data, stock_basic_info, on=['ts_code'], how='left')
            print(f"已关联{len(filtered_data[~filtered_data['name'].isna()])}支股票的基本信息(名称、行业等)")
        
        return filtered_data
        
    except Exception as e:
        print(f"获取股票资金流向数据时出错: {e}")
        return pd.DataFrame()

def calculate_concentration_index(flow_df, top_percent=10):
    """
    计算资金集中度指标
    
    参数:
    flow_df: 所有股票的资金流向DataFrame
    top_percent: 前多少百分比的股票，默认为10%
    
    返回:
    float: 资金集中度指标（前top_percent%股票的资金净流入占总净流入的比例）
    """
    if flow_df.empty:
        return None
    
    # 确保数据有净流入列
    if 'net_amount' not in flow_df.columns:
        if 'buy_amount' in flow_df.columns and 'sell_amount' in flow_df.columns:
            flow_df['net_amount'] = flow_df['buy_amount'] - flow_df['sell_amount']
        else:
            print("资金流向数据不包含必要的列，无法计算资金集中度指标")
            return None
    
    # 将净流入转换为数值类型
    flow_df['net_amount'] = pd.to_numeric(flow_df['net_amount'], errors='coerce')
    
    # 按净流入金额降序排序
    sorted_df = flow_df.sort_values('net_amount', ascending=False)
    
    # 计算前top_percent%的股票数量
    top_count = int(len(sorted_df) * top_percent / 100)
    
    if top_count == 0:
        print("股票数量太少，无法计算前10%")
        return None
    
    # 计算前10%的净流入总额
    top_net_inflow = sorted_df.iloc[:top_count]['net_amount'].sum()
    
    # 计算所有股票的净流入总额（只考虑净流入为正的股票）
    total_net_inflow = sorted_df[sorted_df['net_amount'] > 0]['net_amount'].sum()
    
    # 计算资金集中度
    if total_net_inflow > 0:
        concentration_index = (top_net_inflow / total_net_inflow) * 100
        return concentration_index
    else:
        print("总净流入为0或负值，无法计算资金集中度指标")
        return None

def analyze_capital_concentration(token=None, days=20, top_percent=10, save_fig=True, show_fig=True, date=None):
    """
    计算过去N个交易日的资金集中度指标
    
    参数:
    token: tushare API token，若为None则使用默认token
    days: 要分析的天数，默认为20
    top_percent: 前多少百分比的股票，默认为10%
    save_fig: 是否保存图片，默认为True
    show_fig: 是否显示图表，默认为True
    date: 结束日期，格式为'YYYYMMDD'，若为None则使用当前日期
    
    返回:
    DataFrame: 包含每日资金集中度指标的DataFrame
    """
    # 设置默认token
    if token is None:
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
    
    # 初始化tushare API
    pro = ts.pro_api(token)
    
    # 获取当前日期和N天前的日期
    if date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    else:
        end_date = date
        
    print(f"分析结束日期: {end_date}")
    
    start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=days*2)).strftime('%Y%m%d')  # 多取一些交易日，确保有足够的数据
    
    # 获取交易日期列表
    trade_dates = get_trade_dates(pro, start_date, end_date)
    if not trade_dates:
        print("获取交易日期失败")
        return pd.DataFrame()
    
    # 只保留最近N个交易日
    recent_trade_dates = trade_dates[-days:] if len(trade_dates) >= days else trade_dates
    
    print(f"分析以下{len(recent_trade_dates)}个交易日的资金集中度指标:")
    for date in recent_trade_dates:
        print(f"- {date}")
    
    # 获取A股股票列表
    stock_list = get_stock_list(pro)
    if stock_list.empty:
        print("获取股票列表失败，无法继续分析")
        return pd.DataFrame()
    
    # 计算每个交易日的资金集中度指标
    concentration_data = []
    
    for trade_date in recent_trade_dates:
        print(f"\n分析 {trade_date} 的资金集中度指标...")
        
        # 获取所有股票的资金流向数据
        flow_data = get_stocks_moneyflow(pro, stock_list['ts_code'].tolist(), trade_date)
        
        if flow_data.empty:
            print(f"获取 {trade_date} 资金流向数据失败，跳过该日期")
            continue
        
        # 计算资金集中度指标
        concentration_index = calculate_concentration_index(flow_data, top_percent)
        
        if concentration_index is not None:
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            concentration_data.append({
                'trade_date': trade_date,
                'formatted_date': formatted_date,
                'concentration_index': concentration_index
            })
            
            level = "高" if concentration_index >= 80 else "中" if concentration_index >= 60 else "低"
            print(f"{trade_date} 资金集中度指标: {concentration_index:.2f}% (集中度: {level})")
    
    # 创建DataFrame
    df_concentration = pd.DataFrame(concentration_data)
    
    if not df_concentration.empty:
        # 绘制折线图
        plot_concentration_index(df_concentration, top_percent, save_fig, show_fig)
    else:
        print("没有有效的资金集中度指标数据")
    
    return df_concentration

def plot_concentration_index(df_concentration, top_percent=10, save_fig=True, show_fig=True):
    """
    绘制资金集中度指标折线图
    
    参数:
    df_concentration: 包含每日资金集中度指标的DataFrame
    top_percent: 前多少百分比的股票，默认为10%
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    """
    if df_concentration.empty:
        print("没有数据可供绘图")
        return
    
    # 设置图表大小
    plt.figure(figsize=(16, 8))
    
    # 获取日期和指数数据
    dates = df_concentration['formatted_date'].tolist()
    indices = df_concentration['concentration_index'].tolist()
    
    # 绘制折线图
    plt.plot(dates, indices, marker='o', linestyle='-', linewidth=2, markersize=8, color='#F63366')
    
    # 添加背景色区域来表示集中度级别
    plt.axhspan(0, 60, alpha=0.2, color='green', label='低集中度区域')
    plt.axhspan(60, 80, alpha=0.2, color='yellow', label='中集中度区域')
    plt.axhspan(80, 100, alpha=0.2, color='red', label='高集中度区域')
    
    # 添加标题和标签
    plt.title(f'市场资金集中度指标（前{top_percent}%个股的资金净流入占比）', fontsize=18, pad=15)
    plt.xlabel('日期', fontsize=14, labelpad=10)
    plt.ylabel('资金集中度（%）', fontsize=14, labelpad=10)
    
    # 设置x轴标签
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # 添加网格线
    plt.grid(axis='both', linestyle='--', alpha=0.6)
    
    # 美化图表
    plt.gca().spines['top'].set_visible(False)  # 去掉上边框
    plt.gca().spines['right'].set_visible(False)  # 去掉右边框
    
    # 设置y轴范围
    plt.ylim(0, 100)
    
    # 添加警示线并标注
    plt.axhline(y=80, color='red', linestyle='--', alpha=0.8)
    plt.text(0, 82, '警戒线（80%）：超过此线表示市场资金高度集中', 
              ha='left', va='bottom', color='red', fontsize=10)
    
    # 添加平均线
    mean_value = np.mean(indices)
    plt.axhline(y=mean_value, color='blue', linestyle='--', alpha=0.8)
    plt.text(0, mean_value + 2, f'平均线（{mean_value:.2f}%）', 
              ha='left', va='bottom', color='blue', fontsize=10)
    
    # 添加数据标签
    for i, (date, value) in enumerate(zip(dates, indices)):
        plt.text(i, value + 2, f"{value:.1f}%", ha='center', va='bottom', fontsize=9)
    
    # 添加图例
    plt.legend(loc='upper left', frameon=True, fontsize=10)
    
    # 添加数据来源和日期
    plt.figtext(0.02, 0.02, f"数据来源: 同花顺 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                ha='left', fontsize=8, alpha=0.6)
    
    # 添加分析说明
    explanation_text = (
        "资金集中度指标说明：\n"
        f"1. 计算方法：前{top_percent}%个股的资金净流入占所有正向净流入的比例\n"
        "2. 指标含义：反映市场资金集中度，集中度越高说明市场情绪越分化\n"
        "3. 集中度水平：<60%低集中度，60%-80%中集中度，>80%高集中度"
    )
    plt.figtext(0.5, 0.02, explanation_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.2))
    
    # 优化布局
    plt.tight_layout(pad=2.0, rect=[0, 0.05, 1, 1])
    
    # 保存图片
    if save_fig:
        filename = f'capital_concentration_index_{datetime.now().strftime("%Y%m%d")}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"图表已保存为 {os.path.abspath(filename)}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()

if __name__ == "__main__":
    # 分析过去20个交易日的资金集中度指标
    df_concentration = analyze_capital_concentration(days=20, top_percent=10, save_fig=True, show_fig=True) 