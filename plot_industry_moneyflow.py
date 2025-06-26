#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
绘制行业资金流向图表
包括资金净流入最多和最少的行业
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tushare as ts
from datetime import datetime, timedelta
import time
import requests  # 用于捕获请求异常
import os  # 用于文件路径操作

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

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

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

def plot_industry_moneyflow(token=None, date=None, top_n=10, save_fig=True, show_fig=True):
    """
    绘制行业资金流向图表
    
    参数:
    token: tushare API token，若为None则使用默认token
    date: 要查询的日期，格式为'YYYYMMDD'，若为None则使用当前日期
    top_n: 显示资金净流入最多和最少的行业数量，默认为10
    save_fig: 是否保存图片，默认为True
    show_fig: 是否显示图表，默认为True
    
    返回:
    pandas.DataFrame: 包含行业资金流向数据的DataFrame
    """
    # 初始化tushare API
    if token is None:
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
    
    pro = ts.pro_api(token)
    
    # 获取查询日期
    if date is None:
        date = get_latest_trade_date(pro)
    
    # 尝试获取当天数据
    print(f"尝试获取 {date} 的行业资金流向数据")
    df = get_data_with_retry(pro.moneyflow_ind_ths, trade_date=date)

    # 如果数据为空，尝试获取前一天的数据
    if df.empty and date is None:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        print(f"当天数据为空，尝试获取 {yesterday} 的数据")
        df = get_data_with_retry(pro.moneyflow_ind_ths, trade_date=yesterday)
        date = yesterday

    # 如果数据仍为空，再尝试前一天
    if df.empty and date is None:
        day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime('%Y%m%d')
        print(f"前一天数据也为空，尝试获取 {day_before_yesterday} 的数据")
        df = get_data_with_retry(pro.moneyflow_ind_ths, trade_date=day_before_yesterday)
        date = day_before_yesterday

    # 检查数据是否为空
    if df.empty:
        print("无法获取数据，请检查网络连接或API调用限制。")
        # 使用测试数据（如果API调用失败）
        print("使用测试数据进行展示...")
        # 创建测试数据
        test_data = {
            'industry': ['电子设备', '软件服务', '医药制造', '银行', '食品饮料', '汽车制造', '电力设备', '房地产', '钢铁', '化工', 
                         '农林牧渔', '建筑建材', '商业贸易', '家用电器', '传媒', '纺织服装', '交通运输', '综合', '有色金属', '国防军工'],
            'net_amount': [5.67, 4.23, 3.89, -2.45, 2.11, -1.78, 1.56, -1.32, 0.89, -0.76,
                            -0.65, 0.54, -0.43, 0.37, -0.31, 0.25, -0.21, 0.15, -0.12, 0.08]
        }
        df = pd.DataFrame(test_data)
        date = datetime.now().strftime('%Y%m%d')

    print("获取到的数据：")
    print(df.head())
    print(f"数据列名: {df.columns.tolist()}")
    print(f"共获取到 {len(df)} 条记录")

    # 添加行业名称字典，如果可能的话，转换行业代码为行业名称
    # 检查列名是否存在
    if 'industry' in df.columns:
        df['display_name'] = df['industry']
    elif 'ts_code' in df.columns:
        df['display_name'] = df['ts_code']
    else:
        # 如果没有可用的显示列，使用索引
        df['display_name'] = [f"行业{i+1}" for i in range(len(df))]

    # 将净流入金额直接使用，因为已经是亿为单位
    if 'net_amount' in df.columns:
        # 确保净流入金额为数值类型
        df['net_amount'] = pd.to_numeric(df['net_amount'], errors='coerce')
        df['net_amount_yiyuan'] = df['net_amount']  # 已经是亿元单位
        
        # 按净流入金额从大到小排序
        df = df.sort_values('net_amount', ascending=False)
        
        # 计算行业总数量
        total_industries = len(df)
        print(f"总行业数量: {total_industries}")
        
        # 只保留净流入最多的top_n个和最少的top_n个行业
        if total_industries > top_n * 2:
            top = df.head(top_n)
            bottom = df.tail(top_n)
            # 合并数据
            df_plot = pd.concat([top, bottom])
            print(f"只显示前{top_n}和后{top_n}，共{len(df_plot)}个行业")
        else:
            df_plot = df
            print(f"行业数量较少，显示全部{len(df_plot)}个行业")
        
        if show_fig or save_fig:
            # 设置更好的图表大小
            plt.figure(figsize=(16, 10))

            # 使用柱状图显示结果，使用更友好的颜色
            bars = plt.bar(df_plot['display_name'], df_plot['net_amount_yiyuan'], width=0.6)

            # 设置颜色：红色表示正值（净流入），绿色表示负值（净流出）
            for i, bar in enumerate(bars):
                if bar.get_height() >= 0:
                    bar.set_color('#F63366')  # 红色
                else:
                    bar.set_color('#09B552')  # 绿色

            # 添加数据标签
            for i, bar in enumerate(bars):
                height = bar.get_height()
                if height >= 0:
                    plt.text(bar.get_x() + bar.get_width()/2., height + 0.1, 
                            f"+{height:.2f}", ha='center', va='bottom', fontsize=9)
                else:
                    plt.text(bar.get_x() + bar.get_width()/2., height - 0.1, 
                            f"{height:.2f}", ha='center', va='top', fontsize=9)

            # 格式化日期
            formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else date
            
            # 添加标题和标签
            plt.title(f"{formatted_date} 行业资金净流入排行(前{top_n}与后{top_n})", fontsize=18, pad=15)
            plt.xlabel('行业', fontsize=14, labelpad=10)
            plt.ylabel('净流入金额（亿元）', fontsize=14, labelpad=10)

            # 设置x轴标签
            plt.xticks(rotation=45, ha='right', fontsize=10)

            # 添加网格线
            plt.grid(axis='y', linestyle='--', alpha=0.6)

            # 美化图表
            plt.gca().spines['top'].set_visible(False)  # 去掉上边框
            plt.gca().spines['right'].set_visible(False)  # 去掉右边框

            # 添加均值线 - 安全检查
            mean_value = df_plot['net_amount_yiyuan'].mean()
            if not np.isnan(mean_value) and not np.isinf(mean_value):
                plt.axhline(y=mean_value, color='#6A5ACD', linestyle='--', alpha=0.8)
                plt.text(len(df_plot)-1, mean_value, f'平均: {mean_value:.2f}亿', 
                        ha='right', va='bottom' if mean_value >= 0 else 'top', color='#6A5ACD')

            # 添加零线
            plt.axhline(y=0, color='black', alpha=0.3)

            # 调整y轴范围 - 安全检查
            max_value = df_plot['net_amount_yiyuan'].max()
            min_value = df_plot['net_amount_yiyuan'].min()
            
            if not (np.isnan(max_value) or np.isnan(min_value) or np.isinf(max_value) or np.isinf(min_value)):
                y_padding = max(abs(max_value), abs(min_value)) * 0.15
                plt.ylim(min_value - y_padding, max_value + y_padding)
            else:
                print("警告：数据中存在NaN或Inf值，无法设置自动Y轴范围，使用默认范围")
                plt.ylim(-1, 1)  # 使用默认范围

            # 添加数据来源和日期
            plt.figtext(0.02, 0.02, f"数据来源: 同花顺 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 显示前{top_n}和后{top_n}行业", 
                        ha='left', fontsize=8, alpha=0.6)

            # 优化布局
            plt.tight_layout(pad=2.0)

            # 保存图片
            if save_fig:
                filename = f'industry_moneyflow_top_bottom_{date}.png'
                plt.savefig(filename, dpi=300, bbox_inches='tight')
                print(f"图表已保存为 {os.path.abspath(filename)}")

            # 显示图表
            if show_fig:
                plt.show()
            else:
                plt.close()

        return df
    else:
        print("数据中不包含'net_amount'列，无法绘制图表")
        print("可用的列名:", df.columns.tolist())
        return df

# 如果作为主程序运行
if __name__ == "__main__":
    # 调用函数获取行业资金流向数据并绘制图表
    df = plot_industry_moneyflow(top_n=10)

