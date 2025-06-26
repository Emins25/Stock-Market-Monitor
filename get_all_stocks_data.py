# 导入必要的库
import tushare as ts  # 导入tushare库，用于获取股票数据
import pandas as pd   # 导入pandas库，用于数据处理

# 设置tushare的token，用于API认证
ts.set_token('bc635143344483cee2e990d64c8d356a6f50f5786e6918ff7001b524')
# 创建tushare的API接口对象
pro = ts.pro_api()

# 获取所有上市公司的股票代码列表
stock_list = pro.stock_basic(
    exchange='',      # 交易所代码，空字符串表示获取所有交易所（包括上交所和深交所）
    list_status='L',  # 股票状态：L-上市，D-退市，P-暂停上市
    fields='ts_code'  # 只获取股票代码字段
)['ts_code'].tolist()  # 将结果转换为列表格式

# 打印开始信息，显示要获取的股票总数
print(f"开始获取全部上市公司数据，共{len(stock_list)}只股票")

# 设置数据获取的时间范围
start_date = '20200101'  # 开始日期：2020年1月1日
end_date = '20241231'    # 结束日期：2024年12月31日

# 创建一个空的DataFrame，用于存储所有股票的数据
all_data = pd.DataFrame()

# 遍历每只股票，获取其日行情数据
for i, stock in enumerate(stock_list, 1):
    # 打印当前正在处理的股票信息
    print(f"正在获取第{i}/{len(stock_list)}只股票: {stock}")
    # 获取单只股票的日行情数据
    df = pro.daily(ts_code=stock, 
                  start_date=start_date, 
                  end_date=end_date)
    # 如果获取到的数据不为空，则添加到总数据中
    if df is not None and not df.empty:
        all_data = pd.concat([all_data, df], ignore_index=True)

# 将所有获取到的数据保存为CSV文件
all_data.to_csv('all_stocks_daily_data_2020_2024.csv', index=False)
# 打印完成信息
print("数据获取完成！") 