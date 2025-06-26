import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import datetime
from matplotlib.ticker import MaxNLocator
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 替换为您的Tushare API token
TUSHARE_TOKEN = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'

def get_stock_daily_basic(trade_date):
    """获取指定交易日的A股基本面数据"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    try:
        # 获取当日全部股票的行情数据
        df = pro.daily(trade_date=trade_date, fields='ts_code,trade_date,close,pct_chg')
        return df
    except Exception as e:
        print(f"获取股票数据失败: {e}")
        return None

def get_previous_trading_day(current_date):
    """获取前一个交易日期"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    try:
        # 获取当前日期的前一天作为结束日期
        date_obj = datetime.datetime.strptime(current_date, '%Y%m%d')
        end_date = (date_obj - datetime.timedelta(days=1)).strftime('%Y%m%d')
        
        # 获取最近10个交易日的日历
        trade_cal = pro.trade_cal(exchange='SSE', 
                                start_date=(date_obj - datetime.timedelta(days=10)).strftime('%Y%m%d'),
                                end_date=current_date,
                                fields='cal_date,is_open')
        
        # 按日期降序排序并筛选交易日
        trade_days = trade_cal[trade_cal['is_open'] == 1]['cal_date'].sort_values(ascending=False).tolist()
        
        # 找到小于当前日期的最近交易日
        for day in trade_days:
            if day < current_date:
                return day
                
        return None
    except Exception as e:
        print(f"获取前一交易日失败: {e}")
        return None

def get_trading_days(end_date, days=20):
    """获取截至指定日期的N个交易日列表"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    try:
        # 向前推30天，确保足够获取N个交易日
        date_obj = datetime.datetime.strptime(end_date, '%Y%m%d')
        start_date = (date_obj - datetime.timedelta(days=days*2)).strftime('%Y%m%d')
        
        # 获取交易日历
        trade_cal = pro.trade_cal(exchange='SSE', 
                               start_date=start_date,
                               end_date=end_date,
                               fields='cal_date,is_open')
        
        # 筛选交易日并按日期排序
        trade_days = trade_cal[trade_cal['is_open'] == 1]['cal_date'].sort_values().tolist()
        
        # 返回最近N个交易日
        return trade_days[-days:] if len(trade_days) >= days else trade_days
    except Exception as e:
        print(f"获取交易日列表失败: {e}")
        return []

def calculate_market_up_down_counts(df):
    """计算市场涨跌家数"""
    if df is None or df.empty:
        return None
    
    # 计算涨跌家数
    up_count = len(df[df['pct_chg'] > 0])  # 上涨家数
    flat_count = len(df[df['pct_chg'] == 0])  # 平盘家数
    down_count = len(df[df['pct_chg'] < 0])  # 下跌家数
    
    result = {
        '内地-上涨家数': up_count,
        '内地-平盘家数': flat_count,
        '内地-下跌家数': down_count
    }
    
    return result

def calculate_up_down_ratio(df):
    """计算上涨/下跌股票的比值"""
    if df is None or df.empty:
        return 0.0
    
    # 计算涨跌家数
    up_count = len(df[df['pct_chg'] > 0])  # 上涨家数
    down_count = len(df[df['pct_chg'] < 0])  # 下跌家数
    
    # 避免除以零的情况
    ratio = up_count / down_count if down_count > 0 else float('inf')
    
    return ratio

def plot_market_up_down_chart(data_current, data_previous, trade_date, prev_date):
    """绘制A股市场涨跌家数柱状图"""
    if data_current is None:
        print("无数据可绘制")
        return
    
    # 设置图表大小
    plt.figure(figsize=(12, 8))
    
    # 将日期格式从YYYYMMDD转换为YYYY-MM-DD以便显示
    current_date_formatted = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
    prev_date_formatted = f"{prev_date[:4]}-{prev_date[4:6]}-{prev_date[6:]}"
    
    # 数据准备
    categories = list(data_current.keys())
    current_values = list(data_current.values())
    prev_values = list(data_previous.values()) if data_previous else [0, 0, 0]
    
    # 设置柱状图位置
    bar_width = 0.35
    index = range(len(categories))
    
    # 绘制柱状图
    bars1 = plt.bar([i for i in index], current_values, bar_width, color=['red', 'yellow', 'green'], label=current_date_formatted)
    bars2 = plt.bar([i + bar_width for i in index], prev_values, bar_width, color=['#FF7F7F', '#FFFF99', '#90EE90'], label=prev_date_formatted)
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=12)
    
    for bar in bars2:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', fontsize=12)
    
    # 设置图表标题和标签
    plt.title('A股市场涨跌家数', fontsize=16)
    plt.ylabel('家数', fontsize=14)
    
    # 调整X轴
    plt.xticks([i + bar_width/2 for i in index], categories, fontsize=12)
    
    # 添加图例
    plt.legend(fontsize=12)
    
    # 调整Y轴，使其显示整数刻度
    ax = plt.gca()
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    
    # 添加网格线
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 保存图表
    plt.tight_layout()
    output_file = f'a_shares_up_down_{trade_date}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存为: {output_file}")
    
    # 显示图表
    plt.show()

def analyze_up_down_ratio(end_date=None, days=20, token=None, save_fig=True, show_fig=True):
    """
    分析过去N个交易日的上涨/下跌股票比值
    
    参数:
    end_date: 结束日期，格式'YYYYMMDD'，若为None则使用最近交易日
    days: 要分析的交易日天数，默认20天
    token: tushare API token
    save_fig: 是否保存图表，默认True
    show_fig: 是否显示图表，默认True
    
    返回:
    pd.DataFrame: 包含日期和上涨/下跌比值的数据框
    """
    if token:
        global TUSHARE_TOKEN
        TUSHARE_TOKEN = token
    
    # 获取日期范围
    if end_date is None:
        end_date = datetime.datetime.now().strftime('%Y%m%d')
    
    # 获取交易日列表
    trade_days = get_trading_days(end_date, days)
    
    if not trade_days:
        print("无法获取交易日数据")
        return None
    
    # 计算每个交易日的上涨/下跌比值
    ratio_data = []
    for date in trade_days:
        df = get_stock_daily_basic(date)
        ratio = calculate_up_down_ratio(df)
        ratio_data.append({
            'trade_date': date,
            'up_down_ratio': ratio
        })
    
    # 转换为DataFrame
    df_ratio = pd.DataFrame(ratio_data)
    df_ratio['trade_date'] = pd.to_datetime(df_ratio['trade_date'], format='%Y%m%d')
    
    # 绘制折线图
    if save_fig or show_fig:
        plt.figure(figsize=(12, 6))
        plt.plot(df_ratio['trade_date'], df_ratio['up_down_ratio'], marker='o', linewidth=2, markersize=8)
        
        # 设置标题和标签
        plt.title('A股市场上涨/下跌股票比值走势', fontsize=16, fontweight='bold')
        plt.ylabel('上涨/下跌比值', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # 设置日期格式
        plt.gcf().autofmt_xdate()
        
        # 添加水平参考线
        plt.axhline(y=1, color='r', linestyle='--', alpha=0.5)
        
        # 添加注释说明
        plt.annotate('比值=1 (上涨家数=下跌家数)', xy=(df_ratio['trade_date'].iloc[0], 1), 
                   xytext=(df_ratio['trade_date'].iloc[0], 1.2),
                   arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8),
                   fontsize=12)
        
        # 添加最新数据点的标注
        latest_date = df_ratio['trade_date'].iloc[-1]
        latest_ratio = df_ratio['up_down_ratio'].iloc[-1]
        plt.annotate(f'{latest_ratio:.2f}', 
                   xy=(latest_date, latest_ratio),
                   xytext=(latest_date, latest_ratio * 1.1),
                   arrowprops=dict(facecolor='blue', shrink=0.05, width=1.5, headwidth=8),
                   fontsize=12,
                   color='blue')
        
        # 美化图表
        plt.tight_layout()
        
        # 保存图表
        if save_fig:
            output_file = f'up_down_ratio_{end_date}.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"上涨/下跌比值走势图已保存为: {output_file}")
        
        # 显示图表
        if show_fig:
            plt.show()
        else:
            plt.close()
    
    return df_ratio

def main():
    # 获取当前日期（格式：YYYYMMDD）
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 也可以指定特定日期
    today = '20250327'  # 示例：2025年3月27日
    
    print(f"正在获取 {today} 的市场数据...")
    
    # 获取前一个交易日
    prev_trading_day = get_previous_trading_day(today)
    
    if prev_trading_day:
        print(f"前一个交易日是: {prev_trading_day}")
        
        # 获取当日和前一日的股票数据
        df_current = get_stock_daily_basic(today)
        df_previous = get_stock_daily_basic(prev_trading_day)
        
        # 计算涨跌家数
        counts_current = calculate_market_up_down_counts(df_current)
        counts_previous = calculate_market_up_down_counts(df_previous)
        
        # 打印统计结果
        print(f"\n{today} 市场统计:")
        if counts_current:
            for key, value in counts_current.items():
                print(f"{key}: {value}")
        
        print(f"\n{prev_trading_day} 市场统计:")
        if counts_previous:
            for key, value in counts_previous.items():
                print(f"{key}: {value}")
        
        # 绘制柱状图
        plot_market_up_down_chart(counts_current, counts_previous, today, prev_trading_day)
        
        # 计算并绘制过去20个交易日的上涨/下跌比值走势
        print("\n计算过去20个交易日的上涨/下跌比值...")
        df_ratio = analyze_up_down_ratio(end_date=today, days=20, show_fig=True)
        
        if df_ratio is not None:
            print("\n上涨/下跌比值统计:")
            print(df_ratio)
    else:
        print("无法获取前一个交易日")

if __name__ == "__main__":
    main() 
 