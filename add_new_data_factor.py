import pandas as pd
import tushare as ts
import numpy as np
import time
from datetime import datetime

# 设置tushare的token
ts.set_token('bc635143344483cee2e990d64c8d356a6f50f5786e6918ff7001b524')
pro = ts.pro_api()

# 读取已有的日行情数据
print("正在读取已有的日行情数据...")
daily_data = pd.read_csv('all_stocks_daily_data_2020_2024.csv')
# 确保trade_date列的类型一致
daily_data['trade_date'] = daily_data['trade_date'].astype(str)

# 获取所有上市公司的股票代码列表
stock_list = pro.stock_basic(
    exchange='',      # 交易所代码，空字符串表示获取所有交易所
    list_status='L',  # 股票状态：L-上市，D-退市，P-暂停上市
    fields='ts_code'  # 只获取股票代码字段
)['ts_code'].tolist()

print(f"开始获取总市值数据，共{len(stock_list)}只股票")

# 设置数据获取的时间范围
start_date = '20200101'  # 开始日期：2020年1月1日
end_date = '20241231'    # 结束日期：2024年12月31日

# 创建一个空的DataFrame，用于存储所有股票的总市值数据
market_cap_data = pd.DataFrame()

# 初始化计数器
request_count = 0
last_reset_time = time.time()

# 遍历每只股票，获取其总市值数据
for i, stock in enumerate(stock_list, 1):
    print(f"正在获取第{i}/{len(stock_list)}只股票的总市值数据: {stock}")
    try:
        # 检查是否需要暂停
        if request_count >= 195:
            current_time = time.time()
            elapsed_time = current_time - last_reset_time
            if elapsed_time < 60:  # 如果距离上次重置不到1分钟
                sleep_time = 60 - elapsed_time
                print(f"已达到访问限制，等待 {sleep_time:.1f} 秒...")
                time.sleep(sleep_time)
            request_count = 0
            last_reset_time = time.time()
            print("继续获取数据...")

        # 获取单只股票的每日总市值数据
        df = pro.daily_basic(ts_code=stock, 
                           start_date=start_date, 
                           end_date=end_date,
                           fields='ts_code,trade_date,total_mv')  # 只获取总市值字段
        
        if df is not None and not df.empty:
            # 确保trade_date列的类型一致
            df['trade_date'] = df['trade_date'].astype(str)
            market_cap_data = pd.concat([market_cap_data, df], ignore_index=True)
        
        # 增加请求计数
        request_count += 1
        
    except Exception as e:
        print(f"获取股票 {stock} 的总市值数据时出错: {str(e)}")
        continue

# 将总市值数据与日行情数据合并
print("正在合并数据...")
merged_data = pd.merge(daily_data, 
                      market_cap_data,
                      on=['ts_code', 'trade_date'],  # 按照股票代码和交易日期合并
                      how='left')  # 使用左连接，保留所有日行情数据

# 检查是否有缺失值
missing_count = merged_data['total_mv'].isnull().sum()
print(f"总市值数据缺失数量: {missing_count}")

# 保存合并后的数据
merged_data.to_csv('all_stocks_daily_data_2020_2024_with_mv.csv', index=False)
print("数据合并完成！")

