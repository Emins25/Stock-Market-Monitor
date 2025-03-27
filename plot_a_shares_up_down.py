import tushare as ts
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from matplotlib.ticker import MaxNLocator

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 替换为您的Tushare API token
TUSHARE_TOKEN = "替换为您的Tushare token"

def get_trading_day_stocks_status(date_str):
    """获取指定交易日的股票涨跌情况"""
    pro = ts.pro_api(TUSHARE_TOKEN)
    
    try:
        # 获取当日全部股票的行情数据
        df = pro.daily_basic(trade_date=date_str, fields='ts_code,trade_date,close,pct_chg')
        
        if df is None or df.empty:
            print(f"未获取到 {date_str} 的数据，可能是非交易日或数据尚未更新")
            return None
            
        # 计算涨跌家数
        up_count = len(df[df['pct_chg'] > 0])
        flat_count = len(df[df['pct_chg'] == 0])
        down_count = len(df[df['pct_chg'] < 0])
        
        return {
            '上涨家数': up_count,
            '平盘家数': flat_count,
            '下跌家数': down_count
        }
    except Exception as e:
        print(f"获取数据时出错: {e}")
        return None

def plot_market_stats():
    """绘制指定日期的市场涨跌统计图"""
    # 根据图片中的数据，模拟两个交易日的数据
    # 如果想获取实际数据，可以使用上面的函数调用tushare API
    
    # 示例数据 - 与图片中保持一致
    day1 = '20250326'
    day2 = '20250325'
    
    # 方法1：直接使用图片中的数据
    stats_day1 = {
        '内地-上涨家数': 3602,
        '内地-平盘家数': 183,
        '内地-下跌家数': 1688
    }
    
    stats_day2 = {
        '内地-上涨家数': 2536,
        '内地-平盘家数': 167,
        '内地-下跌家数': 2769
    }
    
    # 方法2：如果要获取实时数据，取消下面的注释
    # stats_day1 = get_trading_day_stocks_status(day1)
    # stats_day2 = get_trading_day_stocks_status(day2)
    
    # 检查是否获取到数据
    if not stats_day1 or not stats_day2:
        print("无法获取足够的数据来绘制图表")
        return
    
    # 设置图表
    plt.figure(figsize=(14, 8))
    
    # 提取数据
    categories = list(stats_day1.keys())
    values_day1 = list(stats_day1.values())
    values_day2 = list(stats_day2.values())
    
    # 格式化日期显示
    day1_formatted = f"{day1[:4]}-{day1[4:6]}-{day1[6:]}"
    day2_formatted = f"{day2[:4]}-{day2[4:6]}-{day2[6:]}"
    
    # 设置柱状图位置
    x = range(len(categories))
    width = 0.35
    
    # 创建柱状图
    bars1 = plt.bar([i for i in x], values_day1, width, color=['#c20000', '#ffc000', '#92d050'], label=day1_formatted)
    bars2 = plt.bar([i + width for i in x], values_day2, width, color=['#ff7f7f', '#fff582', '#c5e0b4'], label=day2_formatted)
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 30,
                f'{int(height)}', ha='center', va='bottom', fontsize=12)
    
    for bar in bars2:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 30,
                f'{int(height)}', ha='center', va='bottom', fontsize=12)
    
    # 设置图表标题和标签
    plt.title('图 1: A股市场整体表现', fontsize=16, fontweight='bold')
    plt.ylabel('家数', fontsize=14)
    plt.ylim(0, 4500)  # 根据数据调整Y轴范围
    
    # 调整X轴标签
    plt.xticks([i + width/2 for i in x], categories, fontsize=12)
    
    # 移除上边框和右边框
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加图例
    plt.legend(fontsize=12)
    
    # 添加网格线
    plt.grid(axis='y', linestyle='-', alpha=0.2)
    
    # 保存图表
    plt.tight_layout()
    output_file = f'a_shares_market_performance_{day1}.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"图表已保存为: {output_file}")
    
    # 显示图表
    plt.show()

if __name__ == "__main__":
    plot_market_stats() 