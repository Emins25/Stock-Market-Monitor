import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import os
import sys
import logging

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('market_moneyflow')

"""
全市场个股资金净流入分析：分析全市场资金净流入最高的股票
1. 拉取全市场个股的当日资金净流入数据，排序之后取前十名，柱状图展示
2. 计算全市场每个股票的资金流入率=（资金净流入/当日成交额）*100%，排序后取最高的前十名，柱状图展示
"""

# 导入通用的Tushare工具模块
try:
    from tushare_utils import get_data_with_retry
except ImportError:
    # 如果导入失败，使用内部定义的版本
    def get_data_with_retry(func, max_retries=5, retry_delay=2, extended_wait=True, **kwargs):
        """
        带重试机制的数据获取函数
        
        参数:
            func: tushare接口函数
            max_retries: 最大重试次数，默认为5
            retry_delay: 初始重试延迟（秒），默认为2秒
            extended_wait: 是否在错误时使用指数退避延迟，默认为True
            **kwargs: 传递给接口的参数
        
        返回:
            pd.DataFrame: 获取的数据，失败时返回空DataFrame
        """
        for i in range(max_retries):
            try:
                data = func(**kwargs)
                return data
            except Exception as e:
                error_msg = str(e)
                print(f"获取数据时出错 (尝试 {i+1}/{max_retries}): {error_msg}")
                
                # 检查是否是API访问频率限制错误
                if "每分钟最多访问该接口" in error_msg:
                    print(f"遇到API访问频率限制，暂停60秒后继续...")
                    time.sleep(60)  # 暂停60秒后继续尝试
                    continue  # 不增加retry计数，直接重试
                    
                if i < max_retries - 1:
                    sleep_time = retry_delay if not extended_wait else retry_delay * (2 ** i)
                    print(f"等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
        
        # 所有尝试都失败，返回空DataFrame
        print("所有尝试都失败，返回空数据")
        return pd.DataFrame()

def get_latest_trade_date(pro, days_back=5):
    """
    获取最近的交易日期
    
    参数:
    pro: tushare pro接口
    days_back: 向前查找的天数
    
    返回:
    str: 最近的交易日期，格式为YYYYMMDD
    """
    today = datetime.now()
    end_date = today.strftime('%Y%m%d')
    start_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
    
    try:
        # 获取交易日历
        trade_cal = get_data_with_retry(pro.trade_cal, exchange='SSE', 
                                     start_date=start_date, 
                                     end_date=end_date, 
                                     is_open='1')
        if not trade_cal.empty:
            # 获取最近的交易日
            latest_trade_date = trade_cal['cal_date'].iloc[-1]
            return latest_trade_date
    except Exception as e:
        print(f"获取最近交易日期失败: {e}")
    
    # 如果获取失败，返回当前日期
    return end_date

def analyze_market_moneyflow(token=None, date=None, top_n=10, save_fig=True, show_fig=True, only_net_inflow=False):
    """
    分析全市场个股资金净流入情况
    
    参数:
    token: tushare API token，若为None则使用默认token
    date: 要查询的日期，格式为'YYYYMMDD'，若为None则使用当前日期
    top_n: 要显示的股票数量，默认为10
    save_fig: 是否保存图片，默认为True
    show_fig: 是否显示图表，默认为True
    only_net_inflow: 是否只返回净流入排行，不返回净流入率排行，默认为False
    
    返回:
    tuple: 包含净流入排行和流入率排行的DataFrame
    """
    # 设置默认token
    if token is None:
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
    
    # 初始化tushare API
    pro = ts.pro_api(token)
    
    # 获取交易日期
    if date is None:
        date = get_latest_trade_date(pro)
    print(f"分析日期: {date}")
    
    # 获取所有股票列表
    print("获取A股股票列表...")
    stocks = get_data_with_retry(pro.stock_basic, exchange='', list_status='L', 
                              fields='ts_code,name,industry,market,area,list_date')
    
    if stocks.empty:
        print("获取股票列表失败")
        return pd.DataFrame(), pd.DataFrame()
    
    print(f"共获取 {len(stocks)} 支股票的基本信息")
    
    # 获取股票资金流向数据
    print("获取全市场个股资金流向数据...")
    df_flow = get_stocks_moneyflow(pro, stocks['ts_code'].tolist(), date)
    
    if df_flow.empty:
        print("获取资金流向数据失败")
        return pd.DataFrame(), pd.DataFrame()
    
    print(f"成功获取 {len(df_flow)} 支股票的资金流向数据")
    
    # 1. 分析资金净流入最高的股票
    net_inflow_top = analyze_net_inflow(df_flow, top_n, date, save_fig, show_fig)
    
    # 2. 分析资金流入率最高的股票 (如果参数为True则跳过)
    if only_net_inflow:
        print("只返回净流入排行，跳过净流入率排行分析")
        inflow_rate_top = pd.DataFrame()
    else:
        inflow_rate_top = analyze_inflow_rate(df_flow, top_n, date, save_fig, show_fig)
    
    return net_inflow_top, inflow_rate_top

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
            filtered_data['net_mf_amount'] = pd.to_numeric(filtered_data['net_mf_amount'], errors='coerce')
            filtered_data['net_amount'] = filtered_data['net_mf_amount']
            print("已将net_mf_amount复制为net_amount以保持代码兼容性")
        elif 'buy_amount' in filtered_data.columns and 'sell_amount' in filtered_data.columns:
            filtered_data['net_amount'] = filtered_data['buy_amount'] - filtered_data['sell_amount']
            print("已计算net_amount (buy_amount - sell_amount)")
        
        # 获取日线数据以补充成交额等信息
        if 'amount' not in filtered_data.columns:
            print("获取日线数据以补充成交额信息...")
            df_daily = get_data_with_retry(pro.daily, trade_date=trade_date, 
                                      fields='ts_code,trade_date,open,high,low,close,vol,amount')
            
            if not df_daily.empty:
                filtered_data = pd.merge(filtered_data, df_daily, on=['ts_code', 'trade_date'], how='left')
                print(f"成功补充了{len(filtered_data[~filtered_data['amount'].isna()])}支股票的成交额信息")
        
        # 获取股票名称等基本信息
        print("获取股票基本信息...")
        stock_basic_info = get_data_with_retry(pro.stock_basic, 
                                          fields='ts_code,name,industry,market,area',
                                          exchange='',
                                          list_status='L')
        
        if not stock_basic_info.empty:
            filtered_data = pd.merge(filtered_data, stock_basic_info, on=['ts_code'], how='left')
            print(f"已关联{len(filtered_data[~filtered_data['name'].isna()])}支股票的基本信息(名称、行业等)")
        
        # 打印数据列名，帮助调试
        print(f"数据列名: {filtered_data.columns.tolist()}")
        
        return filtered_data
        
    except Exception as e:
        print(f"获取股票资金流向数据时出错: {e}")
        return pd.DataFrame()

def analyze_net_inflow(df_flow, top_n=10, trade_date=None, save_fig=True, show_fig=True):
    """
    分析全市场资金净流入最高的股票
    
    参数:
    df_flow: 股票资金流向数据
    top_n: 要显示的股票数量
    trade_date: 交易日期
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    
    返回:
    DataFrame: 资金净流入排名靠前的股票
    """
    print("分析全市场资金净流入最高的股票...")
    
    # 检查是否存在净流入金额列
    if 'net_amount' not in df_flow.columns:
        print("数据中缺少net_amount列，尝试计算...")
        if 'buy_amount' in df_flow.columns and 'sell_amount' in df_flow.columns:
            df_flow['net_amount'] = df_flow['buy_amount'] - df_flow['sell_amount']
        else:
            print("无法计算净流入金额，无法进行分析")
            return pd.DataFrame()
    
    # 确保净流入金额为数值类型
    df_flow['net_amount'] = pd.to_numeric(df_flow['net_amount'], errors='coerce')
    
    # 处理缺失值
    df_flow = df_flow.dropna(subset=['net_amount'])
    
    if df_flow.empty:
        print("处理后数据为空，无法继续分析")
        return pd.DataFrame()
    
    # 按净流入金额排序
    top_stocks = df_flow.sort_values('net_amount', ascending=False).head(top_n)
    
    # 打印资金净流入排名靠前的股票
    print(f"资金净流入排名前{top_n}的股票:")
    for i, (idx, row) in enumerate(top_stocks.iterrows(), 1):
        stock_name = row['name'] if 'name' in row and pd.notna(row['name']) else row['ts_code']
        net_amount_val = row['net_amount']
        # 根据数值大小判断单位并转换为亿元
        if isinstance(net_amount_val, (int, float)) and abs(net_amount_val) > 10000000:
            net_amount = net_amount_val / 100000000
            unit = "亿元"
        else:
            net_amount = net_amount_val / 10000
            unit = "亿元"
        
        print(f"{i}. {stock_name}({row['ts_code']}): {net_amount:.2f} {unit}")
    
    # 绘制柱状图
    if show_fig or save_fig:
        plot_net_inflow(top_stocks, trade_date, save_fig, show_fig)
    
    return top_stocks

def analyze_inflow_rate(df_flow, top_n=10, trade_date=None, save_fig=True, show_fig=True):
    """
    分析全市场资金流入率最高的股票
    资金流入率 = (资金净流入 / 成交额) * 100%
    
    参数:
    df_flow: 股票资金流向数据
    top_n: 要显示的股票数量
    trade_date: 交易日期
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    
    返回:
    DataFrame: 资金流入率排名靠前的股票
    """
    print("分析全市场资金流入率最高的股票...")
    
    # 复制数据以防修改原始数据
    df = df_flow.copy()
    
    # 检查是否存在净流入金额列和成交额列
    if 'net_amount' not in df.columns:
        print("数据中缺少net_amount列，尝试计算...")
        if 'buy_amount' in df.columns and 'sell_amount' in df.columns:
            df['net_amount'] = df['buy_amount'] - df['sell_amount']
        else:
            print("无法计算净流入金额，无法进行分析")
            return pd.DataFrame()
    
    if 'amount' not in df.columns:
        print("数据中缺少amount列，无法计算资金流入率")
        return pd.DataFrame()
    
    # 确保净流入金额和成交额为数值类型
    df['net_amount'] = pd.to_numeric(df['net_amount'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    
    # 处理缺失值
    df = df.dropna(subset=['net_amount', 'amount'])
    
    # 筛选成交额不为0的股票
    df = df[df['amount'] > 0]
    
    if df.empty:
        print("处理后数据为空，无法继续分析")
        return pd.DataFrame()
    
    # 计算资金流入率
    df['inflow_rate'] = df['net_amount'] / df['amount'] * 100
    
    # 检查计算结果中是否存在无穷大或NaN
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['inflow_rate'])
    
    if df.empty:
        print("计算资金流入率后数据为空，无法继续分析")
        return pd.DataFrame()
    
    # 按资金流入率排序
    top_stocks = df.sort_values('inflow_rate', ascending=False).head(top_n)
    
    # 打印资金流入率排名靠前的股票
    print(f"资金流入率排名前{top_n}的股票:")
    for i, (idx, row) in enumerate(top_stocks.iterrows(), 1):
        stock_name = row['name'] if 'name' in row and pd.notna(row['name']) else row['ts_code']
        print(f"{i}. {stock_name}({row['ts_code']}): {row['inflow_rate']:.2f}%")
    
    # 绘制柱状图
    if show_fig or save_fig:
        plot_inflow_rate(top_stocks, trade_date, save_fig, show_fig)
    
    return top_stocks

def plot_net_inflow(top_stocks, trade_date=None, save_fig=True, show_fig=True):
    """
    绘制全市场资金净流入最高的股票柱状图
    
    参数:
    top_stocks: 资金净流入排名靠前的股票
    trade_date: 交易日期
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    """
    if top_stocks.empty:
        print("没有数据可供绘图")
        return
    
    # 设置图表大小
    plt.figure(figsize=(16, 10))
    
    # 准备绘图数据
    stock_names = []
    for idx, row in top_stocks.iterrows():
        name = row['name'] if 'name' in row and pd.notna(row['name']) else ''
        code = row['ts_code'] if 'ts_code' in row else ''
        
        if name:
            display_name = f"{name}({code.split('.')[0]})"
        else:
            display_name = code
        
        stock_names.append(display_name)
    
    # 净流入金额处理
    # 检测值的单位
    net_amount_col = pd.to_numeric(top_stocks['net_amount'], errors='coerce')
    if abs(net_amount_col.max()) > 10000000 or abs(net_amount_col.min()) > 10000000:
        # 值很大，可能是原始单位，转换为亿元
        net_amounts = net_amount_col / 100000000
        print("净流入金额单位检测：原始单位，转换为亿元")
    else:
        # 值较小，可能已经是万元单位，转换为亿元
        net_amounts = net_amount_col / 10000
        print("净流入金额单位检测：万元单位，转换为亿元")
    
    # 绘制柱状图
    bars = plt.bar(stock_names, net_amounts, width=0.6)
    
    # 设置柱子颜色：红色表示正值，绿色表示负值
    for i, bar in enumerate(bars):
        if bar.get_height() >= 0:
            bar.set_color('#F63366')  # 红色（净流入）
        else:
            bar.set_color('#09B552')  # 绿色（净流出）
    
    # 添加数据标签
    for i, bar in enumerate(bars):
        height = bar.get_height()
        if height >= 0:
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.05, 
                     f"+{height:.2f}", ha='center', va='bottom', fontsize=9)
        else:
            plt.text(bar.get_x() + bar.get_width()/2., height - 0.05, 
                     f"{height:.2f}", ha='center', va='top', fontsize=9)
    
    # 格式化日期
    formatted_date = trade_date
    if trade_date and len(trade_date) == 8:
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
    
    # 添加标题和标签
    plt.title(f"{formatted_date} 全市场个股资金净流入排行", fontsize=18, pad=15)
    plt.xlabel('股票', fontsize=14, labelpad=10)
    plt.ylabel('净流入金额（亿元）', fontsize=14, labelpad=10)
    
    # 设置x轴标签
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # 添加网格线
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    # 美化图表
    plt.gca().spines['top'].set_visible(False)  # 去掉上边框
    plt.gca().spines['right'].set_visible(False)  # 去掉右边框
    
    # 添加均值线
    mean_value = np.mean(net_amounts)
    if not np.isnan(mean_value) and not np.isinf(mean_value):
        plt.axhline(y=mean_value, color='#6A5ACD', linestyle='--', alpha=0.8)
        plt.text(len(stock_names)-1, mean_value, f'平均: {mean_value:.2f}亿', 
                 ha='right', va='bottom' if mean_value >= 0 else 'top', color='#6A5ACD')
    
    # 添加零线
    plt.axhline(y=0, color='black', alpha=0.3)
    
    # 调整y轴范围
    max_value = max(net_amounts)
    min_value = min(net_amounts)
    
    if not (np.isnan(max_value) or np.isnan(min_value) or np.isinf(max_value) or np.isinf(min_value)):
        y_padding = max(abs(max_value), abs(min_value)) * 0.15
        plt.ylim(min_value - y_padding, max_value + y_padding)
    
    # 添加数据来源和日期
    plt.figtext(0.02, 0.02, f"数据来源: 同花顺 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                ha='left', fontsize=8, alpha=0.6)
    
    # 优化布局
    plt.tight_layout(pad=2.0)
    
    # 保存图片
    if save_fig:
        filename = f'market_net_inflow_top_{trade_date}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"图表已保存为 {os.path.abspath(filename)}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()

def plot_inflow_rate(top_stocks, trade_date=None, save_fig=True, show_fig=True):
    """
    绘制全市场资金流入率最高的股票柱状图
    
    参数:
    top_stocks: 资金流入率排名靠前的股票
    trade_date: 交易日期
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    """
    if top_stocks.empty:
        print("没有数据可供绘图")
        return
    
    # 设置图表大小
    plt.figure(figsize=(16, 10))
    
    # 准备绘图数据
    stock_names = []
    for idx, row in top_stocks.iterrows():
        name = row['name'] if 'name' in row and pd.notna(row['name']) else ''
        code = row['ts_code'] if 'ts_code' in row else ''
        
        if name:
            display_name = f"{name}({code.split('.')[0]})"
        else:
            display_name = code
        
        stock_names.append(display_name)
    
    # 资金流入率处理
    inflow_rates = top_stocks['inflow_rate'].values
    
    # 绘制柱状图
    bars = plt.bar(stock_names, inflow_rates, width=0.6)
    
    # 设置柱子颜色：红色表示正值，绿色表示负值
    for i, bar in enumerate(bars):
        if bar.get_height() >= 0:
            bar.set_color('#F63366')  # 红色（正流入率）
        else:
            bar.set_color('#09B552')  # 绿色（负流入率）
    
    # 添加数据标签
    for i, bar in enumerate(bars):
        height = bar.get_height()
        if height >= 0:
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5, 
                     f"+{height:.2f}%", ha='center', va='bottom', fontsize=9)
        else:
            plt.text(bar.get_x() + bar.get_width()/2., height - 0.5, 
                     f"{height:.2f}%", ha='center', va='top', fontsize=9)
    
    # 格式化日期
    formatted_date = trade_date
    if trade_date and len(trade_date) == 8:
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
    
    # 添加标题和标签
    plt.title(f"{formatted_date} 全市场个股资金流入率排行", fontsize=18, pad=15)
    plt.xlabel('股票', fontsize=14, labelpad=10)
    plt.ylabel('资金流入率（%）', fontsize=14, labelpad=10)
    
    # 设置x轴标签
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    # 添加网格线
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    
    # 美化图表
    plt.gca().spines['top'].set_visible(False)  # 去掉上边框
    plt.gca().spines['right'].set_visible(False)  # 去掉右边框
    
    # 添加均值线
    mean_value = np.mean(inflow_rates)
    if not np.isnan(mean_value) and not np.isinf(mean_value):
        plt.axhline(y=mean_value, color='#6A5ACD', linestyle='--', alpha=0.8)
        plt.text(len(stock_names)-1, mean_value, f'平均: {mean_value:.2f}%', 
                 ha='right', va='bottom' if mean_value >= 0 else 'top', color='#6A5ACD')
    
    # 添加零线
    plt.axhline(y=0, color='black', alpha=0.3)
    
    # 调整y轴范围
    max_value = max(inflow_rates)
    min_value = min(inflow_rates)
    
    if not (np.isnan(max_value) or np.isnan(min_value) or np.isinf(max_value) or np.isinf(min_value)):
        y_padding = max(abs(max_value), abs(min_value)) * 0.15
        plt.ylim(min_value - y_padding, max_value + y_padding)
    
    # 添加数据来源和日期
    plt.figtext(0.02, 0.02, f"数据来源: 同花顺 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                ha='left', fontsize=8, alpha=0.6)
    
    # 优化布局
    plt.tight_layout(pad=2.0)
    
    # 保存图片
    if save_fig:
        filename = f'market_inflow_rate_top_{trade_date}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"图表已保存为 {os.path.abspath(filename)}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()

if __name__ == "__main__":
    # 分析全市场个股资金净流入情况
    net_inflow_top, inflow_rate_top = analyze_market_moneyflow(top_n=10) 