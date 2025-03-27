import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
import requests

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

"""
全市场个股资金净流入分析：分析全市场资金净流入最高的股票
1. 拉取全市场个股的当日资金净流入数据，排序之后取前十名，柱状图展示
2. 计算全市场每个股票的资金流入率=（资金净流入/当日成交额）*100%，排序后取最高的前十名，柱状图展示
"""

def analyze_market_moneyflow(token=None, date=None, top_n=10, save_fig=True, show_fig=True):
    """
    分析全市场个股资金净流入情况
    
    参数:
    token: tushare API token，若为None则使用默认token
    date: 要查询的日期，格式为'YYYYMMDD'，若为None则使用当前日期
    top_n: 要显示的股票数量，默认为10
    save_fig: 是否保存图片，默认为True
    show_fig: 是否显示图表，默认为True
    
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
        date = datetime.now().strftime('%Y%m%d')
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
    
    # 2. 分析资金流入率最高的股票
    inflow_rate_top = analyze_inflow_rate(df_flow, top_n, date, save_fig, show_fig)
    
    return net_inflow_top, inflow_rate_top

def get_data_with_retry(func, max_retries=5, **kwargs):
    """
    带有重试机制的数据获取函数
    
    参数:
    func: 要调用的函数
    max_retries: 最大重试次数
    kwargs: 传递给func的参数
    
    返回:
    func的返回结果或空DataFrame
    """
    retry_delay = 2  # 初始延迟2秒
    
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            if attempt == max_retries - 1:
                print(f"尝试{max_retries}次后仍然失败: {e}")
                return pd.DataFrame()
                
            print(f"第{attempt+1}次请求失败: {e}，{retry_delay}秒后重试...")
            time.sleep(retry_delay)
            retry_delay *= 1.5  # 指数退避策略，增加重试间隔
    
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
    all_data = []
    
    # 由于API限制，每次请求不超过100支股票
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
                # 获取日线数据以补充成交额等信息
                df_daily = get_data_with_retry(pro.daily, ts_code=','.join(batch), trade_date=trade_date, 
                                           fields='ts_code,trade_date,open,high,low,close,vol,amount')
                
                # 合并同花顺数据和日线数据
                if not df_daily.empty:
                    df = pd.merge(df_flow_ths, df_daily, on=['ts_code', 'trade_date'], how='left')
                else:
                    df = df_flow_ths
                
                all_data.append(df)
                continue
            
            # 如果同花顺数据API返回为空，回退到使用普通资金流向API
            # 获取股票日线数据
            df_daily = get_data_with_retry(pro.daily, ts_code=','.join(batch), trade_date=trade_date, 
                                        fields='ts_code,trade_date,open,high,low,close,vol,amount')
            
            # 获取股票资金流向数据
            df_flow = get_data_with_retry(pro.moneyflow, ts_code=','.join(batch), trade_date=trade_date)
            
            # 获取股票基本信息
            df_basic = get_data_with_retry(pro.daily_basic, ts_code=','.join(batch), trade_date=trade_date, 
                                        fields='ts_code,turnover_rate,volume_ratio,pe,pb')
            
            # 合并数据
            if not df_daily.empty and not df_flow.empty:
                # 合并日线数据和资金流向数据
                df = pd.merge(df_daily, df_flow, on=['ts_code', 'trade_date'], how='inner')
                if not df_basic.empty:
                    df = pd.merge(df, df_basic, on=['ts_code'], how='left')
                
                # 获取股票名称
                stock_names = get_data_with_retry(pro.stock_basic, ts_code=','.join(batch), 
                                                fields='ts_code,name')
                
                if not stock_names.empty:
                    df = pd.merge(df, stock_names, on=['ts_code'], how='left')
                
                # 计算净流入
                if 'buy_amount' in df.columns and 'sell_amount' in df.columns:
                    df['net_amount'] = df['buy_amount'] - df['sell_amount']
                
                all_data.append(df)
        
        except Exception as e:
            print(f"获取股票数据时出错: {e}")
    
    # 合并所有批次的数据
    if all_data:
        result_df = pd.concat(all_data)
        
        # 打印数据列名，帮助调试
        print(f"数据列名: {result_df.columns.tolist()}")
        
        return result_df
    else:
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
    
    # 按净流入金额排序
    top_stocks = df_flow.sort_values('net_amount', ascending=False).head(top_n)
    
    # 打印资金净流入排名靠前的股票
    print(f"资金净流入排名前{top_n}的股票:")
    for i, (idx, row) in enumerate(top_stocks.iterrows(), 1):
        stock_name = row['name'] if 'name' in row else row['ts_code']
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
    
    # 检查是否存在净流入金额列和成交额列
    if 'net_amount' not in df_flow.columns:
        print("数据中缺少net_amount列，尝试计算...")
        if 'buy_amount' in df_flow.columns and 'sell_amount' in df_flow.columns:
            df_flow['net_amount'] = df_flow['buy_amount'] - df_flow['sell_amount']
        else:
            print("无法计算净流入金额，无法进行分析")
            return pd.DataFrame()
    
    if 'amount' not in df_flow.columns:
        print("数据中缺少amount列，无法计算资金流入率")
        return pd.DataFrame()
    
    # 确保净流入金额和成交额为数值类型
    df_flow['net_amount'] = pd.to_numeric(df_flow['net_amount'], errors='coerce')
    df_flow['amount'] = pd.to_numeric(df_flow['amount'], errors='coerce')
    
    # 筛选成交额不为0的股票
    df_flow = df_flow[df_flow['amount'] > 0]
    
    # 计算资金流入率
    df_flow['inflow_rate'] = df_flow['net_amount'] / df_flow['amount'] * 100
    
    # 按资金流入率排序
    top_stocks = df_flow.sort_values('inflow_rate', ascending=False).head(top_n)
    
    # 打印资金流入率排名靠前的股票
    print(f"资金流入率排名前{top_n}的股票:")
    for i, (idx, row) in enumerate(top_stocks.iterrows(), 1):
        stock_name = row['name'] if 'name' in row else row['ts_code']
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
        print(f"图表已保存为 {filename}")
    
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
        print(f"图表已保存为 {filename}")
    
    # 显示图表
    if show_fig:
        plt.show()
    else:
        plt.close()

if __name__ == "__main__":
    # 分析全市场个股资金净流入情况
    net_inflow_top, inflow_rate_top = analyze_market_moneyflow(top_n=10) 