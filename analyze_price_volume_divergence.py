#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
量价背离指数计算模块

量价背离指数：筛选当日涨幅前50但资金净流出的个股占比，反应市场虚涨风险
- 占比大于30%警示回调可能性
- 计算过去20个交易日每天的量价背离指数
- 分别拉取每天全市场涨幅前50的股票，并拉取他们的资金净流入/流出情况，计算量价背离指数
- 将过去20天的数据画折线图展示
"""

import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import os

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

def get_top_gainers(pro, trade_date, top_n=50):
    """
    获取指定日期涨幅前N的股票
    
    参数:
    pro: tushare pro接口
    trade_date: 交易日期，格式为'YYYYMMDD'
    top_n: 前N只股票，默认为50
    
    返回:
    DataFrame: 涨幅前N的股票信息
    """
    print(f"获取{trade_date}涨幅前{top_n}的股票...")
    
    try:
        # 获取当日所有股票的行情数据
        df_daily = get_data_with_retry(pro.daily, trade_date=trade_date)
        
        if df_daily.empty:
            print(f"获取{trade_date}行情数据失败")
            return pd.DataFrame()
        
        # 获取股票名称
        df_basic = get_data_with_retry(pro.stock_basic, exchange='', list_status='L', 
                                  fields='ts_code,name,industry,market')
        
        if not df_basic.empty:
            # 合并股票信息
            df = pd.merge(df_daily, df_basic, on='ts_code', how='left')
        else:
            df = df_daily
        
        # 按涨跌幅降序排序
        df = df.sort_values('pct_chg', ascending=False)
        
        # 获取涨幅前N的股票
        top_gainers = df.head(top_n)
        
        print(f"成功获取{len(top_gainers)}只涨幅最高的股票")
        return top_gainers
    
    except Exception as e:
        print(f"获取涨幅前{top_n}股票时出错: {e}")
        return pd.DataFrame()

def get_stocks_moneyflow(pro, stock_list, trade_date):
    """
    获取多支股票的资金流向数据
    
    参数:
    pro: tushare pro接口
    stock_list: 股票代码列表
    trade_date: 交易日期
    
    返回:
    DataFrame: 包含股票资金流向数据
    """
    print(f"获取{len(stock_list)}支股票的资金流向数据...")
    
    all_data = []
    
    # 由于API限制，每次请求不超过50支股票
    batch_size = 50
    total_batches = (len(stock_list) + batch_size - 1) // batch_size
    
    for i in range(0, len(stock_list), batch_size):
        batch = stock_list[i:i + batch_size]
        current_batch = i // batch_size + 1
        print(f"获取第 {current_batch}/{total_batches} 批股票资金流向数据 ({len(batch)} 支)...")
        
        try:
            # 优先使用同花顺个股资金流向API
            df_flow_ths = get_data_with_retry(pro.moneyflow_ths, ts_code=','.join(batch), trade_date=trade_date)
            
            if not df_flow_ths.empty:
                all_data.append(df_flow_ths)
                continue
            
            # 如果同花顺数据API返回为空，回退到使用普通资金流向API
            df_flow = get_data_with_retry(pro.moneyflow, ts_code=','.join(batch), trade_date=trade_date)
            
            if not df_flow.empty:
                all_data.append(df_flow)
        
        except Exception as e:
            print(f"获取股票资金流向数据时出错: {e}")
    
    # 合并所有批次的数据
    if all_data:
        result_df = pd.concat(all_data)
        print(f"成功获取 {len(result_df)} 支股票的资金流向数据")
        return result_df
    else:
        return pd.DataFrame()

def calculate_divergence_index(top_gainers_df, flow_df):
    """
    计算量价背离指数
    
    参数:
    top_gainers_df: 涨幅前N的股票DataFrame
    flow_df: 资金流向DataFrame
    
    返回:
    float: 量价背离指数（净流出股票数量占比）
    """
    if top_gainers_df.empty or flow_df.empty:
        return None
    
    # 合并涨幅数据和资金流向数据
    if 'net_amount' in flow_df.columns:
        # 使用同花顺数据
        merged_df = pd.merge(top_gainers_df, flow_df[['ts_code', 'net_amount']], on='ts_code', how='left')
    elif 'buy_amount' in flow_df.columns and 'sell_amount' in flow_df.columns:
        # 使用普通资金流向数据
        flow_df['net_amount'] = flow_df['buy_amount'] - flow_df['sell_amount']
        merged_df = pd.merge(top_gainers_df, flow_df[['ts_code', 'net_amount']], on='ts_code', how='left')
    else:
        print("资金流向数据不包含必要的列，无法计算量价背离指数")
        return None
    
    # 计算净流出的股票数量
    merged_df['net_amount'] = pd.to_numeric(merged_df['net_amount'], errors='coerce')
    outflow_count = sum(merged_df['net_amount'] < 0)
    
    # 计算量价背离指数（净流出股票占比）
    total_count = len(merged_df)
    if total_count > 0:
        divergence_index = outflow_count / total_count * 100
        return divergence_index
    else:
        return None

def analyze_price_volume_divergence(token=None, days=20, top_n=50, save_fig=True, show_fig=True, date=None):
    """
    计算过去N个交易日的量价背离指数
    
    参数:
    token: tushare API token，若为None则使用默认token
    days: 要分析的天数，默认为20
    top_n: 每天分析涨幅前多少的股票，默认为50
    save_fig: 是否保存图片，默认为True
    show_fig: 是否显示图表，默认为True
    date: 结束日期，格式为'YYYYMMDD'，若为None则使用当前日期
    
    返回:
    DataFrame: 包含每日量价背离指数的DataFrame
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
    
    print(f"分析以下{len(recent_trade_dates)}个交易日的量价背离指数:")
    for date in recent_trade_dates:
        print(f"- {date}")
    
    # 计算每个交易日的量价背离指数
    divergence_data = []
    
    for trade_date in recent_trade_dates:
        print(f"\n分析 {trade_date} 的量价背离指数...")
        
        # 获取涨幅前N的股票
        top_gainers = get_top_gainers(pro, trade_date, top_n)
        
        if top_gainers.empty:
            print(f"获取 {trade_date} 涨幅前{top_n}的股票失败，跳过该日期")
            continue
        
        # 获取这些股票的资金流向数据
        flow_data = get_stocks_moneyflow(pro, top_gainers['ts_code'].tolist(), trade_date)
        
        if flow_data.empty:
            print(f"获取 {trade_date} 资金流向数据失败，跳过该日期")
            continue
        
        # 计算量价背离指数
        divergence_index = calculate_divergence_index(top_gainers, flow_data)
        
        if divergence_index is not None:
            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
            divergence_data.append({
                'trade_date': trade_date,
                'formatted_date': formatted_date,
                'divergence_index': divergence_index
            })
            
            risk_level = "高" if divergence_index >= 30 else "中" if divergence_index >= 20 else "低"
            print(f"{trade_date} 量价背离指数: {divergence_index:.2f}% (风险水平: {risk_level})")
    
    # 创建DataFrame
    df_divergence = pd.DataFrame(divergence_data)
    
    if not df_divergence.empty:
        # 绘制折线图
        plot_divergence_index(df_divergence, save_fig, show_fig)
    else:
        print("没有有效的量价背离指数数据")
    
    return df_divergence

def plot_divergence_index(df_divergence, save_fig=True, show_fig=True):
    """
    绘制量价背离指数折线图
    
    参数:
    df_divergence: 包含每日量价背离指数的DataFrame
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    """
    if df_divergence.empty:
        print("没有数据可供绘图")
        return
    
    # 设置图表大小
    plt.figure(figsize=(16, 8))
    
    # 获取日期和指数数据
    dates = df_divergence['formatted_date'].tolist()
    indices = df_divergence['divergence_index'].tolist()
    
    # 绘制折线图
    plt.plot(dates, indices, marker='o', linestyle='-', linewidth=2, markersize=8, color='#1E88E5')
    
    # 添加背景色区域来表示风险级别
    plt.axhspan(0, 20, alpha=0.2, color='green', label='低风险区域')
    plt.axhspan(20, 30, alpha=0.2, color='yellow', label='中风险区域')
    plt.axhspan(30, 100, alpha=0.2, color='red', label='高风险区域')
    
    # 添加标题和标签
    plt.title('市场量价背离指数（涨幅前50股中资金净流出占比）', fontsize=18, pad=15)
    plt.xlabel('日期', fontsize=14, labelpad=10)
    plt.ylabel('量价背离指数（%）', fontsize=14, labelpad=10)
    
    # 设置x轴标签
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # 添加网格线
    plt.grid(axis='both', linestyle='--', alpha=0.6)
    
    # 美化图表
    plt.gca().spines['top'].set_visible(False)  # 去掉上边框
    plt.gca().spines['right'].set_visible(False)  # 去掉右边框
    
    # 设置y轴范围
    plt.ylim(0, max(100, max(indices) * 1.1))
    
    # 添加警示线并标注
    plt.axhline(y=30, color='red', linestyle='--', alpha=0.8)
    plt.text(0, 32, '警戒线（30%）：超过此线警示市场回调可能性增大', 
             ha='left', va='bottom', color='red', fontsize=10)
    
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
        "量价背离指数说明：\n"
        "1. 计算方法：涨幅前50只股票中资金净流出的股票占比\n"
        "2. 指标含义：反映市场虚涨风险，占比大于30%警示回调可能性增大\n"
        "3. 风险水平：<20%低风险，20%-30%中风险，>30%高风险"
    )
    plt.figtext(0.5, 0.02, explanation_text, ha='center', fontsize=9, 
                bbox=dict(facecolor='lightgray', alpha=0.2))
    
    # 优化布局
    plt.tight_layout(pad=2.0, rect=[0, 0.05, 1, 1])
    
    # 保存图片
    if save_fig:
        filename = f'price_volume_divergence_index_{datetime.now().strftime("%Y%m%d")}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"图表已保存为 {os.path.abspath(filename)}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()

if __name__ == "__main__":
    # 分析过去20个交易日的量价背离指数
    df_divergence = analyze_price_volume_divergence(days=20, top_n=50, save_fig=True, show_fig=True) 