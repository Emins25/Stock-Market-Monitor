# 市场监测系统
import tushare as ts # 导入tushare库用于获取金融数据
import pandas as pd # 导入pandas用于数据处理
import matplotlib.pyplot as plt # 导入matplotlib.pyplot用于绘制图表
import numpy as np # 导入numpy用于数值计算
from datetime import datetime, timedelta  # 导入日期处理相关模块
from plot_index_performance import plot_index_performance
from plot_industry_moneyflow import plot_industry_moneyflow

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

pro = ts.pro_api('284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736')

## 1. 取每天主要指数的涨跌幅并生成柱状图
# 获取今天的日期
end_date = datetime.now().strftime('%Y%m%d')
start_date = end_date

# 定义指数名称字典，用于显示中文名称
index_names = {
    '399300.SZ': '沪深300',
    '000001.SH': '上证指数',
    '399001.SZ': '深证成指',
    '000688.SH': '科创50',
    '399006.SZ': '创业板指',
    '399905.SZ': '中证500',
    '399852.SZ': '中证1000'
}


df1 = plot_index_performance(index_names, start_date, end_date, save_fig=True)

print(df1)


# 2. 获取行业资金流向
df2 = plot_industry_moneyflow(date=end_date, top_n=10, save_fig=True, show_fig=True)

print(df2)


