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
import logging
import os
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('technical_indicators')

# 初始化tushare
TOKEN = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
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

def get_indicator_signals(data, indicators):
    """
    根据技术指标生成买入卖出信号
    
    参数:
        data (pd.DataFrame): 包含价格和指标数据的DataFrame
        indicators (list): 需要分析的指标列表，可包含'macd'、'rsi'等
        
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
    
    return signals

def get_stock_indicators(ts_code, start_date, end_date):
    """
    获取股票或指数的技术指标数据
    
    参数:
        ts_code (str): 股票或指数代码，格式如'000001.SZ'（股票）或'000001.SH'（指数）
        start_date (str): 开始日期，格式如'20230101'
        end_date (str): 结束日期，格式如'20231231'
        
    返回:
        pd.DataFrame: 包含价格和技术指标的DataFrame
    """
    max_retries = 3
    retry_delay = 2  # 初始延迟时间（秒）
    
    for retry in range(max_retries):
        try:
            # 根据代码判断是否为指数
            is_index = (ts_code.endswith('.SH') and ts_code.startswith('0')) or (ts_code.endswith('.SZ') and ts_code.startswith('39'))
            
            # 获取日线数据
            if is_index:
                logger.info(f"获取指数 {ts_code} 的日线数据，使用index_daily接口")
                df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            else:
                logger.info(f"获取个股 {ts_code} 的日线数据，使用daily接口")
                df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                logger.warning(f"未获取到{ts_code}的数据")
                return None
            
            df = df.sort_values('trade_date')
            
            # 将trade_date设置为索引
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            
            # 计算技术指标
            macd_data = calculate_macd(df)
            rsi_data = calculate_rsi(df)
            
            # 合并数据
            result = pd.concat([df, macd_data, rsi_data], axis=1)
            
            return result
        
        except Exception as e:
            if retry < max_retries - 1:
                logger.warning(f"获取{ts_code}数据出错（尝试 {retry+1}/{max_retries}）: {str(e)}，将在{retry_delay}秒后重试")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避策略
            else:
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
    
    # 使用中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']  # 优先使用的中文字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    fig = plt.figure(figsize=(14, 10))
    
    # 创建子图数量 - 总共3个（价格、MACD、RSI）
    plot_count = 3
    
    # 绘制K线图
    ax1 = plt.subplot2grid((plot_count, 1), (0, 0), rowspan=1)
    ax1.plot(data.index, data['close'], 'b-', label='收盘价')
    ax1.set_title(title or "技术指标分析")
    ax1.legend(loc='upper right')
    ax1.grid(True, linestyle='--', alpha=0.3)
    
    # 绘制MACD
    if all(col in data.columns for col in ['dif', 'dea', 'macd']):
        ax2 = plt.subplot2grid((plot_count, 1), (1, 0), rowspan=1, sharex=ax1)
        ax2.plot(data.index, data['dif'], 'r-', label='DIF')
        ax2.plot(data.index, data['dea'], 'g-', label='DEA')
        ax2.bar(data.index, data['macd'], color='blue', label='MACD')
        ax2.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax2.set_title("MACD指标")
        ax2.legend(loc='upper right')
        ax2.grid(True, linestyle='--', alpha=0.3)
    
    # 绘制RSI
    rsi_cols = [col for col in data.columns if col.startswith('rsi_')]
    if rsi_cols:
        ax3 = plt.subplot2grid((plot_count, 1), (2, 0), rowspan=1, sharex=ax1)
        for col in rsi_cols:
            ax3.plot(data.index, data[col], label=col.upper())
        
        # 标记超买超卖区域
        ax3.axhline(y=30, color='g', linestyle='--', alpha=0.5)
        ax3.axhline(y=70, color='r', linestyle='--', alpha=0.5)
        ax3.fill_between(data.index, 0, 30, color='g', alpha=0.1)
        ax3.fill_between(data.index, 70, 100, color='r', alpha=0.1)
        
        ax3.set_title("RSI指标")
        ax3.set_ylim(0, 100)
        ax3.legend(loc='upper right')
        ax3.grid(True, linestyle='--', alpha=0.3)
    
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
    
    # 当MACD和RSI同时发出底部信号时，标记为潜在底部
    result.loc[macd_bottom & rsi_bottom, 'prediction'] = 1  # 底部
    
    # 当MACD和RSI同时发出顶部信号时，标记为潜在顶部
    result.loc[macd_top & rsi_top, 'prediction'] = -1  # 顶部
    
    return result

def analyze_market_trend(market_code='000001.SH', start_date=None, end_date=None, days=90, save_fig=True, show_fig=False):
    """
    分析市场趋势并预测顶底
    
    参数:
        market_code (str): 市场指数代码，默认为上证指数
        start_date (str): 开始日期，格式如'20230101'
        end_date (str): 结束日期，格式如'20231231'
        days (int): 如果未提供开始日期，则使用最近days天的数据
        save_fig (bool): 是否保存图表到文件
        show_fig (bool): 是否显示图表
        
    返回:
        tuple: (pd.DataFrame, str) 分析结果和图表文件路径
    """
    from datetime import datetime, timedelta
    
    # 使用实际当前日期，而非可能出现的未来日期
    current_date = datetime.now()
    
    # 如果未提供结束日期，使用当前日期
    if end_date is None:
        end_date = current_date.strftime('%Y%m%d')
    else:
        # 确保结束日期不超过当前日期
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        if end_dt > current_date:
            end_date = current_date.strftime('%Y%m%d')
            logger.warning(f"结束日期超过当前日期，已调整为当前日期: {end_date}")
    
    # 如果未提供开始日期，使用结束日期前days天
    if start_date is None:
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        start_dt = end_dt - timedelta(days=days)
        start_date = start_dt.strftime('%Y%m%d')
    
    logger.info(f"获取 {market_code} 从 {start_date} 到 {end_date} 的数据")
    
    # 获取市场数据及指标
    market_data = get_stock_indicators(market_code, start_date, end_date)
    
    # 如果在线获取失败，尝试使用模拟数据
    if market_data is None:
        logger.warning("在线数据获取失败，使用模拟数据")
        market_data = create_mock_data(start_date, end_date)
    
    if market_data is None:
        logger.error(f"未能获取{market_code}从{start_date}到{end_date}的数据")
        return None, None
    
    # 预测顶底
    prediction = predict_market_tops_bottoms(market_data)
    
    # 生成图表
    fig = plot_technical_indicators(market_data, title=f"{market_code} 技术指标分析")
    
    # 在收盘价图上标记预测的顶底
    if prediction is not None and not prediction.empty and fig is not None:
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
    
    # 保存图表
    fig_path = None
    if save_fig and fig is not None:
        fig_path = f'market_technical_analysis_{end_date}.png'
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        logger.info(f"技术分析图表已保存到: {fig_path}")
    
    # 显示图表
    if show_fig and fig is not None:
        plt.show()
    else:
        plt.close(fig)
    
    return prediction, fig_path

def create_mock_data(start_date=None, end_date=None):
    """
    创建模拟数据集用于测试
    
    参数:
        start_date (str): 开始日期，格式如'20230101'
        end_date (str): 结束日期，格式如'20231231'
        
    返回:
        pd.DataFrame: 包含模拟数据的DataFrame
    """
    logger.info("创建模拟数据集用于测试")
    
    # 解析日期
    from datetime import datetime
    if start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
    else:
        end_dt = datetime.now()
        start_dt = datetime(end_dt.year, end_dt.month - 3, end_dt.day)
    
    # 生成日期范围
    dates = pd.date_range(start=start_dt, end=end_dt, freq='B')
    
    # 生成示例价格数据
    n = len(dates)
    np.random.seed(42)  # 设置随机种子以保证可重复性
    
    # 生成收盘价
    close = 3000 + np.cumsum(np.random.normal(0, 30, n))
    # 确保价格在合理范围内
    close = np.clip(close, 2800, 3600)
    
    # 生成开盘价、最高价、最低价
    open_price = close + np.random.normal(0, 20, n)
    high = np.maximum(close, open_price) + np.random.normal(10, 10, n)
    low = np.minimum(close, open_price) - np.random.normal(10, 10, n)
    
    # 创建DataFrame
    df = pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'vol': np.random.normal(3e8, 5e7, n),
        'amount': np.random.normal(3.5e8, 5e7, n)
    }, index=dates)
    
    # 计算技术指标
    macd_data = calculate_macd(df)
    rsi_data = calculate_rsi(df)
    
    # 合并数据
    result = pd.concat([df, macd_data, rsi_data], axis=1)
    return result

if __name__ == "__main__":
    import datetime
    
    # 测试函数
    end_date = datetime.datetime.now().strftime('%Y%m%d')
    prediction, fig_path = analyze_market_trend(
        market_code='000001.SH',
        days=90,
        end_date=end_date,
        save_fig=True,
        show_fig=True
    )
    
    if prediction is not None and not prediction.empty:
        # 输出最近的预测
        recent_predictions = prediction[prediction['prediction'] != 0].tail(5)
        if not recent_predictions.empty:
            print("\n最近的市场顶底预测:")
            for idx, row in recent_predictions.iterrows():
                signal = "底部" if row['prediction'] == 1 else "顶部"
                print(f"日期: {idx.strftime('%Y-%m-%d')}, 收盘价: {row['close']}, 预测: {signal}")
        else:
            print("\n最近没有检测到明显的市场顶底信号")
    
    print(f"\n技术分析图表已保存到: {fig_path}") 