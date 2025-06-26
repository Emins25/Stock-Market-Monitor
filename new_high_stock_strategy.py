#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新高股票选股策略

功能：
1. 每天筛选出创过去300个交易日新高的股票
2. 基于上一步筛选出150亿市值以上的股票
3. 基于上一步筛选出最近不是快速大幅上涨，而是更趋势性上涨的股票
4. 基于上一步筛选出目前的股价相对于之前的历史最高股价和历史最低股价，从底部反弹不超过40%的股票
5. 基于最终筛选出的股票，用爬虫的方法从韭研公社网站上获取相关的文章内容，利用DeepSeek大模型对文章内容进行分析，总结最近股价上涨的核心逻辑，辅助投资决策

数据来源：Tushare API
API key：284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736

韭研公社网站：https://www.jiuyangongshe.com/

DeepSeek API key：sk-4f3b471744e7491bb14159cd600409f2
"""

import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import json
import logging
import argparse
import os
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('new_high_stock_strategy')

# ============ 参数设置 ============
# Tushare token
TOKEN = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'

# DeepSeek API key
DEEPSEEK_API_KEY = 'sk-4f3b471744e7491bb14159cd600409f2'

# 策略参数
TRADE_DAYS = 300          # 最近300个交易日
MARKET_VALUE_THRESHOLD = 150 * 10000  # 150亿市值，单位：万元（1亿 = 10000万元）
RECENT_RETURN_THRESHOLD = 0.15      # 最近10日累计涨幅阈值：15%
RECENT_DAYS = 10           # 最近10日用于计算累计涨幅
REBOUND_THRESHOLD = 0.40   # 从底部反弹不超过40%
MIN_UPTREND_DAYS = 30      # 趋势判断的最小天数
MAX_THREADS = 10           # 并发请求的最大线程数

# 网络请求参数
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

# 韭研公社搜索URL
JIUYAN_SEARCH_URL = "https://www.jiuyangongshe.com/search"

# DeepSeek API URL
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 创建输出目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
            logger.warning(f"获取数据时出错 (尝试 {i+1}/{max_tries}): {error_msg}")
            
            # 检查是否是API访问频率限制错误
            if "每分钟最多访问该接口" in error_msg:
                logger.info(f"遇到API访问频率限制，暂停60秒后继续...")
                time.sleep(60)  # 暂停60秒后继续尝试
                continue  # 直接重试
            
            if i < max_tries - 1:  # 如果不是最后一次尝试，等待一段时间后重试
                sleep_time = (i + 1) * 2  # 指数退避
                logger.info(f"等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
    
    # 所有尝试都失败，返回空DataFrame
    logger.error("所有尝试都失败，返回空数据")
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
        logger.error(f"获取交易日期时出错: {e}")
        return []

def is_uptrend(prices, window=20, volatility_threshold=0.03, recent_volatility_threshold=0.02, use_adj=True):
    """
    判断是否为趋势性上涨，而不是暴涨
    
    参数:
    prices: DataFrame或Series，价格数据，如果是DataFrame则应包含前复权价格列
    window: 移动窗口大小
    volatility_threshold: 波动率阈值，默认为0.03(3%)
    recent_volatility_threshold: 最近五个交易日波动率阈值，默认为0.02(2%)
    use_adj: 是否使用前复权价格，默认为True
    
    返回:
    bool: 是否为趋势性上涨
    """
    # 如果prices是DataFrame，提取适当的价格列
    if isinstance(prices, pd.DataFrame):
        # 检查是否有前复权价格
        has_adj_price = 'close_adj' in prices.columns
        # 选择价格列
        if use_adj and has_adj_price:
            prices = prices['close_adj']
        else:
            prices = prices['close']
    
    if len(prices) < MIN_UPTREND_DAYS:
        return False
    
    # 计算移动平均线
    ma = prices.rolling(window=window).mean()
    
    # 计算最近一段时间的趋势斜率
    recent_ma = ma.dropna().tail(MIN_UPTREND_DAYS)
    if len(recent_ma) < MIN_UPTREND_DAYS:
        return False
    
    # 线性回归计算斜率
    x = np.arange(len(recent_ma))
    y = recent_ma.values
    slope, _ = np.polyfit(x, y, 1)
    
    # 计算整体波动率
    volatility = prices.pct_change().tail(MIN_UPTREND_DAYS).std()
    
    # 计算最近五个交易日的波动率
    recent_volatility = prices.pct_change().tail(5).std()
    
    # 判断趋势：斜率为正且波动率不高，且最近五日波动率不高
    return (slope > 0 and 
            volatility < volatility_threshold and 
            recent_volatility < recent_volatility_threshold)

def calculate_rebound_from_bottom(df, years=5):
    """
    计算当前价格从历史最低价反弹的相对位置，仅考虑最近几年的数据，使用前复权价格
    
    参数:
    df: 价格数据DataFrame，包含前复权价格
    years: 计算历史最高/最低点的年数范围，默认为5年
    
    返回:
    float: 相对位置，范围0-1，0表示在历史最低点，1表示在历史最高点
    """
    if df.empty or len(df) < 20:
        return 1.0  # 返回100%表示无法计算或数据不足
    
    # 检查是否包含前复权价格
    has_adj_price = all(col in df.columns for col in ['close_adj', 'high_adj', 'low_adj'])
    
    # 选择使用的价格列
    close_col = 'close_adj' if has_adj_price else 'close'
    high_col = 'high_adj' if has_adj_price else 'high'
    low_col = 'low_adj' if has_adj_price else 'low'
    
    # 计算过去5年对应的交易日数量（约250个交易日/年）
    days_in_period = min(years * 250, len(df))
    
    # 截取最近的数据
    recent_df = df.tail(days_in_period)
    
    # 使用前复权价格计算
    current_price = recent_df[close_col].iloc[-1]
    historical_low = recent_df[low_col].min()
    historical_high = recent_df[high_col].max()
    
    price_type = "前复权" if has_adj_price else "未复权"
    logger.debug(f"当前价格({price_type}): {current_price:.2f}, 历史最低({price_type}, 近{years}年): {historical_low:.2f}, "
                f"历史最高({price_type}, 近{years}年): {historical_high:.2f}")
    
    # 计算相对位置 = (当前价格 - 历史最低) / (历史最高 - 历史最低)
    if historical_high > historical_low:
        relative_position = (current_price - historical_low) / (historical_high - historical_low)
    else:
        relative_position = 1.0  # 避免除零
    
    # 仍然计算绝对反弹幅度，但仅用于日志记录
    absolute_rebound = (current_price - historical_low) / historical_low if historical_low > 0 else 0
    
    logger.debug(f"相对位置: {relative_position:.2f} (0-1范围), 绝对反弹幅度: {absolute_rebound:.2f} ({absolute_rebound*100:.1f}%)")
    
    # 返回相对位置作为反弹指标
    return relative_position

def search_articles(keyword):
    """
    在韭研公社搜索股票相关文章
    
    参数:
    keyword: 搜索关键词，通常是股票名称
    
    返回:
    list: 文章链接和标题列表
    """
    # 构造查询参数
    params = {"q": keyword}
    try:
        response = requests.get(JIUYAN_SEARCH_URL, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"搜索 {keyword} 时请求出错: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 根据网站HTML结构解析搜索结果
    articles = []
    results = soup.find_all("div", class_="search-result-item")
    for res in results:
        title_tag = res.find("a")
        if title_tag and title_tag.get("href"):
            title = title_tag.get_text(strip=True)
            link = title_tag["href"]
            # 如果链接不是绝对链接，则补全
            if not link.startswith("http"):
                link = "https://www.jiuyangongshe.com" + link
            articles.append({"title": title, "url": link})
    
    return articles

def fetch_article_content(url):
    """
    获取文章正文内容
    
    参数:
    url: 文章链接
    
    返回:
    str: 文章正文
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"获取文章 {url} 时出错: {e}")
        return ""
    
    soup = BeautifulSoup(response.text, "html.parser")
    # 假设正文在 <div class="article-content"> 中，实际需要根据网站结构调整
    content_div = soup.find("div", class_="article-content")
    if content_div:
        content = content_div.get_text(separator="\n", strip=True)
        return content
    return ""

def call_deepseek_api(text, stock_info):
    """
    调用DeepSeek API分析文章内容
    
    参数:
    text: 文章内容
    stock_info: 股票信息，包含股票名称、代码等
    
    返回:
    str: 分析结果
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    # 构建提示词
    prompt = f"""
    请分析以下关于股票 {stock_info['name']}({stock_info['ts_code']}) 的文章内容，总结该股近期上涨的核心逻辑。
    
    请考虑以下因素：
    1. 主要的业务增长点或转折点
    2. 行业政策变化的影响
    3. 市场热点与资金流向
    4. 技术面因素
    
    文章内容：
    {text}
    
    请用清晰、简洁的语言输出分析结果，突出关键信息。
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content
    except Exception as e:
        logger.error(f"DeepSeek API 请求出错: {e}")
        return f"API调用失败: {str(e)}"

def analyze_stock(stock):
    """
    分析单个股票，获取文章并调用DeepSeek API生成分析
    
    参数:
    stock: 股票信息字典
    
    返回:
    dict: 包含分析结果的字典
    """
    logger.info(f"开始分析股票 {stock['ts_code']} {stock['name']} ...")

    # 搜索相关文章
    articles = search_articles(stock['name'])
    if not articles:
        logger.warning(f"未搜索到关于 {stock['name']} 的相关文章")
        return {**stock, "analysis": "未找到相关文章"}

    # 获取文章内容
    content_list = []
    for art in articles[:3]:  # 只获取前3篇文章
        logger.info(f"获取文章: {art['title']}")
        art_content = fetch_article_content(art['url'])
        if art_content:
            content_list.append(art_content)
        time.sleep(0.5)  # 避免请求过快
    
    if not content_list:
        logger.warning(f"关于 {stock['name']} 的文章内容为空")
        return {**stock, "analysis": "文章内容为空"}

    # 组合文章内容
    full_content = "\n\n".join(content_list)
    # 截取适当长度，避免超出API限制
    full_content = full_content[:5000]

    # 调用DeepSeek API分析
    logger.info(f"调用DeepSeek API分析 {stock['name']} 的相关文章...")
    analysis = call_deepseek_api(full_content, stock)
    
    return {**stock, "analysis": analysis}

def plot_stock_price(stock_data, selected_stocks, output_dir=OUTPUT_DIR, use_adj_price=True):
    """
    绘制并保存选中股票的K线图
    
    参数:
    stock_data: 字典，键为股票代码，值为价格数据DataFrame
    selected_stocks: 选中的股票列表
    output_dir: 输出目录
    use_adj_price: 是否使用前复权价格，默认True
    """
    for stock in selected_stocks[:10]:  # 最多绘制前10只股票
        ts_code = stock['ts_code']
        if ts_code not in stock_data:
            continue
            
        df = stock_data[ts_code]
        if df.empty or len(df) < 50:
            continue
            
        # 创建图表
        plt.figure(figsize=(12, 6))
        
        # 绘制K线图和均线
        price_col = 'close_adj' if use_adj_price and all(col in df.columns for col in ['close_adj', 'high_adj', 'low_adj']) else 'close'
        plt.plot(df.index, df[price_col], 'b-', label='收盘价')
        plt.plot(df.index, df[price_col].rolling(window=20).mean(), 'r-', label='20日均线')
        plt.plot(df.index, df[price_col].rolling(window=60).mean(), 'g-', label='60日均线')
        
        # 标记当前价格
        current_price = df[price_col].iloc[-1]
        plt.axhline(y=current_price, color='r', linestyle='--', alpha=0.3)
        
        # 标记历史最高和最低价
        hist_high = df['high'].max()
        hist_low = df['low'].min()
        plt.axhline(y=hist_high, color='g', linestyle='--', alpha=0.3, label='历史最高价')
        plt.axhline(y=hist_low, color='r', linestyle='--', alpha=0.3, label='历史最低价')
        
        # 设置标题和标签
        price_type = "前复权" if use_adj_price else "未复权"
        plt.title(f"{stock['name']}({ts_code}) - 历史价格走势 ({price_type}价格)")
        plt.xlabel('日期')
        plt.ylabel('价格')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 保存图表
        filename = os.path.join(output_dir, f"{ts_code}_{stock['name']}_price_chart.png")
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        plt.close()
        
        logger.info(f"已保存 {stock['name']} 的价格走势图到 {filename}")

def analyze_stocks_with_threads(stocks, max_workers=MAX_THREADS):
    """
    使用多线程分析多只股票
    
    参数:
    stocks: 股票列表
    max_workers: 最大线程数
    
    返回:
    list: 包含分析结果的列表
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {executor.submit(analyze_stock, stock): stock for stock in stocks}
        for future in as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"分析股票 {stock['name']} 时出错: {e}")
    
    return results

def save_results_to_file(results, filename=None):
    """
    保存分析结果到文件
    
    参数:
    results: 分析结果列表
    filename: 输出文件名，默认为当前日期加股票数量
    """
    if not filename:
        today = datetime.today().strftime('%Y%m%d')
        filename = os.path.join(OUTPUT_DIR, f"stock_analysis_{today}_{len(results)}.json")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"分析结果已保存到 {filename}")
    
    # 同时保存为CSV格式，便于查看
    csv_filename = filename.replace('.json', '.csv')
    df = pd.DataFrame(results)
    if not df.empty:
        # 选择要保存的列
        columns = ['ts_code', 'name', 'trade_date', 'last_close', 'total_mv', 'recent_return', 'rebound_ratio']
        if 'analysis' in df.columns:
            columns.append('analysis')
        df[columns].to_csv(csv_filename, index=False, encoding='utf-8-sig')
        logger.info(f"分析结果摘要已保存到 {csv_filename}")

def get_adj_price_data(pro, ts_code, start_date, end_date):
    """
    获取前复权价格数据
    
    参数:
    pro: tushare pro接口
    ts_code: 股票代码
    start_date: 开始日期
    end_date: 结束日期
    
    返回:
    pd.DataFrame: 前复权价格数据
    """
    # 先获取普通行情数据
    df = get_data_with_retry(pro.daily, ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df.empty:
        return df
    
    # 获取复权因子
    adj_factor = get_data_with_retry(pro.adj_factor, ts_code=ts_code, start_date=start_date, end_date=end_date)
    if adj_factor.empty:
        return df  # 如果获取复权因子失败，则返回原始数据
    
    # 确保时间序列对齐
    df = df.set_index('trade_date')
    adj_factor = adj_factor.set_index('trade_date')
    
    # 合并数据
    df = pd.merge(df, adj_factor, left_index=True, right_index=True, how='left')
    
    # 填充缺失的复权因子（向前填充）
    df['adj_factor'] = df['adj_factor'].ffill()
    
    # 使用当前的复权因子作为基准
    current_factor = df['adj_factor'].iloc[-1] if not df.empty else 1.0
    
    # 计算前复权价格
    for col in ['open', 'high', 'low', 'close']:
        df[f'{col}_adj'] = df[col] * df['adj_factor'] / current_factor
    
    # 重置索引
    df = df.reset_index()
    
    return df

def run_strategy(
    date=None, 
    trade_days=300, 
    market_value=150, 
    rebound=0.4, 
    volatility=0.03,
    recent_volatility=0.02,
    history_years=5,
    skip_analysis=False, 
    skip_plot=False,
    use_adj_price=True,
    debug_stock=None  # 增加调试特定股票的参数
):
    """
    运行新高股票选股策略
    
    参数:
        date: 分析日期，格式为YYYYMMDD，默认为最近交易日
        trade_days: 历史数据天数，默认300天
        market_value: 最小市值（亿元），默认150亿
        rebound: 最大反弹幅度，默认0.4（40%）
        volatility: 波动率阈值，默认0.03（3%），用于判断趋势性上涨
        recent_volatility: 最近五日波动率阈值，默认0.02(2%)
        history_years: 计算历史最高/最低点时考虑的年数，默认5年
        skip_analysis: 是否跳过文章分析，默认False
        skip_plot: 是否跳过图表绘制，默认False
        use_adj_price: 是否使用前复权价格，默认True
        debug_stock: 需要调试的特定股票代码，例如'000733.SZ'
    
    返回:
        dict: 包含选中的股票列表和分析结果
    """
    # 临时提高日志级别以显示调试信息
    logger.setLevel(logging.DEBUG)
    
    # 更新参数
    global TRADE_DAYS, MARKET_VALUE_THRESHOLD, REBOUND_THRESHOLD
    
    TRADE_DAYS = trade_days
    MARKET_VALUE_THRESHOLD = market_value * 10000  # 转换为万元单位
    REBOUND_THRESHOLD = rebound
    
    # 初始化Tushare
    ts.set_token(TOKEN)
    pro = ts.pro_api()
    
    # 计算日期范围
    end_date = date if date else datetime.today().strftime("%Y%m%d")
    
    # 为确保能获得足够的数据，获取较长时间范围（需要获取足够多年的数据用于计算历史高低点）
    days_delta = max(int(TRADE_DAYS * 1.8), history_years * 365)  # 计算开始日期
    start_date = (datetime.strptime(end_date, "%Y%m%d") - timedelta(days=days_delta)).strftime("%Y%m%d")
    
    price_type = "前复权" if use_adj_price else "未复权"
    logger.info(f"分析日期范围: {start_date} 至 {end_date} (历史高低点计算使用最近{history_years}年{price_type}数据)")
    logger.info(f"选股条件: 市值>={MARKET_VALUE_THRESHOLD/10000:.1f}亿, 相对位置<={REBOUND_THRESHOLD:.2f}, "
                f"波动率<{volatility*100:.1f}%, 最近五日波动率<{recent_volatility*100:.1f}%")
    
    # 获取股票列表
    stock_basic = get_data_with_retry(pro.stock_basic, exchange='', list_status='L', fields='ts_code,name,industry,market')
    stock_list = stock_basic['ts_code'].tolist()
    logger.info(f"共获取 {len(stock_list)} 只股票进行处理...")
    
    # 如果指定了调试股票，优先处理
    if debug_stock and debug_stock in stock_list:
        # 将调试股票移动到列表开头
        stock_list.remove(debug_stock)
        stock_list.insert(0, debug_stock)
        logger.info(f"优先处理调试股票: {debug_stock}")
    
    # 获取交易日期列表，用于确保数据完整性
    trade_dates = get_trade_dates(pro, start_date, end_date)
    if not trade_dates:
        logger.error("无法获取交易日期，请检查日期范围和API访问权限")
        return {"selected_stocks": [], "analysis_results": []}
    
    # 确定最后交易日
    last_trade_date = trade_dates[-1]
    logger.info(f"最近交易日: {last_trade_date}")
    
    # 用于保存候选股票和临时数据
    selected_stocks = []
    stock_data = {}  # 存储股票价格数据，避免重复获取
    
    # 计数器，用于记录各条件筛选出的股票数量
    counters = {
        "total": 0,
        "new_high": 0,
        "market_value": 0,
        "uptrend": 0,
        "rebound": 0,
        "final": 0
    }
    
    # 处理每支股票
    for i, ts_code in enumerate(stock_list):
        is_debug_stock = (ts_code == debug_stock)
        
        if i % 100 == 0 or is_debug_stock:
            logger.info(f"进度: {i}/{len(stock_list)} ({i/len(stock_list)*100:.1f}%) 处理: {ts_code}")
        
        try:
            counters["total"] += 1
            
            # 获取前复权历史行情数据
            df = get_adj_price_data(pro, ts_code, start_date, end_date)
            if df.empty or len(df) < TRADE_DAYS:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 数据不足: 获取到 {len(df)} 行数据，需要 {TRADE_DAYS} 行")
                continue  # 数据不足，跳过
            
            # 将数据按日期升序排序
            df.sort_values(by='trade_date', inplace=True)
            df.reset_index(drop=True, inplace=True)
            
            # 保存价格数据，用于后续处理
            stock_data[ts_code] = df.copy()
            
            # 截取最近N天数据
            df_recent = df.tail(TRADE_DAYS)
            
            # 获取最近一天的数据
            last_day = df_recent.iloc[-1]
            if last_day['trade_date'] != last_trade_date:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 最新数据不是最近交易日: {last_day['trade_date']} != {last_trade_date}")
                continue  # 最新数据不是最近交易日，可能停牌，跳过
            
            # 选择价格列
            has_adj_price = all(col in df.columns for col in ['close_adj', 'high_adj', 'low_adj'])
            close_col = 'close_adj' if use_adj_price and has_adj_price else 'close'
            high_col = 'high_adj' if use_adj_price and has_adj_price else 'high'
                
            last_close = last_day[close_col]
            
            # 检查是否为300日新高（使用前复权价格）
            if is_debug_stock:
                # 详细输出调试股票的新高判断信息
                recent_max_close = df_recent[close_col].max()
                high_date = df_recent.loc[df_recent[close_col].idxmax(), 'trade_date']
                logger.warning(f"调试股票 {ts_code} 新高检查:")
                logger.warning(f"  - 当前收盘价({price_type}): {last_close}")
                logger.warning(f"  - 近{TRADE_DAYS}日最高收盘价({price_type}): {recent_max_close} [日期: {high_date}]")
                logger.warning(f"  - 是否创新高: {last_close >= recent_max_close}")
                
                # 输出最近的最高收盘价记录
                high_prices = df_recent.sort_values(by=close_col, ascending=False).head(5)
                logger.warning(f"  - 最近5个最高收盘价记录:")
                for idx, row in high_prices.iterrows():
                    logger.warning(f"    * 日期: {row['trade_date']}, {close_col}: {row[close_col]}")
            
            # 1. 判断是否为300日新高（使用前复权价格）
            # 注意：这里之前的判断有问题，应该检查当前收盘价是否达到最近N个交易日的最高收盘价
            # 而不是高价，历史最高价应该用close_col而不是high_col
            recent_max_close = df_recent[close_col].max()
            if last_close < recent_max_close:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 未通过新高筛选，当前收盘价({last_close}) < 历史最高收盘价({recent_max_close})")
                continue
                
            # 获取股票名称用于日志输出
            stock_name = stock_basic[stock_basic['ts_code'] == ts_code]['name'].values[0]
            logger.debug(f"股票 {stock_name}({ts_code}) 通过新高筛选条件 ({price_type}价格)")
            counters["new_high"] += 1
            
            # 2. 检查市值
            df_basic = get_data_with_retry(pro.daily_basic, ts_code=ts_code, trade_date=last_day['trade_date'],
                                      fields='ts_code,total_mv,turnover_rate,pe,pb')
            if df_basic.empty:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 未获取到基本面数据")
                continue
                
            total_mv = df_basic.iloc[0]['total_mv']
            if total_mv < MARKET_VALUE_THRESHOLD:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 市值({total_mv/10000:.2f}亿)未达到阈值({MARKET_VALUE_THRESHOLD/10000:.2f}亿)")
                continue
                
            logger.debug(f"股票 {stock_name}({ts_code}) 通过市值筛选条件, 市值:{total_mv/10000:.2f}亿")
            counters["market_value"] += 1
            
            # 3. 检查是否是趋势性上涨而非暴涨，使用传入的波动率阈值
            if not is_uptrend(df, window=20, volatility_threshold=volatility, 
                              recent_volatility_threshold=recent_volatility, use_adj=use_adj_price):
                # 计算波动率用于调试日志
                price_series = df[close_col] if isinstance(df, pd.DataFrame) else df
                calculated_volatility = price_series.pct_change().tail(MIN_UPTREND_DAYS).std()
                recent_vol = price_series.pct_change().tail(5).std()
                
                if is_debug_stock:
                    # 详细输出调试股票的趋势判断
                    ma = price_series.rolling(window=20).mean()
                    recent_ma = ma.dropna().tail(MIN_UPTREND_DAYS)
                    x = np.arange(len(recent_ma))
                    y = recent_ma.values
                    slope, _ = np.polyfit(x, y, 1)
                    
                    logger.warning(f"调试股票 {ts_code} 趋势判断:")
                    logger.warning(f"  - 斜率: {slope:.6f} (需要 > 0)")
                    logger.warning(f"  - 总体波动率: {calculated_volatility:.4f} (需要 < {volatility:.4f})")
                    logger.warning(f"  - 最近五日波动率: {recent_vol:.4f} (需要 < {recent_volatility:.4f})")
                    
                logger.debug(f"股票 {stock_name}({ts_code}) 未通过趋势性上涨筛选, "
                           f"波动率:{calculated_volatility:.4f}/{volatility:.4f}, "
                           f"最近五日波动率:{recent_vol:.4f}/{recent_volatility:.4f}")
                continue
                
            logger.debug(f"股票 {stock_name}({ts_code}) 通过趋势性上涨筛选条件 ({price_type}价格)")
            counters["uptrend"] += 1
            
            # 4. 计算从底部反弹的相对位置，使用指定的历史年数
            rebound_ratio = calculate_rebound_from_bottom(df, years=history_years)
            
            if is_debug_stock:
                # 详细输出调试股票的反弹位置计算
                days_in_period = min(history_years * 250, len(df))
                recent_df = df.tail(days_in_period)
                c_col = 'close_adj' if use_adj_price and has_adj_price else 'close'
                l_col = 'low_adj' if use_adj_price and has_adj_price else 'low'
                h_col = 'high_adj' if use_adj_price and has_adj_price else 'high'
                
                current_price = recent_df[c_col].iloc[-1]
                historical_low = recent_df[l_col].min()
                historical_high = recent_df[h_col].max()
                
                low_date = recent_df.loc[recent_df[l_col].idxmin(), 'trade_date']
                high_date = recent_df.loc[recent_df[h_col].idxmax(), 'trade_date']
                
                logger.warning(f"调试股票 {ts_code} 反弹位置计算:")
                logger.warning(f"  - 当前价格: {current_price:.2f}")
                logger.warning(f"  - 历史最低: {historical_low:.2f} [日期: {low_date}]")
                logger.warning(f"  - 历史最高: {historical_high:.2f} [日期: {high_date}]")
                logger.warning(f"  - 相对位置: {rebound_ratio:.4f} (需要 <= {REBOUND_THRESHOLD:.4f})")
            
            logger.debug(f"股票 {stock_name}({ts_code}) 相对位置: {rebound_ratio:.2f} (基于近{history_years}年{price_type}数据), 阈值: {REBOUND_THRESHOLD:.2f}")
            
            if rebound_ratio > REBOUND_THRESHOLD:
                logger.debug(f"股票 {stock_name}({ts_code}) 未通过反弹位置筛选条件: {rebound_ratio:.2f} > {REBOUND_THRESHOLD:.2f}")
                continue
                
            logger.debug(f"股票 {stock_name}({ts_code}) 通过反弹位置筛选条件")
            counters["rebound"] += 1
            
            # 计算最近一段时间的累计涨幅
            if len(df) <= RECENT_DAYS:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 数据不足以计算最近的累计涨幅")
                continue
            
            # 使用适当的价格列计算累计涨幅    
            recent_return = (last_close / df.iloc[-RECENT_DAYS-1][close_col]) - 1
            
            if is_debug_stock:
                logger.warning(f"调试股票 {ts_code} 最近{RECENT_DAYS}日累计涨幅: {recent_return*100:.2f}% (阈值: {RECENT_RETURN_THRESHOLD*100:.2f}%)")
            
            if recent_return > RECENT_RETURN_THRESHOLD:
                if is_debug_stock:
                    logger.warning(f"调试股票 {ts_code} 最近涨幅过高: {recent_return*100:.2f}% > {RECENT_RETURN_THRESHOLD*100:.2f}%")
                continue
            
            # 获取行业
            industry = stock_basic[stock_basic['ts_code'] == ts_code]['industry'].values[0]
            
            # 添加到候选列表
            selected_stocks.append({
                'ts_code': ts_code,
                'name': stock_name,
                'industry': industry,
                'trade_date': last_day['trade_date'],
                'last_close': last_close,
                'total_mv': total_mv,
                'recent_return': recent_return,
                'rebound_ratio': rebound_ratio
            })
            
            counters["final"] += 1
            logger.info(f"找到符合条件的股票: {stock_name}({ts_code}), 市值:{total_mv/10000:.2f}亿, 相对位置:{rebound_ratio:.2f} (近{history_years}年{price_type})")
            
        except Exception as e:
            logger.error(f"处理 {ts_code} 发生错误: {e}")
            if is_debug_stock:
                # 对于调试股票，显示更详细的错误信息
                import traceback
                logger.error(f"调试股票 {ts_code} 出错详情:")
                logger.error(traceback.format_exc())
            continue
    
    analysis_results = []
    
    # 显示筛选计数
    logger.info("筛选统计:")
    logger.info(f"总股票数量: {counters['total']}")
    logger.info(f"新高筛选通过: {counters['new_high']}")
    logger.info(f"市值筛选通过: {counters['market_value']}")
    logger.info(f"趋势筛选通过: {counters['uptrend']}")
    logger.info(f"反弹位置筛选通过(近{history_years}年{price_type}): {counters['rebound']}")
    logger.info(f"最终通过: {counters['final']}")
    
    # 显示初步筛选结果
    if selected_stocks:
        logger.info(f"初步筛选出 {len(selected_stocks)} 只符合条件的股票")
        
        # 绘制价格走势图
        if not skip_plot:
            logger.info("绘制价格走势图...")
            plot_stock_price(stock_data, selected_stocks, use_adj_price=use_adj_price)
        
        # 深入分析文章内容
        if not skip_analysis and selected_stocks:
            logger.info("开始分析股票相关文章...")
            analysis_results = analyze_stocks_with_threads(selected_stocks)
            save_results_to_file(analysis_results)
        else:
            save_results_to_file(selected_stocks)
    else:
        logger.info("没有找到符合条件的股票")
    
    # 恢复日志级别
    logger.setLevel(logging.INFO)
    
    return {
        "selected_stocks": selected_stocks,
        "analysis_results": analysis_results if analysis_results else selected_stocks
    }

def main():
    parser = argparse.ArgumentParser(description='New High Stock Strategy')
    parser.add_argument('--date', '-d', type=str, help='Analysis date in YYYYMMDD format')
    parser.add_argument('--days', '-n', type=int, default=TRADE_DAYS, help='Days of historical data, default: ' + str(TRADE_DAYS))  # 历史数据天数
    parser.add_argument('--market-value', '-m', type=float, default=150, help='Minimum market value in billion yuan, default: 150')
    parser.add_argument('--rebound', '-r', type=float, default=0.4, help='Maximum rebound ratio, default: 0.4')
    parser.add_argument('--volatility', '-v', type=float, default=0.03, help='Maximum volatility threshold, default: 0.03')
    parser.add_argument('--recent-volatility', '-rv', type=float, default=0.02, help='Maximum recent volatility threshold, default: 0.02')
    parser.add_argument('--history-years', '-hy', type=int, default=5, help='Maximum history years for rebound calculation, default: 5')
    parser.add_argument('--no-analysis', '-na', action='store_true', help='Skip article analysis')
    parser.add_argument('--no-plot', '-np', action='store_true', help='Skip chart plotting')
    parser.add_argument('--no-adj-price', '-nap', action='store_true', help='Do not use adjusted price')
    parser.add_argument('--debug-stock', '-ds', type=str, help='Debug specific stock code, e.g., 000733.SZ')
    args = parser.parse_args()
    
    # 通过函数调用策略
    run_strategy(
        date=args.date,
        trade_days=args.days,
        market_value=args.market_value,
        rebound=args.rebound,
        volatility=args.volatility,
        recent_volatility=args.recent_volatility,
        history_years=args.history_years,
        skip_analysis=args.no_analysis,
        skip_plot=args.no_plot,
        use_adj_price=not args.no_adj_price,
        debug_stock=args.debug_stock
    )

# 测试调用
if __name__ == "__main__":
    # 使用真实历史日期进行测试，并调试振华科技
    results = run_strategy(
        date='20250411',  # 使用指定日期的数据
        trade_days=300,   # 分析过去300个交易日的新高
        market_value=100, # 筛选100亿市值以上的股票
        rebound=0.35,     # 相对位置不超过0.35（即当前价格在历史最低点到最高点之间的前35%区域内）
        volatility=0.04,  # 总体波动率阈值为4%
        recent_volatility=0.05,  # 最近五日波动率阈值为5%
        history_years=4,   # 使用最近4年的数据计算历史最高/最低点
        use_adj_price=True,  # 使用前复权价格
        #debug_stock='000733.SZ'  # 调试振华科技
    )
    
    # 获取结果
    selected_stocks = results['selected_stocks']
    
    # 打印结果统计
    print(f"找到符合条件的股票数量: {len(selected_stocks)}")
    for stock in selected_stocks[:10]:  # 只显示前10只
        print(f"{stock['name']}({stock['ts_code']}): 市值{stock['total_mv']/10000:.2f}亿, 相对位置:{stock['rebound_ratio']:.2f}")

def filter_stocks_for_report(date=None, 
                    trade_days=300, 
                    market_value=150, 
                    rebound=0.4, 
                    volatility=0.03,
                    recent_volatility=0.02,
                    history_years=5,
                    use_adj_price=True):
    """
    简化版的新高股票筛选函数，用于集成到市场监测报告中
    
    参数:
        date: 分析日期，格式为YYYYMMDD，默认为最近交易日
        trade_days: 历史数据天数，默认300天
        market_value: 最小市值（亿元），默认150亿
        rebound: 最大反弹幅度，默认0.4（40%）
        volatility: 波动率阈值，默认0.03（3%），用于判断趋势性上涨
        recent_volatility: 最近五日波动率阈值，默认0.02(2%)
        history_years: 计算历史最高/最低点时考虑的年数，默认5年
        use_adj_price: 是否使用前复权价格，默认True
    
    返回:
        list: 筛选出的股票列表，每个股票包含基本信息
    """
    logger.info("开始筛选创新高的优质股票...")
    
    # 运行筛选策略，但跳过分析和绘图步骤
    results = run_strategy(
        date=date,
        trade_days=trade_days,
        market_value=market_value,
        rebound=rebound,
        volatility=volatility,
        recent_volatility=recent_volatility,
        history_years=history_years,
        skip_analysis=True,  # 跳过文章分析
        skip_plot=True,      # 跳过绘图
        use_adj_price=use_adj_price
    )
    
    # 获取筛选结果
    selected_stocks = results["selected_stocks"]
    
    # 简化输出信息
    simplified_results = []
    for stock in selected_stocks:
        simplified_results.append({
            'ts_code': stock['ts_code'],
            'name': stock['name'],
            'industry': stock['industry'],
            'trade_date': stock['trade_date'],
            'last_close': stock['last_close'],
            'total_mv': stock['total_mv']/10000,  # 转换为亿元单位
            'recent_return': stock['recent_return'],
            'rebound_ratio': stock['rebound_ratio']
        })
    
    logger.info(f"筛选完成，共找到 {len(simplified_results)} 只符合条件的股票")
    return simplified_results

def generate_filtered_stocks_plot(filtered_stocks, save_path="filtered_stocks.png", show_fig=False):
    """
    为筛选出的股票生成图表，用于市场监测报告
    
    参数:
        filtered_stocks: 筛选出的股票列表
        save_path: 保存图表的路径
        show_fig: 是否显示图表
    
    返回:
        str: 保存的图表文件路径
    """
    # 如果没有筛选到股票，则返回空
    if not filtered_stocks:
        return None
    
    # 取前20只或全部（如果不足20只）进行可视化
    max_stocks = min(len(filtered_stocks), 20)
    stocks_to_plot = filtered_stocks[:max_stocks]
    
    # 准备数据
    names = [f"{stock['name']}({stock['ts_code'].split('.')[0]})" for stock in stocks_to_plot]
    market_values = [stock['total_mv'] for stock in stocks_to_plot]
    rebound_ratios = [stock['rebound_ratio'] for stock in stocks_to_plot]
    
    # 创建图表
    plt.figure(figsize=(14, 8))
    
    # 创建双坐标轴
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    
    # 绘制柱状图（市值）
    bars = ax1.bar(names, market_values, color='skyblue', alpha=0.7)
    ax1.set_ylabel('市值（亿元）', fontsize=12)
    ax1.set_ylim(bottom=0)  # 设置Y轴起点为0
    
    # 绘制折线图（相对位置）
    ax2.plot(names, rebound_ratios, 'ro-', linewidth=2)
    ax2.set_ylabel('相对位置（0-1之间）', fontsize=12)
    ax2.set_ylim(0, 1)  # 相对位置在0-1之间
    
    # 标记数据点
    for i, v in enumerate(rebound_ratios):
        ax2.text(i, v + 0.02, f'{v:.2f}', ha='center', fontsize=9)
    
    # 设置X轴标签
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.title('创新高优质股票筛选结果', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(save_path, dpi=120, bbox_inches='tight')
    
    if show_fig:
        plt.show()
    else:
        plt.close()
    
    return save_path