import tushare as ts # 导入tushare库用于获取金融数据
import pandas as pd # 导入pandas用于数据处理
import matplotlib.pyplot as plt # 导入matplotlib.pyplot用于绘制图表
import numpy as np # 导入numpy用于数值计算
from datetime import datetime, timedelta  # 导入日期处理相关模块
import time  # 用于重试间隔
import requests  # 用于捕获请求异常

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

def get_data_with_retry(func, max_retries=5, retry_delay=2, extended_wait=True, **kwargs):
    """
    带有重试机制的数据获取函数
    
    参数:
    func: 要调用的函数
    max_retries: 最大重试次数
    retry_delay: 初始重试延迟(秒)
    extended_wait: 是否在多次重试失败后启用长时间等待再尝试
    kwargs: 传递给func的参数
    
    返回:
    func的返回结果或空DataFrame
    """
    for attempt in range(max_retries):
        try:
            result = func(**kwargs)
            # 检查结果是否为空DataFrame
            if isinstance(result, pd.DataFrame) and result.empty:
                if attempt == max_retries - 1:
                    if extended_wait:
                        # 如果所有重试都失败且启用了长时间等待，则等待1分钟后再试一次
                        print(f"尝试{max_retries}次后获取到空数据，等待60秒后进行最后一次尝试...")
                        time.sleep(60)  # 等待1分钟
                        try:
                            result = func(**kwargs)
                            if not (isinstance(result, pd.DataFrame) and result.empty):
                                print("在额外等待后成功获取数据")
                                return result
                        except Exception as e:
                            print(f"额外等待后尝试仍然失败: {e}")
                    
                    print(f"尝试{max_retries}次后获取到空数据")
                    return pd.DataFrame()
                
                print(f"第{attempt+1}次请求返回空数据，{retry_delay:.1f}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # 指数退避策略
                continue
            
            return result
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                Exception) as e:
            if attempt == max_retries - 1:
                if extended_wait:
                    # 如果所有重试都失败且启用了长时间等待，则等待1分钟后再试一次
                    print(f"尝试{max_retries}次后仍然失败，等待60秒后进行最后一次尝试...")
                    time.sleep(60)  # 等待1分钟
                    try:
                        result = func(**kwargs)
                        print("在额外等待后成功获取数据")
                        return result
                    except Exception as e:
                        print(f"额外等待后尝试仍然失败: {e}")
                
                print(f"尝试{max_retries}次后仍然失败: {e}")
                return pd.DataFrame()
                
            print(f"第{attempt+1}次请求失败: {e}，{retry_delay:.1f}秒后重试...")
            time.sleep(retry_delay)
            retry_delay *= 1.5  # 指数退避策略，增加重试间隔
    
    return pd.DataFrame()

def plot_index_performance(index_names=None, start_date=None, end_date=None, save_fig=True, show_fig=True, token=None):
    """
    绘制指数涨跌幅排行柱状图
    
    参数:
    index_names (dict): 指数代码到中文名称的映射字典，默认为None，会使用预定义的字典
    start_date (str): 开始日期，格式为'YYYYMMDD'，默认为None，会使用结束日期前7天
    end_date (str): 结束日期，格式为'YYYYMMDD'，默认为None，会使用当前日期
    save_fig (bool): 是否保存图片，默认为True
    show_fig (bool): 是否显示图表，默认为True
    token (str): tushare API token，若为None则使用默认token
    
    返回:
    pandas.DataFrame: 包含指数涨跌幅数据的DataFrame
    """
    # 设置默认指数映射（如果未提供）
    if index_names is None:
        index_names = {
            '000001.SH': '上证指数',
            '399001.SZ': '深证成指',
            '000016.SH': '上证50',
            '000300.SH': '沪深300',
            '000905.SH': '中证500',
            '399006.SZ': '创业板指',
            '000688.SH': '科创50',
            '399673.SZ': '创业板50'
        }
    
    # 设置默认日期（如果未提供）
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')
    
    if start_date is None:
        # 默认查询最近7天的数据
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=7)).strftime('%Y%m%d')
    
    # 初始化tushare API
    if token is None:
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
    pro = ts.pro_api(token)

    # 获取指数列表
    index_list = list(index_names.keys())
    
    # 用for循环，获取每一个指数的数据
    df_list = []
    for index_code in index_list:
        try:
            # 使用带重试机制的函数获取指数数据
            df_index = get_data_with_retry(pro.index_daily, ts_code=index_code, start_date=start_date, end_date=end_date)
            if not df_index.empty:
                df_list.append(df_index)
            else:
                print(f"警告: 无法获取指数 {index_code} 的数据")
        except Exception as e:
            print(f"获取指数 {index_code} 数据时出错: {e}")
    
    # 检查是否获取到数据
    if not df_list:
        print("错误: 未能获取任何指数数据")
        return pd.DataFrame()
    
    # 将df_list中的数据合并成一个DataFrame
    df = pd.concat(df_list)
    
    # 确保获取的是最近一个交易日的数据
    latest_date = df['trade_date'].max()
    df = df[df['trade_date'] == latest_date]
    print(f"使用交易日期: {latest_date} 的数据")
    
    # 如果数据过滤后为空，则返回空DataFrame
    if df.empty:
        print("错误: 过滤后数据为空")
        return pd.DataFrame()

    # 将vol列和amount列的结果除以相应数值调整单位
    if 'vol' in df.columns:
        df['vol'] = df['vol'] / 10000  # 单位从手变成万手
    if 'amount' in df.columns:
        df['amount'] = df['amount'] / 100000  # 单位从千元变成亿元

    # 将pct_chg列结果除以100转换为小数
    if 'pct_chg' in df.columns:
        df['pct_chg'] = df['pct_chg'] / 100
    else:
        print("错误: 数据中没有'pct_chg'列")
        return df

    # 添加中文名称列
    df['index_name'] = df['ts_code'].map(index_names)

    # 按涨跌幅从大到小排序
    df = df.sort_values('pct_chg', ascending=False)

    # 绘制柱状图前检查数据
    print("绘图数据预览：")
    print(df[['index_name', 'pct_chg']].to_string())
    print(f"最大值: {df['pct_chg'].max():.4f}, 最小值: {df['pct_chg'].min():.4f}")

    if show_fig or save_fig:
        # 设置更合适的图表大小
        plt.figure(figsize=(16, 9))

        # 使用中文名称和排序后的数据绘制柱状图
        bars = plt.bar(df['index_name'], df['pct_chg'], width=0.6)

        # 设置柱子颜色：红色表示正值，绿色表示负值（符合A股习惯）
        for i, bar in enumerate(bars):
            bar_height = bar.get_height()
            if bar_height >= 0:
                bar.set_color('#F63366')  # 红色（上涨）
            else:
                bar.set_color('#09B552')  # 绿色（下跌）
            
            # 修改标签位置，确保可见
            label_offset = max(0.0008, abs(bar_height) * 0.05)  # 动态计算标签偏移量
            
            # 在柱状图上添加标签
            if bar_height >= 0:
                plt.text(bar.get_x() + bar.get_width()/2, bar_height + label_offset, 
                        f'+{bar_height:.2%}', ha='center', va='bottom', fontsize=10)
            else:
                plt.text(bar.get_x() + bar.get_width()/2, bar_height - label_offset, 
                        f'{bar_height:.2%}', ha='center', va='top', fontsize=10)

        # 添加标题和标签
        formatted_date = datetime.strptime(latest_date, '%Y%m%d').strftime('%Y-%m-%d')
        plt.title(f'{formatted_date} 主要指数涨跌幅排行', fontsize=16, pad=15)
        plt.ylabel('涨跌幅', fontsize=12)

        # 添加网格线
        plt.grid(axis='y', linestyle='--', alpha=0.6)

        # 设置x轴标签
        plt.xticks(rotation=30, fontsize=10, ha='right')

        # 美化背景和边框
        plt.gca().spines['top'].set_visible(False)  # 去掉上边框
        plt.gca().spines['right'].set_visible(False)  # 去掉右边框

        # 添加均值线 - 安全检查
        mean_value = df['pct_chg'].mean()
        if not np.isnan(mean_value) and not np.isinf(mean_value):
            plt.axhline(y=mean_value, color='#6A5ACD', linestyle='--', alpha=0.8)
            plt.text(len(df)-0.5, mean_value, f'平均: {mean_value:.2%}', 
                    ha='right', va='bottom' if mean_value >= 0 else 'top', color='#6A5ACD')

        # 添加0线
        plt.axhline(y=0, color='black', alpha=0.3)

        # 调整y轴范围，确保所有柱子和标签完全可见 - 安全检查
        max_val = df['pct_chg'].max()
        min_val = df['pct_chg'].min()
        
        if not (np.isnan(max_val) or np.isnan(min_val) or np.isinf(max_val) or np.isinf(min_val)):
            padding = max(abs(max_val), abs(min_val)) * 0.25  # 增大边距至25%
            # 确保y轴范围足够大
            y_max = max_val + padding
            y_min = min_val - padding
            plt.ylim(y_min, y_max)
        else:
            print("警告: 数据异常，使用默认Y轴范围")
            plt.ylim(-0.05, 0.05)  # 使用默认范围

        # 美化y轴刻度为百分比格式
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.2%}'.format(y)))

        # 添加数据来源和日期
        plt.figtext(0.02, 0.02, f'数据来源: 东方财富 | 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                    ha='left', fontsize=8, alpha=0.6)

        # 使用紧凑布局但预留足够空间
        plt.tight_layout(pad=2.0)

        # 保存图片 - 先保存后显示
        if save_fig:
            filename = f'index_performance_{latest_date}.png'
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"图表已保存为 {filename}")

        # 显示图表
        if show_fig:
            plt.show()
        else:
            plt.close()
    
    return df

# 如果作为主程序运行
if __name__ == "__main__":
    # 调用函数获取指数数据并绘制图表
    df = plot_index_performance()