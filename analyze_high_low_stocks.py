#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新高新低股票数分析

功能：
1. 统计每天创52周新高和新低的股票数量
2. 统计每天创26周新高和新低的股票数量
3. 分别生成52周和26周新高新低趋势图
4. 支持数据库存储，实现历史数据一次性拉取和每日增量更新
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tushare as ts
from datetime import datetime, timedelta
import time
import argparse
from matplotlib.ticker import MaxNLocator
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('high_low_analysis')

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

# 导入数据库工具模块
try:
    from db_utils import (save_high_low_stats, get_high_low_stats, 
                        get_latest_trade_date_in_db, save_stock_daily_data,
                        get_stock_daily_data, update_db_status, get_db_status,
                        clear_old_stock_data, recreate_tables)
except ImportError:
    logger.error("未能导入数据库工具模块，请确保db_utils.py文件存在")
    # 定义空函数，防止程序崩溃
    def save_high_low_stats(*args, **kwargs): return False
    def get_high_low_stats(*args, **kwargs): return pd.DataFrame()
    def get_latest_trade_date_in_db(*args, **kwargs): return None
    def save_stock_daily_data(*args, **kwargs): return 0
    def get_stock_daily_data(*args, **kwargs): return pd.DataFrame()
    def update_db_status(*args, **kwargs): pass
    def get_db_status(*args, **kwargs): return None
    def clear_old_stock_data(*args, **kwargs): return 0
    def recreate_tables(*args, **kwargs): return False

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
        logger.error(f"获取交易日期时出错: {e}")
        return []

def get_stock_price_data(pro, ts_code, start_date, end_date):
    """
    获取单只股票在指定日期范围内的价格数据，优先从数据库获取，如果数据库中没有则从API获取
    
    参数:
    pro: tushare pro接口
    ts_code: 股票代码
    start_date: 开始日期，格式为'YYYYMMDD'
    end_date: 结束日期，格式为'YYYYMMDD'
    
    返回:
    pd.DataFrame: 股票价格数据
    """
    try:
        # 首先从数据库获取数据
        df_db = get_stock_daily_data(ts_code, start_date, end_date)
        
        # 如果数据库中有完整数据，直接返回
        if not df_db.empty and len(df_db) >= 20:  # 假设至少需要20天数据
            logger.debug(f"从数据库获取到股票 {ts_code} 的价格数据: {len(df_db)} 条记录")
            return df_db
        
        # 如果本次请求的日期范围已有过缓存标记，避免重复请求
        cache_key = f"cache_checked_{ts_code}_{start_date}_{end_date}"
        if hasattr(get_stock_price_data, cache_key):
            # 如果已请求过且数据库中无数据，直接返回空DataFrame
            return df_db
            
        # 从API获取数据
        logger.debug(f"从API获取股票 {ts_code} 的价格数据")
        df_api = get_data_with_retry(pro.daily, ts_code=ts_code, 
                                  start_date=start_date, end_date=end_date)
        
        # 标记本次请求已处理，避免重复请求
        setattr(get_stock_price_data, cache_key, True)
        
        # 如果获取到数据，保存到数据库 (只有上交所或深交所的股票才缓存)
        if not df_api.empty and (ts_code.endswith('.SH') or ts_code.endswith('.SZ')):
            save_stock_daily_data(df_api)
            
        return df_api
    except Exception as e:
        logger.error(f"获取股票 {ts_code} 的价格数据时出错: {e}")
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
        logger.error(f"获取股票列表时出错: {e}")
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
    logger.info(f"分析 {trade_date} 的{week_count}周新高新低...")
    
    # 计算week_count周对应的天数（约等于week_count * 7）
    days = week_count * 7
    
    # 计算开始日期
    date_obj = datetime.strptime(trade_date, '%Y%m%d')
    start_date = (date_obj - timedelta(days=days)).strftime('%Y%m%d')
    
    # 缓存日期，避免对同一天重复处理
    cache_key = f"daily_data_{trade_date}"
    if hasattr(calculate_high_low_for_date, cache_key):
        daily_data = getattr(calculate_high_low_for_date, cache_key)
    else:
        # 获取当日行情数据
        daily_data = get_data_with_retry(pro.daily, trade_date=trade_date)
        if daily_data.empty:
            logger.warning(f"获取 {trade_date} 行情数据失败")
            return 0, 0
        # 缓存到函数属性中
        setattr(calculate_high_low_for_date, cache_key, daily_data)
    
    high_count = 0
    low_count = 0
    
    # 设置进度计数器
    total_stocks = len(all_stocks)
    processed_stocks = 0
    
    # 批处理策略：每次处理批量股票，减少输出日志频率
    batch_size = 100
    
    # 对于每只股票，检查是否创新高/新低
    for i in range(0, total_stocks, batch_size):
        batch_stocks = all_stocks.iloc[i:i+batch_size]
        
        # 更新进度
        processed_stocks += len(batch_stocks)
        logger.info(f"处理进度: {processed_stocks}/{total_stocks} ({processed_stocks/total_stocks*100:.1f}%)")
        
        for _, stock in batch_stocks.iterrows():
            ts_code = stock['ts_code']
            
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
            
            # 计算历史最高收盘价和最低收盘价
            hist_high_close = hist_data['close'].max()
            hist_low_close = hist_data['close'].min()
            
            # 判断是否创新高或新低
            # 新高：当日收盘价严格大于历史最高收盘价
            # 新低：当日收盘价严格小于历史最低收盘价
            if current_close > hist_high_close:
                high_count += 1
            if current_close < hist_low_close:
                low_count += 1
    
    logger.info(f"{trade_date} {week_count}周新高数量: {high_count}, 新低数量: {low_count}")
    return high_count, low_count

def initial_data_load(pro, end_date, days=90, rebuild_db=False):
    """
    初始加载历史数据到数据库
    
    参数:
    pro: tushare pro接口
    end_date: 结束日期，格式为'YYYYMMDD'
    days: 要加载的历史天数，默认90天
    rebuild_db: 是否重建数据库，默认False
    
    返回:
    bool: 是否成功加载
    """
    logger.info(f"开始初始加载{days}天的历史新高新低数据...")
    
    # 如果需要，重建数据库
    if rebuild_db:
        logger.info("重建数据库表...")
        recreate_tables()
    
    # 获取所有A股股票
    all_stocks = get_all_stocks(pro)
    if all_stocks.empty:
        logger.error("无法获取股票列表")
        return False
    
    # 计算开始日期
    date_obj = datetime.strptime(end_date, '%Y%m%d')
    start_date = (date_obj - timedelta(days=days+10)).strftime('%Y%m%d')
    
    # 获取交易日列表
    trade_dates = get_trade_dates(pro, start_date, end_date)
    if not trade_dates:
        logger.error("无法获取交易日期")
        return False
    
    # 只取最近days天的交易日
    recent_trade_dates = trade_dates[-days:] if len(trade_dates) >= days else trade_dates
    
    # 记录处理开始时间
    start_time = time.time()
    
    # 处理每个交易日
    total_dates = len(recent_trade_dates)
    for i, trade_date in enumerate(recent_trade_dates, 1):
        logger.info(f"处理日期 {trade_date} ({i}/{total_dates})")
        
        # 计算新高新低数量
        high_52w, low_52w = calculate_high_low_for_date(pro, trade_date, 52, all_stocks)
        high_26w, low_26w = calculate_high_low_for_date(pro, trade_date, 26, all_stocks)
        
        # 保存到数据库
        save_high_low_stats(trade_date, high_52w, low_52w, high_26w, low_26w)
        
        # 显示进度和预计剩余时间
        elapsed = time.time() - start_time
        avg_time_per_date = elapsed / i
        remaining_dates = total_dates - i
        estimated_remaining = avg_time_per_date * remaining_dates
        
        logger.info(f"进度: {i}/{total_dates} ({i/total_dates*100:.1f}%), "
                   f"已用时间: {elapsed/60:.1f}分钟, "
                   f"预计剩余: {estimated_remaining/60:.1f}分钟")
    
    # 记录完成状态
    update_db_status('last_full_update', end_date)
    update_db_status('last_update', end_date)
    
    # 清理旧的股票日线数据
    clear_old_stock_data(days_to_keep=120)
    
    logger.info(f"初始数据加载完成，共处理了{total_dates}个交易日")
    return True

def incremental_update(pro, end_date):
    """
    增量更新最新的新高新低数据
    
    参数:
    pro: tushare pro接口
    end_date: 结束日期，格式为'YYYYMMDD'
    
    返回:
    bool: 是否成功更新
    """
    # A. 获取数据库中最新的交易日期
    last_date = get_latest_trade_date_in_db()
    if not last_date:
        logger.warning("数据库中没有历史数据，需要执行初始数据加载")
        return False
    
    # B. 获取上次更新日期到当前日期的所有交易日
    date_obj = datetime.strptime(last_date, '%Y%m%d')
    start_date = (date_obj + timedelta(days=1)).strftime('%Y%m%d')  # 从上次更新后的第一天开始
    
    logger.info(f"开始增量更新，上次更新日期: {last_date}, 当前日期: {end_date}")
    
    # 如果开始日期大于结束日期，表示已经是最新数据
    if start_date > end_date:
        logger.info("已经是最新数据，无需更新")
        return True
    
    # 获取需要更新的交易日列表
    trade_dates = get_trade_dates(pro, start_date, end_date)
    if not trade_dates:
        logger.info(f"从 {start_date} 到 {end_date} 没有交易日，无需更新")
        return True
    
    # 获取所有A股股票
    all_stocks = get_all_stocks(pro)
    if all_stocks.empty:
        logger.error("无法获取股票列表")
        return False
    
    # 更新每个交易日的数据
    total_dates = len(trade_dates)
    logger.info(f"需要更新 {total_dates} 个交易日的数据")
    
    for i, trade_date in enumerate(trade_dates, 1):
        logger.info(f"更新日期 {trade_date} ({i}/{total_dates})")
        
        # 计算新高新低数量
        high_52w, low_52w = calculate_high_low_for_date(pro, trade_date, 52, all_stocks)
        high_26w, low_26w = calculate_high_low_for_date(pro, trade_date, 26, all_stocks)
        
        # 保存到数据库
        save_high_low_stats(trade_date, high_52w, low_52w, high_26w, low_26w)
    
    # 更新最后更新日期
    update_db_status('last_update', end_date)
    
    # 清理旧的股票日线数据
    clear_old_stock_data(days_to_keep=120)
    
    logger.info(f"增量更新完成，共更新了{total_dates}个交易日的数据")
    return True

def prepare_high_low_data(pro, end_date, days=30, force_update=False, rebuild_db=False):
    """
    准备新高新低数据，根据需要执行初始加载或增量更新
    
    参数:
    pro: tushare pro接口
    end_date: 结束日期，格式为'YYYYMMDD'
    days: 要分析的天数
    force_update: 是否强制更新数据，即使数据库中已有最新数据
    rebuild_db: 是否重建数据库，默认False
    
    返回:
    tuple: (52周新高新低DataFrame, 26周新高新低DataFrame)
    """
    # 检查是否需要更新数据
    last_update = get_db_status('last_update')
    
    if force_update or not last_update or last_update < end_date:
        # 如果数据库中没有数据，执行初始加载
        if not last_update:
            logger.info("数据库中没有历史数据，执行初始数据加载")
            initial_data_load(pro, end_date, days=max(days, 90), rebuild_db=rebuild_db)  # 最少加载90天数据
        else:
            # 执行增量更新
            logger.info(f"执行增量更新，上次更新: {last_update}, 当前日期: {end_date}")
            incremental_update(pro, end_date)
    else:
        logger.info(f"数据库已是最新（{last_update}），无需更新")
    
    # 从数据库获取所需的数据
    df_all = get_high_low_stats(end_date=end_date, days=days)
    if df_all.empty:
        logger.error(f"数据库中没有找到{days}天的新高新低数据")
        return None, None
    
    # 将数据拆分为52周和26周的DataFrame
    df_52w = pd.DataFrame({
        'trade_date': df_all['trade_date'],
        'formatted_date': df_all['formatted_date'],
        'date': df_all['date'],
        'high_count': df_all['high_count_52w'],
        'low_count': df_all['low_count_52w'],
        'net_high': df_all['net_high_52w']
    })
    
    df_26w = pd.DataFrame({
        'trade_date': df_all['trade_date'],
        'formatted_date': df_all['formatted_date'],
        'date': df_all['date'],
        'high_count': df_all['high_count_26w'],
        'low_count': df_all['low_count_26w'],
        'net_high': df_all['net_high_26w']
    })
    
    return df_52w, df_26w

def analyze_high_low(token=None, end_date=None, days=30, force_update=False, rebuild_db=False, save_fig=True, show_fig=False):
    """
    分析指定时间段内的新高新低股票数量
    
    参数:
    token: Tushare API token
    end_date: 结束日期，格式为'YYYYMMDD'，若为None则使用最近交易日
    days: 要分析的交易日天数，默认30天
    force_update: 是否强制更新数据，即使数据库中已有最新数据
    rebuild_db: 是否重建数据库，默认False
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
    
    # 准备数据 - 从数据库获取或更新
    df_52w, df_26w = prepare_high_low_data(pro, end_date, days, force_update, rebuild_db=rebuild_db)
    
    if df_52w is None or df_26w is None:
        logger.error("数据准备失败，无法进行分析")
        return None, None
    
    # 绘制图表
    if not df_52w.empty:
        plot_high_low_chart(df_52w, 52, end_date, save_fig, show_fig)
    
    if not df_26w.empty:
        plot_high_low_chart(df_26w, 26, end_date, save_fig, show_fig)
    
    # 分析结果
    logger.info(f"新高新低分析完成，数据时间范围: {df_52w['formatted_date'].iloc[0]} 至 {df_52w['formatted_date'].iloc[-1]}")
    
    return df_52w, df_26w

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
        logger.info(f"{week_count}周新高新低趋势图已保存至: {fig_path}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()
    
    return fig_path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='分析新高新低股票数量')
    parser.add_argument('--token', '-t', type=str, help='Tushare API Token')
    parser.add_argument('--date', '-d', type=str, help='分析结束日期，格式为YYYYMMDD，默认为最近交易日')
    parser.add_argument('--days', '-n', type=int, default=30, help='分析的天数，默认30天')
    parser.add_argument('--show', '-s', action='store_true', help='是否显示图表')
    parser.add_argument('--force-update', '-f', action='store_true', help='强制更新数据')
    parser.add_argument('--rebuild-db', '-r', action='store_true', help='重建数据库')
    parser.add_argument('--init-days', '-i', type=int, help='初始加载的天数，仅当数据库为空时使用')
    
    args = parser.parse_args()
    
    # 使用指定的token或默认token
    token = args.token if args.token else TUSHARE_TOKEN
    
    logger.info(f"开始分析新高新低股票数量，结束日期: {args.date or '最近交易日'}, 分析天数: {args.days}天")
    
    # 分析新高新低
    df_52w, df_26w = analyze_high_low(
        token=token,
        end_date=args.date,
        days=args.days,
        force_update=args.force_update,
        rebuild_db=args.rebuild_db,
        save_fig=True,
        show_fig=args.show
    )
    
    if df_52w is not None and df_26w is not None:
        logger.info(f"新高新低分析完成，共计算了 {len(df_52w)} 个交易日的数据")

if __name__ == "__main__":
    main() 