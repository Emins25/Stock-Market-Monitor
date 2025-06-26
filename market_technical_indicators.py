#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技术指标计算模块
实现RSI技术指标的计算，用于市场顶底预测
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

def calculate_rsi(data, periods=[6, 14, 24]):
    """
    计算RSI指标（相对强弱指数）
    
    参数:
        data (pd.DataFrame): 包含收盘价的DataFrame，必须有'close'列
        periods (list): RSI周期列表，默认计算6、14、24周期
        
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
        
        # 计算平均上涨和平均下跌 (使用EMA计算方式更准确)
        avg_gain = df[f'gain_{period}'].ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = df[f'loss_{period}'].ewm(alpha=1/period, min_periods=period).mean()
        
        # 计算相对强度RS
        rs = avg_gain / avg_loss
        
        # 计算RSI
        result[f'rsi_{period}'] = 100 - (100 / (1 + rs))
    
    return result

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
            rsi_data = calculate_rsi(df)
            
            # 合并数据
            result = pd.concat([df, rsi_data], axis=1)
            
            return result
        
        except Exception as e:
            error_msg = str(e)
            # 检查是否是API访问频率限制错误
            if "每分钟最多访问该接口" in error_msg:
                logger.warning(f"遇到API访问频率限制: {error_msg}")
                logger.info(f"暂停60秒后继续...")
                time.sleep(60)  # 暂停60秒后继续尝试
                continue  # 不增加retry计数，直接重试
            
            if retry < max_retries - 1:
                logger.warning(f"获取{ts_code}数据出错（尝试 {retry+1}/{max_retries}）: {error_msg}，将在{retry_delay}秒后重试")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避策略
            else:
                logger.error(f"获取{ts_code}技术指标时出错: {error_msg}")
                return None

def plot_technical_indicators(data, title=None):
    """
    绘制RSI技术指标图表
    
    参数:
        data (pd.DataFrame): 包含价格和技术指标的DataFrame
        title (str): 图表标题
    """
    if data is None or data.empty:
        logger.warning("没有数据可供绘图")
        return None
    
    # 使用中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']  # 优先使用的中文字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    fig = plt.figure(figsize=(14, 10))
    
    # 创建子图 - K线图和RSI
    gs = plt.GridSpec(2, 1, height_ratios=[2, 1])
    
    # 绘制K线图（收盘价）
    ax1 = plt.subplot(gs[0])
    ax1.plot(data.index, data['close'], 'b-', linewidth=1.5, label='收盘价')
    
    # 添加20日和60日均线
    data['ma20'] = data['close'].rolling(window=20).mean()
    data['ma60'] = data['close'].rolling(window=60).mean()
    ax1.plot(data.index, data['ma20'], 'r-', linewidth=1, label='20日均线')
    ax1.plot(data.index, data['ma60'], 'g-', linewidth=1, label='60日均线')
    
    # 设置价格图表参数
    ax1.set_title(title or "上证指数RSI技术指标分析", fontsize=16)
    ax1.grid(True, linestyle='--', alpha=0.3)
    ax1.legend(loc='upper left')
    
    # 计算价格振幅，确保图表美观
    price_range = data['close'].max() - data['close'].min()
    price_min = data['close'].min() - price_range * 0.05
    price_max = data['close'].max() + price_range * 0.05
    ax1.set_ylim(price_min, price_max)
    
    # 设置右侧Y轴显示价格范围百分比
    ax1_right = ax1.twinx()
    base_price = data['close'].iloc[0]
    percentage_min = (price_min / base_price - 1) * 100
    percentage_max = (price_max / base_price - 1) * 100
    ax1_right.set_ylim(percentage_min, percentage_max)
    ax1_right.set_ylabel('涨跌幅 (%)', fontsize=12)
    
    # 绘制RSI
    ax2 = plt.subplot(gs[1], sharex=ax1)
    
    # 判断是否有RSI数据
    rsi_cols = [col for col in data.columns if col.startswith('rsi_')]
    if rsi_cols:
        for col in rsi_cols:
            period = col.split('_')[1]  # 提取周期数字
            ax2.plot(data.index, data[col], label=f'RSI({period})', linewidth=1.5)
        
        # 标记超买超卖区域
        ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5)
        ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5)
        ax2.fill_between(data.index, 0, 30, color='g', alpha=0.1)
        ax2.fill_between(data.index, 70, 100, color='r', alpha=0.1)
        
        # 添加标签
        ax2.text(data.index[-int(len(data)/10)], 72, '超买区域', color='r', fontsize=9)
        ax2.text(data.index[-int(len(data)/10)], 28, '超卖区域', color='g', fontsize=9)
        
        # 设置RSI图表参数
        ax2.set_ylim(0, 100)
        ax2.set_ylabel('RSI值', fontsize=12)
        ax2.grid(True, linestyle='--', alpha=0.3)
        ax2.legend(loc='upper left')
    
    # 美化日期显示
    # 根据数据量调整日期刻度
    date_range = (data.index.max() - data.index.min()).days
    if date_range > 180:
        ax1.xaxis.set_major_locator(plt.matplotlib.dates.MonthLocator(interval=1))
        ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m'))
    else:
        ax1.xaxis.set_major_locator(plt.matplotlib.dates.WeekdayLocator(interval=2))
        ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m-%d'))
    
    # 添加注释说明RSI的使用方法
    note_text = (
        "RSI使用方法:\n"
        "1. RSI>70为超买区域，可能预示顶部形成\n"
        "2. RSI<30为超卖区域，可能预示底部形成\n"
        "3. 价格创新高但RSI未创新高（顶背离）可能信号顶部\n"
        "4. 价格创新低但RSI未创新低（底背离）可能信号底部"
    )
    plt.figtext(0.02, 0.02, note_text, fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
    
    # 寻找并标记RSI背离点
    mark_divergence(data, ax1, ax2)
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)  # 为底部注释留出空间
    
    return fig

def mark_divergence(data, price_ax, rsi_ax):
    """
    标记价格与RSI的背离点
    
    参数:
        data: 包含价格和RSI的DataFrame
        price_ax: 价格子图
        rsi_ax: RSI子图
    """
    if data is None or data.empty or len(data) < 30:
        return
    
    # 使用14天RSI
    rsi_col = 'rsi_14' if 'rsi_14' in data.columns else None
    if rsi_col is None:
        return
    
    # 计算20日滚动窗口的最高价和最低价
    window = 20
    data['price_high'] = data['close'].rolling(window=window).max()
    data['price_low'] = data['close'].rolling(window=window).min()
    data['rsi_high'] = data[rsi_col].rolling(window=window).max()
    data['rsi_low'] = data[rsi_col].rolling(window=window).min()
    
    # 找出潜在的顶背离点
    top_divergence = []
    for i in range(window, len(data)-1):
        # 如果当前价格接近20日高点，但RSI明显低于之前高点
        if (data['close'].iloc[i] > data['close'].iloc[i-1] and 
            data['close'].iloc[i] > 0.98 * data['price_high'].iloc[i] and
            data[rsi_col].iloc[i] < 0.95 * data['rsi_high'].iloc[i-window:i].max() and
            data[rsi_col].iloc[i] > 65):  # RSI需要在高位
            top_divergence.append(i)
    
    # 找出潜在的底背离点
    bottom_divergence = []
    for i in range(window, len(data)-1):
        # 如果当前价格接近20日低点，但RSI明显高于之前低点
        if (data['close'].iloc[i] < data['close'].iloc[i-1] and 
            data['close'].iloc[i] < 1.02 * data['price_low'].iloc[i] and
            data[rsi_col].iloc[i] > 1.05 * data['rsi_low'].iloc[i-window:i].min() and
            data[rsi_col].iloc[i] < 35):  # RSI需要在低位
            bottom_divergence.append(i)
    
    # 标记顶背离点
    for i in top_divergence:
        price_ax.scatter(data.index[i], data['close'].iloc[i], 
                     color='red', marker='v', s=100, zorder=5)
        price_ax.text(data.index[i], data['close'].iloc[i]*1.02, 
                   '顶背离', color='red', fontsize=10, ha='center')
    
    # 标记底背离点
    for i in bottom_divergence:
        price_ax.scatter(data.index[i], data['close'].iloc[i], 
                     color='green', marker='^', s=100, zorder=5)
        price_ax.text(data.index[i], data['close'].iloc[i]*0.98, 
                   '底背离', color='green', fontsize=10, ha='center')

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
    
    # 生成分析结果
    prediction = analyze_rsi_signals(market_data)
    
    # 生成图表
    fig = plot_technical_indicators(market_data, title=f"{market_code} RSI技术指标分析")
    
    # 保存图表
    fig_path = None
    if save_fig and fig is not None:
        fig_path = f'market_rsi_analysis_{end_date}.png'
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        logger.info(f"RSI技术分析图表已保存到: {fig_path}")
    
    # 显示图表
    if show_fig and fig is not None:
        plt.show()
    else:
        plt.close(fig)
    
    return prediction, fig_path

def analyze_rsi_signals(data):
    """
    基于RSI指标分析市场信号
    
    参数:
        data (pd.DataFrame): 包含价格和RSI指标的DataFrame
        
    返回:
        pd.DataFrame: 包含信号的DataFrame
    """
    if data is None or data.empty:
        logger.warning("没有数据可供分析")
        return None
    
    # 确保数据包含所需指标
    rsi_col = 'rsi_14' if 'rsi_14' in data.columns else None
    if rsi_col is None:
        logger.warning("数据中缺少RSI_14指标")
        return None
    
    # 初始化结果DataFrame
    result = pd.DataFrame(index=data.index)
    result['close'] = data['close']
    result['signal'] = 0  # 0代表中性，1代表底部信号，-1代表顶部信号
    
    # 添加RSI指标
    result[rsi_col] = data[rsi_col]
    
    # 识别超买信号（RSI > 70）
    result.loc[data[rsi_col] > 70, 'signal'] = -1
    
    # 识别超卖信号（RSI < 30）
    result.loc[data[rsi_col] < 30, 'signal'] = 1
    
    # 寻找RSI背离点（价格与RSI方向不一致）
    window = 20
    for i in range(window, len(data)-1):
        # 价格创新高但RSI未跟进（顶背离）
        if (data['close'].iloc[i] > data['close'].iloc[i-window:i].max() and 
            data[rsi_col].iloc[i] < data[rsi_col].iloc[i-window:i].max() and
            data[rsi_col].iloc[i] > 65):
            result.iloc[i, result.columns.get_loc('signal')] = -2  # 强烈顶部信号
        
        # 价格创新低但RSI未跟进（底背离）
        if (data['close'].iloc[i] < data['close'].iloc[i-window:i].min() and 
            data[rsi_col].iloc[i] > data[rsi_col].iloc[i-window:i].min() and
            data[rsi_col].iloc[i] < 35):
            result.iloc[i, result.columns.get_loc('signal')] = 2  # 强烈底部信号
    
    return result

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
    
    # 计算RSI指标
    rsi_data = calculate_rsi(df)
    
    # 合并数据
    result = pd.concat([df, rsi_data], axis=1)
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
        # 输出最近的信号
        recent_signals = prediction[prediction['signal'] != 0].tail(5)
        if not recent_signals.empty:
            print("\n最近的RSI市场信号:")
            for idx, row in recent_signals.iterrows():
                signal_type = "强烈底部" if row['signal'] == 2 else "底部" if row['signal'] == 1 else "强烈顶部" if row['signal'] == -2 else "顶部"
                print(f"日期: {idx.strftime('%Y-%m-%d')}, 收盘价: {row['close']:.2f}, RSI: {row['rsi_14']:.2f}, 信号: {signal_type}")
        else:
            print("\n最近没有检测到明显的RSI信号")
    
    print(f"\nRSI技术分析图表已保存到: {fig_path}") 