#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标计算模块
实现MACD、RSI、KDJ等技术指标的计算，用于市场顶底预测
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tushare as ts
from config import TOKEN
from logger import setup_logger

logger = setup_logger('technical_indicators')

# 初始化tushare
ts.set_token(TOKEN)
pro = ts.pro_api()

def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    """
    计算MACD指标
    
    参数:
        data (pd.DataFrame): 包含收盘价的DataFrame，必须有'close'列
        fast_period (int): 快线周期
        slow_period (int): 慢线周期
        signal_period (int): 信号线周期
        
    返回:
        pd.DataFrame: 包含MACD指标的DataFrame(DIF, DEA, MACD)
    """
    if 'close' not in data.columns:
        raise ValueError("输入数据必须包含'close'列")
    
    # 复制数据，避免修改原始数据
    df = data.copy()
    
    # 计算EMA
    df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    # 计算DIF (DIFF)
    df['dif'] = df['ema_fast'] - df['ema_slow']
    
    # 计算DEA (MACD Signal)
    df['dea'] = df['dif'].ewm(span=signal_period, adjust=False).mean()
    
    # 计算柱状图 (MACD Histogram)
    df['macd'] = (df['dif'] - df['dea']) * 2
    
    return df[['dif', 'dea', 'macd']]

def calculate_rsi(data, periods=[6, 12, 24]):
    """
    计算RSI指标
    
    参数:
        data (pd.DataFrame): 包含收盘价的DataFrame，必须有'close'列
        periods (list): RSI周期列表，默认计算6、12、24周期
        
    返回:
        pd.DataFrame: 包含不同周期RSI指标的DataFrame
    """
    if 'close' not in data.columns:
        raise ValueError("输入数据必须包含'close'列")
    
    # 复制数据，避免修改原始数据
    df = data.copy()
    
    # 计算价格变化
    df['price_diff'] = df['close'].diff()
    
    # 初始化结果DataFrame
    result = pd.DataFrame(index=df.index)
    
    # 计算每个周期的RSI
    for period in periods:
        # 分别计算上涨和下跌
        df[f'gain_{period}'] = df['price_diff'].clip(lower=0)
        df[f'loss_{period}'] = -df['price_diff'].clip(upper=0)
        
        # 计算平均上涨和平均下跌
        avg_gain = df[f'gain_{period}'].rolling(window=period).mean()
        avg_loss = df[f'loss_{period}'].rolling(window=period).mean()
        
        # 计算相对强度RS
        rs = avg_gain / avg_loss
        
        # 计算RSI
        result[f'rsi_{period}'] = 100 - (100 / (1 + rs))
    
    return result

def calculate_kdj(data, n=9, m1=3, m2=3):
    """
    计算KDJ指标
    
    参数:
        data (pd.DataFrame): 包含OHLC数据的DataFrame，必须有'high'、'low'和'close'列
        n (int): RSV计算周期
        m1 (int): K值平滑因子
        m2 (int): D值平滑因子
        
    返回:
        pd.DataFrame: 包含KDJ指标的DataFrame
    """
    if not all(col in data.columns for col in ['high', 'low', 'close']):
        raise ValueError("输入数据必须包含'high'、'low'和'close'列")
    
    # 复制数据，避免修改原始数据
    df = data.copy()
    
    # 计算n日内的最低价和最高价
    low_n = df['low'].rolling(window=n).min()
    high_n = df['high'].rolling(window=n).max()
    
    # 计算RSV
    rsv = 100 * (df['close'] - low_n) / (high_n - low_n)
    
    # 计算K值、D值和J值
    k = pd.Series(0.0, index=df.index)
    d = pd.Series(0.0, index=df.index)
    
    for i in range(len(df)):
        if i == 0:
            k[i] = 50
            d[i] = 50
        else:
            k[i] = (m1 - 1) * k[i-1] / m1 + rsv[i] / m1
            d[i] = (m2 - 1) * d[i-1] / m2 + k[i] / m2
    
    j = 3 * k - 2 * d
    
    # 结果DataFrame
    result = pd.DataFrame({'k': k, 'd': d, 'j': j}, index=df.index)
    return result

def get_indicator_signals(data, indicators):
    """
    根据技术指标生成买入卖出信号
    
    参数:
        data (pd.DataFrame): 包含价格和指标数据的DataFrame
        indicators (list): 需要分析的指标列表，可包含'macd'、'rsi'、'kdj'等
        
    返回:
        pd.DataFrame: 包含买入卖出信号的DataFrame
    """
    signals = pd.DataFrame(index=data.index)
    signals['signal'] = 0  # 0表示无信号，1表示买入信号，-1表示卖出信号
    
    # MACD信号
    if 'macd' in indicators and all(col in data.columns for col in ['dif', 'dea']):
        # MACD金叉：DIF从下向上穿越DEA
        signals.loc[(data['dif'] > data['dea']) & (data['dif'].shift(1) <= data['dea'].shift(1)), 'macd_signal'] = 1
        
        # MACD死叉：DIF从上向下穿越DEA
        signals.loc[(data['dif'] < data['dea']) & (data['dif'].shift(1) >= data['dea'].shift(1)), 'macd_signal'] = -1
    
    # RSI信号
    if 'rsi' in indicators and 'rsi_14' in data.columns:
        # RSI超买
        signals.loc[data['rsi_14'] > 70, 'rsi_signal'] = -1
        
        # RSI超卖
        signals.loc[data['rsi_14'] < 30, 'rsi_signal'] = 1
    
    # KDJ信号
    if 'kdj' in indicators and all(col in data.columns for col in ['k', 'd']):
        # KDJ金叉：K线从下向上穿越D线
        signals.loc[(data['k'] > data['d']) & (data['k'].shift(1) <= data['d'].shift(1)), 'kdj_signal'] = 1
        
        # KDJ死叉：K线从上向下穿越D线
        signals.loc[(data['k'] < data['d']) & (data['k'].shift(1) >= data['d'].shift(1)), 'kdj_signal'] = -1
    
    return signals

def get_stock_indicators(ts_code, start_date, end_date):
    """
    获取股票的技术指标数据
    
    参数:
        ts_code (str): 股票代码，格式如'000001.SZ'
        start_date (str): 开始日期，格式如'20230101'
        end_date (str): 结束日期，格式如'20231231'
        
    返回:
        pd.DataFrame: 包含价格和技术指标的DataFrame
    """
    try:
        # 获取日线数据
        df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        df = df.sort_values('trade_date')
        
        if df.empty:
            logger.warning(f"未获取到{ts_code}的数据")
            return None
        
        # 计算技术指标
        macd_data = calculate_macd(df)
        rsi_data = calculate_rsi(df)
        kdj_data = calculate_kdj(df)
        
        # 合并数据
        result = pd.concat([df, macd_data, rsi_data, kdj_data], axis=1)
        
        return result
    
    except Exception as e:
        logger.error(f"获取{ts_code}技术指标时出错: {str(e)}")
        return None

def plot_technical_indicators(data, title=None):
    """
    绘制技术指标图表
    
    参数:
        data (pd.DataFrame): 包含价格和技术指标的DataFrame
        title (str): 图表标题
    """
    if data is None or data.empty:
        logger.warning("没有数据可供绘图")
        return
    
    fig = plt.figure(figsize=(14, 12))
    
    # 绘制K线图
    ax1 = plt.subplot2grid((4, 1), (0, 0), rowspan=1)
    ax1.plot(data.index, data['close'], 'b-', label='收盘价')
    ax1.set_title(title or "技术指标分析")
    ax1.legend()
    
    # 绘制MACD
    if all(col in data.columns for col in ['dif', 'dea', 'macd']):
        ax2 = plt.subplot2grid((4, 1), (1, 0), rowspan=1, sharex=ax1)
        ax2.plot(data.index, data['dif'], 'r-', label='DIF')
        ax2.plot(data.index, data['dea'], 'g-', label='DEA')
        ax2.bar(data.index, data['macd'], color='b', label='MACD')
        ax2.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax2.set_title("MACD指标")
        ax2.legend()
    
    # 绘制RSI
    rsi_cols = [col for col in data.columns if col.startswith('rsi_')]
    if rsi_cols:
        ax3 = plt.subplot2grid((4, 1), (2, 0), rowspan=1, sharex=ax1)
        for col in rsi_cols:
            ax3.plot(data.index, data[col], label=col.upper())
        
        # 标记超买超卖区域
        ax3.axhline(y=30, color='g', linestyle='--', alpha=0.5)
        ax3.axhline(y=70, color='r', linestyle='--', alpha=0.5)
        ax3.fill_between(data.index, 0, 30, color='g', alpha=0.1)
        ax3.fill_between(data.index, 70, 100, color='r', alpha=0.1)
        
        ax3.set_title("RSI指标")
        ax3.set_ylim(0, 100)
        ax3.legend()
    
    # 绘制KDJ
    if all(col in data.columns for col in ['k', 'd', 'j']):
        ax4 = plt.subplot2grid((4, 1), (3, 0), rowspan=1, sharex=ax1)
        ax4.plot(data.index, data['k'], 'b-', label='K')
        ax4.plot(data.index, data['d'], 'g-', label='D')
        ax4.plot(data.index, data['j'], 'r-', label='J')
        
        # 标记超买超卖区域
        ax4.axhline(y=20, color='g', linestyle='--', alpha=0.5)
        ax4.axhline(y=80, color='r', linestyle='--', alpha=0.5)
        ax4.fill_between(data.index, 0, 20, color='g', alpha=0.1)
        ax4.fill_between(data.index, 80, 100, color='r', alpha=0.1)
        
        ax4.set_title("KDJ指标")
        ax4.legend()
    
    plt.tight_layout()
    return fig

def predict_market_tops_bottoms(data):
    """
    基于技术指标预测市场顶部和底部
    
    参数:
        data (pd.DataFrame): 包含价格和技术指标的DataFrame
        
    返回:
        pd.DataFrame: 包含顶部和底部预测的DataFrame
    """
    if data is None or data.empty:
        logger.warning("没有数据可供分析")
        return None
    
    # 确保数据包含所需指标
    required_columns = ['close', 'dif', 'dea', 'macd']
    rsi_col = 'rsi_14' if 'rsi_14' in data.columns else None
    kdj_cols = ['k', 'd', 'j'] if all(col in data.columns for col in ['k', 'd', 'j']) else []
    
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        logger.warning(f"数据缺少以下必需列: {missing_columns}")
        return None
    
    # 初始化结果DataFrame
    result = pd.DataFrame(index=data.index)
    result['close'] = data['close']
    result['prediction'] = 0  # 0代表中性，1代表底部，-1代表顶部
    
    # MACD底部信号：金叉且MACD值为负但变大
    macd_bottom = ((data['dif'] > data['dea']) & 
                   (data['dif'].shift(1) <= data['dea'].shift(1)) & 
                   (data['macd'] < 0) & 
                   (data['macd'] > data['macd'].shift(1)))
    
    # MACD顶部信号：死叉且MACD值为正但变小
    macd_top = ((data['dif'] < data['dea']) & 
                (data['dif'].shift(1) >= data['dea'].shift(1)) & 
                (data['macd'] > 0) & 
                (data['macd'] < data['macd'].shift(1)))
    
    # RSI信号
    rsi_bottom = pd.Series(False, index=data.index)
    rsi_top = pd.Series(False, index=data.index)
    
    if rsi_col:
        # RSI底部信号：RSI低于30且回升
        rsi_bottom = (data[rsi_col] < 30) & (data[rsi_col] > data[rsi_col].shift(1))
        
        # RSI顶部信号：RSI高于70且下降
        rsi_top = (data[rsi_col] > 70) & (data[rsi_col] < data[rsi_col].shift(1))
    
    # KDJ信号
    kdj_bottom = pd.Series(False, index=data.index)
    kdj_top = pd.Series(False, index=data.index)
    
    if kdj_cols:
        # KDJ底部信号：K线和D线都低于20且金叉
        kdj_bottom = ((data['k'] < 20) & 
                      (data['d'] < 20) & 
                      (data['k'] > data['d']) & 
                      (data['k'].shift(1) <= data['d'].shift(1)))
        
        # KDJ顶部信号：K线和D线都高于80且死叉
        kdj_top = ((data['k'] > 80) & 
                   (data['d'] > 80) & 
                   (data['k'] < data['d']) & 
                   (data['k'].shift(1) >= data['d'].shift(1)))
    
    # 综合信号
    # 当至少两个指标同时发出底部信号时，标记为潜在底部
    potential_bottom = ((macd_bottom & rsi_bottom) | 
                        (macd_bottom & kdj_bottom) | 
                        (rsi_bottom & kdj_bottom))
    
    # 当至少两个指标同时发出顶部信号时，标记为潜在顶部
    potential_top = ((macd_top & rsi_top) | 
                     (macd_top & kdj_top) | 
                     (rsi_top & kdj_top))
    
    # 应用预测
    result.loc[potential_bottom, 'prediction'] = 1  # 底部
    result.loc[potential_top, 'prediction'] = -1    # 顶部
    
    return result

def analyze_market_trend(market_code='000001.SH', start_date=None, end_date=None, days=90):
    """
    分析市场趋势并预测顶底
    
    参数:
        market_code (str): 市场指数代码，默认为上证指数
        start_date (str): 开始日期，格式如'20230101'
        end_date (str): 结束日期，格式如'20231231'
        days (int): 如果未提供开始日期，则使用最近days天的数据
        
    返回:
        tuple: (pd.DataFrame, matplotlib.figure.Figure) 分析结果和图表
    """
    from datetime import datetime, timedelta
    
    # 如果未提供结束日期，使用当前日期
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    # 如果未提供开始日期，使用结束日期前days天
    if start_date is None:
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=days)
        start_date = start_dt.strftime('%Y%m%d')
    
    # 获取市场数据及指标
    market_data = get_stock_indicators(market_code, start_date, end_date)
    
    if market_data is None:
        logger.error(f"未能获取{market_code}从{start_date}到{end_date}的数据")
        return None, None
    
    # 预测顶底
    prediction = predict_market_tops_bottoms(market_data)
    
    # 生成图表
    fig = plot_technical_indicators(market_data, title=f"{market_code} 技术指标分析")
    
    # 在收盘价图上标记预测的顶底
    if prediction is not None and not prediction.empty:
        ax = fig.axes[0]
        
        # 标记底部
        bottoms = prediction[prediction['prediction'] == 1]
        if not bottoms.empty:
            ax.scatter(bottoms.index, bottoms['close'], marker='^', color='g', s=100, label='预测底部')
        
        # 标记顶部
        tops = prediction[prediction['prediction'] == -1]
        if not tops.empty:
            ax.scatter(tops.index, tops['close'], marker='v', color='r', s=100, label='预测顶部')
        
        ax.legend()
    
    return prediction, fig

if __name__ == "__main__":
    # 示例：分析上证指数最近90天的数据
    prediction, fig = analyze_market_trend(market_code='000001.SH', days=90)
    
    if fig:
        plt.savefig('market_technical_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    if prediction is not None and not prediction.empty:
        # 输出最近的预测
        recent_predictions = prediction[prediction['prediction'] != 0].tail(5)
        if not recent_predictions.empty:
            print("最近的市场顶底预测:")
            for idx, row in recent_predictions.iterrows():
                signal = "底部" if row['prediction'] == 1 else "顶部"
                print(f"日期: {idx}, 收盘价: {row['close']}, 预测: {signal}")
        else:
            print("最近没有检测到明显的市场顶底信号") 