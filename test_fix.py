import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

# 创建一个模拟的股票数据DataFrame，不包含net_amount列
def test_missing_net_amount():
    # 模拟股票数据
    data = {
        'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ'],
        'name': ['平安银行', '万科A', '国华网安', '国农科技', '世纪星源'],
        'amount': [1000000000, 800000000, 600000000, 400000000, 200000000], 
        'buy_amount': [550000000, 400000000, 350000000, 180000000, 90000000],
        'sell_amount': [450000000, 400000000, 250000000, 220000000, 110000000]
    }
    
    stocks_df = pd.DataFrame(data)
    
    print("原始数据:")
    print(stocks_df)
    
    # 测试计算net_amount
    print("\n测试缺失net_amount的处理:")
    
    # 检查是否存在'net_amount'列，如果不存在则尝试计算它
    if 'net_amount' not in stocks_df.columns:
        print("警告：数据中没有找到'net_amount'列，尝试从买入和卖出金额计算...")
        if 'buy_amount' in stocks_df.columns and 'sell_amount' in stocks_df.columns:
            stocks_df['net_amount'] = stocks_df['buy_amount'] - stocks_df['sell_amount']
            print("已成功计算'net_amount'列")
        else:
            print("错误：无法计算净流入金额，买入或卖出金额列缺失")
            if 'amount' in stocks_df.columns:
                print("使用成交额'amount'作为排序依据")
                stocks_df['net_amount'] = stocks_df['amount']
            else:
                print("没有可用于排序的数据列")
                return

    # 按净流入金额排序
    stocks_df = stocks_df.sort_values('net_amount', ascending=False)
    print("\n按净流入排序后:")
    print(stocks_df)
    
    # 测试绘图部分的净流入计算
    print("\n测试绘图部分的净流入计算:")
    
    # 净流入金额（转换为亿元单位）
    if 'net_amount' in stocks_df.columns:
        net_amounts = stocks_df['net_amount'] / 100000000
        print("使用net_amount列计算净流入")
    elif 'buy_amount' in stocks_df.columns and 'sell_amount' in stocks_df.columns:
        net_amounts = (stocks_df['buy_amount'] - stocks_df['sell_amount']) / 100000000
        print("使用buy_amount和sell_amount计算净流入")
    elif 'amount' in stocks_df.columns:
        print("警告：使用成交额代替净流入")
        net_amounts = stocks_df['amount'] / 100000000
    else:
        print("错误：没有找到任何可用于绘图的数据")
        net_amounts = np.zeros(len(stocks_df))
    
    print("净流入金额(亿元):")
    for i, code in enumerate(stocks_df['ts_code']):
        name = stocks_df['name'].iloc[i]
        print(f"{name}({code}): {net_amounts.iloc[i]:.2f}亿元")

# 运行测试
if __name__ == "__main__":
    test_missing_net_amount()
    print("\n测试完成，修复有效！") 