import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import time

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 替换为您的Tushare API token
TUSHARE_TOKEN = "替换为您的Tushare token"

def get_latest_trading_day():
    """获取最近的交易日"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 获取最近10个交易日，以确保包含最新的交易日
    df = pro.trade_cal(exchange='SSE', start_date=(datetime.datetime.now() - datetime.timedelta(days=15)).strftime('%Y%m%d'), end_date=today)
    
    # 筛选交易日
    trading_days = df[df['is_open'] == 1]['cal_date'].tolist()
    if not trading_days:
        return None
    
    # 返回最近的交易日
    return trading_days[-1]

def get_trading_days(n=2):
    """获取最近n个交易日"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # 获取最近20个交易日，确保足够
    df = pro.trade_cal(exchange='SSE', start_date=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d'), end_date=today)
    
    # 筛选交易日
    trading_days = df[df['is_open'] == 1]['cal_date'].tolist()
    
    # 返回最近的n个交易日
    return trading_days[-n:]

def get_stocks_up_down_count(trade_date):
    """获取指定交易日的股票涨跌统计"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    try:
        # 获取交易日的所有股票行情数据
        df = pro.daily(trade_date=trade_date)
        
        if df is None or df.empty:
            print(f"未获取到{trade_date}的数据")
            return None
        
        # 计算涨跌统计
        up_count = len(df[df['pct_chg'] > 0])
        flat_count = len(df[df['pct_chg'] == 0])
        down_count = len(df[df['pct_chg'] < 0])
        
        return {
            '内地-上涨家数': up_count,
            '内地-平盘家数': flat_count,
            '内地-下跌家数': down_count
        }
    except Exception as e:
        print(f"获取数据失败: {e}")
        return None

def plot_a_shares_stats():
    """绘制A股市场涨跌家数统计图"""
    # 获取最近两个交易日
    trading_days = get_trading_days(2)
    
    if len(trading_days) < 2:
        print("无法获取足够的交易日数据")
        return
    
    print(f"获取最近两个交易日: {trading_days}")
    
    # 获取两个交易日的涨跌统计
    current_day_stats = get_stocks_up_down_count(trading_days[-1])
    previous_day_stats = get_stocks_up_down_count(trading_days[-2])
    
    if not current_day_stats or not previous_day_stats:
        print("无法获取完整的市场统计数据")
        return
    
    # 打印数据
    print(f"\n{trading_days[-1]} 市场统计:")
    for key, value in current_day_stats.items():
        print(f"{key}: {value}")
    
    print(f"\n{trading_days[-2]} 市场统计:")
    for key, value in previous_day_stats.items():
        print(f"{key}: {value}")
    
    # 绘制图表
    plt.figure(figsize=(12, 8))
    
    # 格式化日期显示
    current_date = f"{trading_days[-1][:4]}-{trading_days[-1][4:6]}-{trading_days[-1][6:]}"
    previous_date = f"{trading_days[-2][:4]}-{trading_days[-2][4:6]}-{trading_days[-2][6:]}"
    
    # 准备数据
    categories = list(current_day_stats.keys())
    current_values = list(current_day_stats.values())
    previous_values = list(previous_day_stats.values())
    
    # 设置柱状图位置
    bar_width = 0.35
    x = range(len(categories))
    
    # 绘制柱状图
    bars1 = plt.bar([i for i in x], current_values, bar_width, color=['red', 'yellow', 'green'], label=current_date)
    bars2 = plt.bar([i + bar_width for i in x], previous_values, bar_width, color=['#FF8080', '#FFFF99', '#90EE90'], label=previous_date)
    
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
    plt.title('A股市场整体表现', fontsize=16, fontweight='bold')
    plt.ylabel('家数', fontsize=14)
    
    # 调整X轴标签
    plt.xticks([i + bar_width/2 for i in x], categories, fontsize=12)
    
    # 设置图例
    plt.legend(fontsize=12)
    
    # 添加网格线
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # 保存图表
    plt.tight_layout()
    output_file = f'a_shares_market_stats_{trading_days[-1]}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存为: {output_file}")
    
    # 显示图表
    plt.show()

if __name__ == "__main__":
    plot_a_shares_stats() 