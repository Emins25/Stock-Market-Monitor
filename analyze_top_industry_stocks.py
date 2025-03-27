import tushare as ts # 导入tushare库用于获取金融数据
import pandas as pd # 导入pandas用于数据处理
import matplotlib.pyplot as plt # 导入matplotlib.pyplot用于绘制图表
import numpy as np # 导入numpy用于数值计算
from datetime import datetime, timedelta  # 导入日期处理相关模块
import time  # 用于重试间隔
import requests  # 用于捕获请求异常
import plot_industry_moneyflow as pim  # 导入行业资金流向模块

# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置默认字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

"""
深入分析热点行业中的个股资金流向情况
拉取热点行业个股每日的资金净流入金额，识别热点行业中的热门个股，配合行业数据进行交叉验证
先根据Tushare的同花顺行业资金流向（THS）返回的行业对应的ts_code，使用Tushare的指数成分和权重API接口获取对应的成分股列表，获取成分股的con_code，
再利用con_code，使用Tusahre的个股资金流向（THS）API接口获取每支股票的单日资金净流入数据
根据净流入数据排序之后，取前十名画柱状图展示结果
"""

def get_top_stocks_by_industry(token=None, date=None, top_industry_count=3, top_stock_count=10, save_fig=True, show_fig=True):
    """
    分析净流入最高的前几个行业中，哪些股票的成交额和净流入额最高
    
    参数:
    token: tushare API token，若为None则使用默认token
    date: 要查询的日期，格式为'YYYYMMDD'，若为None则使用当前日期
    top_industry_count: 要分析的行业数量，默认为3
    top_stock_count: 每个行业要显示的股票数量，默认为10
    save_fig: 是否保存图片，默认为True
    show_fig: 是否显示图表，默认为True
    
    返回:
    dict: 包含各行业股票分析结果的字典
    """
    # 设置默认token
    if token is None:  # 如果没有提供token参数
        token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'  # 使用默认的tushare token
    
    # 初始化tushare API
    pro = ts.pro_api(token)  # 使用提供的token初始化tushare的pro API接口
    
    # 首先获取行业资金流向数据
    print("获取行业资金流向数据...")  # 打印提示信息
    industry_df = pim.plot_industry_moneyflow(token=token, date=date, show_fig=False, save_fig=False)  # 调用行业资金流向模块获取数据，不显示也不保存图表
    
    # 检查是否成功获取行业数据
    if industry_df.empty:  # 如果获取的DataFrame为空
        print("未能获取行业资金流向数据")  # 打印错误信息
        return {}  # 返回空字典
    
    # 获取查询日期
    if date is None:  # 如果没有提供日期参数
        # 尝试从获取的数据中提取交易日期，如果没有则使用当前日期
        trade_date = industry_df['trade_date'].iloc[0] if 'trade_date' in industry_df.columns else datetime.now().strftime('%Y%m%d')
    else:  # 如果提供了日期参数
        trade_date = date  # 直接使用提供的日期
    
    print(f"分析日期: {trade_date}")  # 打印当前分析的日期
    
    # 打印行业流向数据的可用列
    print(f"行业数据可用列: {industry_df.columns.tolist()}")
    
    # 检查并确保net_amount列存在
    if 'net_amount' not in industry_df.columns:
        print("警告: 行业数据中缺少net_amount列，尝试计算或使用替代列...")
        # 尝试从现有列计算net_amount
        if 'buy_amount' in industry_df.columns and 'sell_amount' in industry_df.columns:
            industry_df['net_amount'] = industry_df['buy_amount'] - industry_df['sell_amount']
            print("已从买入卖出金额计算净流入金额")
        elif 'amount' in industry_df.columns:
            # 如果没有买入卖出金额，使用总成交额作为替代
            industry_df['net_amount'] = industry_df['amount']
            print("警告: 使用总成交额作为净流入金额的替代")
        else:
            print("错误: 无法确定行业净流入金额，返回空结果")
            return {}
    
    # 获取净流入最高的前N个行业
    top_industries = industry_df.sort_values('net_amount', ascending=False).head(top_industry_count)  # 按净流入金额降序排序并取前N个
    
    print(f"净流入最高的{top_industry_count}个行业:")  # 打印标题
    for i, (idx, row) in enumerate(top_industries.iterrows(), 1):  # 遍历排名前N的行业
        # 获取行业名称（优先使用display_name，如果没有则使用industry）
        industry_name = row['display_name'] if 'display_name' in row else row['industry']
        
        # 根据net_amount的值范围判断单位
        net_val = row['net_amount']
        if isinstance(net_val, (int, float)) and abs(net_val) > 10000000:
            # 值很大，可能是原始单位，转换为亿元
            net_amount = net_val / 100000000
        else:
            # 值较小，可能已经是亿元单位或万元单位
            net_amount = net_val if abs(net_val) < 1000 else net_val / 10000
        
        print(f"{i}. {industry_name}: {net_amount:.2f}亿元")  # 打印行业排名、名称和净流入金额
    
    # 存储各行业的股票数据
    industry_stocks = {}  # 创建空字典用于存储各行业的股票数据
    
    # 遍历每个行业，获取其成分股的资金流向
    for i, (idx, industry) in enumerate(top_industries.iterrows(), 1):  # 遍历每个排名靠前的行业
        # 获取行业名称和代码
        industry_name = industry['display_name'] if 'display_name' in industry else industry['industry']
        industry_code = industry['ts_code'] if 'ts_code' in industry else None
        
        print(f"\n分析行业: {industry_name}")  # 打印当前正在分析的行业名称
        
        # 获取行业成分股
        stocks_in_industry = get_industry_stocks(pro, industry_code, trade_date)  # 调用函数获取该行业的所有股票
        
        if not stocks_in_industry:  # 如果没有找到该行业的股票
            print(f"未找到行业 {industry_name} 的成分股信息")  # 打印警告信息
            continue  # 跳过当前行业，继续下一个
        
        # 获取这些股票的资金流向数据
        stocks_data = get_stocks_moneyflow(pro, stocks_in_industry, trade_date)  # 调用函数获取股票的资金流向数据
        
        # 打印调试信息
        print(f"获取到 {len(stocks_data)} 条股票数据，列名: {stocks_data.columns.tolist() if not stocks_data.empty else '无数据'}")
        
        if stocks_data.empty:  # 如果获取的数据为空
            print(f"未能获取行业 {industry_name} 的股票资金流向数据")  # 打印警告信息
            continue  # 跳过当前行业，继续下一个
        
        # 检查是否存在'net_amount'列，如果不存在则尝试计算它
        if 'net_amount' not in stocks_data.columns:
            print(f"警告：数据中没有找到'net_amount'列，尝试从买入和卖出金额计算...")
            if 'buy_amount' in stocks_data.columns and 'sell_amount' in stocks_data.columns:
                stocks_data['net_amount'] = stocks_data['buy_amount'] - stocks_data['sell_amount']
                print("已成功计算'net_amount'列")
            else:
                print(f"错误：无法计算净流入金额，买入或卖出金额列缺失")
                if 'amount' in stocks_data.columns:
                    print("使用成交额'amount'作为排序依据")
                    stocks_data['net_amount'] = stocks_data['amount']
                else:
                    print("没有可用于排序的数据列，跳过此行业")
                    continue
                
        # 确保net_amount列是数值类型
        stocks_data['net_amount'] = pd.to_numeric(stocks_data['net_amount'], errors='coerce')
        
        # 按净流入金额排序
        stocks_data = stocks_data.sort_values('net_amount', ascending=False)  # 将股票按净流入金额从高到低排序
        
        # 保存前N支股票数据
        industry_stocks[industry_name] = stocks_data.head(top_stock_count)  # 取前N支股票保存到结果字典中
        
        # 绘制该行业前N支股票的净流入柱状图
        if show_fig or save_fig:  # 如果需要显示或保存图表
            plot_industry_top_stocks(industry_name, stocks_data.head(top_stock_count), 
                                     trade_date, i, top_industry_count, save_fig, show_fig)  # 调用函数绘制图表
    
    return industry_stocks  # 返回包含各行业股票数据的字典

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
    for attempt in range(max_retries):  # 在最大重试次数内尝试
        try:
            result = func(**kwargs)  # 尝试调用传入的函数并返回结果
            # 检查结果是否为空DataFrame
            if isinstance(result, pd.DataFrame) and result.empty:
                if attempt == max_retries - 1:  # 如果已经是最后一次尝试
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
                Exception) as e:  # 捕获网络相关异常
            if attempt == max_retries - 1:  # 如果已经是最后一次尝试
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
                
                print(f"尝试{max_retries}次后仍然失败: {e}")  # 打印失败信息
                return pd.DataFrame()  # 返回空DataFrame
                
            print(f"第{attempt+1}次请求失败: {e}，{retry_delay:.1f}秒后重试...")  # 打印重试信息
            time.sleep(retry_delay)  # 等待一段时间后重试
            retry_delay *= 1.5  # 指数退避策略，增加重试间隔
    
    return pd.DataFrame()  # 如果所有尝试都失败，返回空DataFrame

def get_industry_stocks(pro, industry_code, trade_date=None, retries=3, retry_delay=2):
    """
    获取行业成分股
    
    参数:
    pro: tushare pro API实例
    industry_code: 行业代码，格式为'881101.TI'
    trade_date: 交易日期，格式为'YYYYMMDD'，默认为None使用最近交易日
    retries: 重试次数
    retry_delay: 重试延迟(秒)
    
    返回:
    list: 行业成分股代码列表
    """
    print(f"获取行业 {industry_code} 的成分股...")
    
    try:
        # 注意: 根据测试结果，直接使用ths_member接口获取同花顺行业成分股效果更好
        # 不再尝试使用index_weight接口，减少API调用次数和等待时间
        stock_list = []
        
        for attempt in range(retries):
            try:
                # 直接使用ths_member获取成分股
                df = get_data_with_retry(pro.ths_member, ts_code=industry_code)
                
                if not df.empty:
                    stock_list = df['ts_code'].tolist()
                    print(f"通过ths_member成功获取到 {len(stock_list)} 支成分股")
                    return stock_list
                
                # 获取失败，等待后重试
                print(f"第{attempt+1}次尝试获取行业成分股失败，{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # 使用指数退避策略
            
            except Exception as e:
                print(f"获取行业成分股时出错: {e}")
                if attempt < retries - 1:
                    print(f"第{attempt+1}次尝试失败，{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
        
        # 如果所有尝试都失败，返回空列表
        print(f"尝试{retries}次后仍无法获取行业 {industry_code} 的成分股")
        return []
        
    except Exception as e:
        print(f"获取行业成分股时发生异常: {e}")
        return []

def get_stocks_moneyflow(pro, stock_list, trade_date):
    """
    获取多支股票的资金流向数据，一次请求一支股票
    
    参数:
    pro: tushare pro接口
    stock_list: 股票代码列表
    trade_date: 交易日期
    
    返回:
    DataFrame: 包含股票资金流向数据
    """
    all_data = []
    total_stocks = len(stock_list)
    
    # 改为逐个获取每支股票的数据，以提高成功率
    for i, stock_code in enumerate(stock_list):
        print(f"获取第 {i+1}/{total_stocks} 支股票 {stock_code} 的资金流向数据...")
        
        try:
            # 优先使用同花顺个股资金流向API，该接口提供完整的净流入数据
            print(f"使用同花顺个股资金流向(THS)API获取数据...")
            # 使用start_date和end_date参数替代trade_date参数
            df_flow_ths = get_data_with_retry(pro.moneyflow_ths, ts_code=stock_code, start_date=trade_date, end_date=trade_date)
            
            if not df_flow_ths.empty:
                print(f"成功获取同花顺资金流向数据")
                
                # 获取日线数据以补充成交额等信息
                df_daily = get_data_with_retry(pro.daily, ts_code=stock_code, trade_date=trade_date, 
                                            fields='ts_code,trade_date,open,high,low,close,vol,amount')
                
                # 合并同花顺数据和日线数据
                if not df_daily.empty:
                    df = pd.merge(df_flow_ths, df_daily, on=['ts_code', 'trade_date'], how='left')
                else:
                    df = df_flow_ths
                
                # 将净流入金额转换为万元单位以保持一致性
                if 'net_amount' in df.columns:
                    df['net_amount'] = pd.to_numeric(df['net_amount'], errors='coerce')
                    # 检查单位：同花顺API返回的net_amount单位为万元
                    print(f"净流入金额: {df['net_amount'].iloc[0]} (单位:万元)")
                
                all_data.append(df)
                
                # 成功获取数据后等待短暂时间，避免API限制
                time.sleep(0.5)
                continue  # 继续下一支股票
            else:
                print(f"同花顺资金流向数据获取失败，尝试使用其他API...")
            
            # 如果同花顺数据API返回为空，回退到使用普通资金流向API
            print(f"使用标准资金流向API获取数据...")
            
            # 获取股票日线数据
            df_daily = get_data_with_retry(pro.daily, ts_code=stock_code, trade_date=trade_date, 
                                        fields='ts_code,trade_date,open,high,low,close,vol,amount')
            
            # 获取股票资金流向数据
            df_flow = get_data_with_retry(pro.moneyflow, ts_code=stock_code, trade_date=trade_date)
            
            # 获取股票基本信息
            df_basic = get_data_with_retry(pro.daily_basic, ts_code=stock_code, trade_date=trade_date, 
                                        fields='ts_code,turnover_rate,volume_ratio,pe,pb')
            
            # 合并数据
            if not df_daily.empty and not df_flow.empty:
                # 合并日线数据和资金流向数据
                df = pd.merge(df_daily, df_flow, on=['ts_code', 'trade_date'], how='inner')
                if not df_basic.empty:
                    df = pd.merge(df, df_basic, on=['ts_code'], how='left')
                
                # 获取股票名称
                stock_names = get_data_with_retry(pro.stock_basic, ts_code=stock_code, 
                                                fields='ts_code,name')
                
                if not stock_names.empty:
                    df = pd.merge(df, stock_names, on=['ts_code'], how='left')
                
                # 计算净流入
                if 'buy_amount' in df.columns and 'sell_amount' in df.columns:
                    df['net_amount'] = df['buy_amount'] - df['sell_amount']
                    print(f"从买入卖出金额计算净流入")
                
                all_data.append(df)
            else:
                print(f"未能获取股票 {stock_code} 的数据")
        
        except Exception as e:
            print(f"获取股票 {stock_code} 数据时出错: {e}")
        
        # 每个股票请求后添加短暂延迟，避免频繁请求触发API限制
        time.sleep(1)
        
        # 每获取10支股票后休息5秒，以避免API频率限制
        if (i + 1) % 10 == 0 and i + 1 < total_stocks:
            rest_time = 5
            print(f"已获取{i + 1}支股票数据，休息{rest_time}秒后继续...")
            time.sleep(rest_time)
    
    # 合并所有股票的数据
    if all_data:
        result_df = pd.concat(all_data)
        print(f"成功获取 {len(result_df)} 条股票资金流向数据")
        
        # 打印数据列名，帮助调试
        print(f"数据列名: {result_df.columns.tolist()}")
        
        return result_df
    else:
        return pd.DataFrame()

def plot_industry_top_stocks(industry_name, stocks_df, trade_date, industry_rank, total_industries, save_fig=True, show_fig=True):
    """
    绘制行业内部前N支股票的净流入柱状图
    
    参数:
    industry_name: 行业名称
    stocks_df: 股票数据DataFrame
    trade_date: 交易日期
    industry_rank: 行业排名
    total_industries: 总行业数
    save_fig: 是否保存图片
    show_fig: 是否显示图表
    """
    if stocks_df.empty:  # 如果传入的股票数据为空
        print(f"行业 {industry_name} 没有可用的股票数据来绘制图表")  # 打印警告信息
        return  # 直接返回，不绘制图表
    
    # 打印初始数据信息，帮助调试
    print(f"绘制图表前的数据列名: {stocks_df.columns.tolist()}")
    
    # 设置图表大小
    plt.figure(figsize=(16, 10))  # 创建16x10英寸的图表
    
    # 准备绘图数据
    stock_names = []  # 创建空列表用于存储股票显示名称
    for idx, row in stocks_df.iterrows():  # 遍历每支股票的数据
        # 使用股票名称和代码
        name = row['name'] if 'name' in row and pd.notna(row['name']) else ''  # 获取股票名称，如果不存在则为空字符串
        code = row['ts_code'] if 'ts_code' in row else ''  # 获取股票代码，如果不存在则为空字符串
        
        if name:  # 如果股票名称存在
            display_name = f"{name}({code.split('.')[0]})"  # 格式化为"名称(代码)"的形式，去掉代码中的交易所后缀
        else:
            display_name = code  # 如果没有名称，直接使用代码
        
        stock_names.append(display_name)  # 添加到显示名称列表
    
    # 净流入金额处理
    # 同花顺API的net_amount单位为万元，需要转换为亿元用于显示
    if 'net_amount' in stocks_df.columns:
        # 确保净流入金额为数值类型
        net_amount_col = pd.to_numeric(stocks_df['net_amount'], errors='coerce')
        
        # 检测单位：如果最大值超过1000万，则可能已经是万元单位
        if abs(net_amount_col.max()) > 10000000 or abs(net_amount_col.min()) > 10000000:
            # 值很大，可能是原始单位，转换为亿元(除以100000000)
            net_amounts = net_amount_col / 100000000
            print("净流入金额单位检测：原始单位，转换为亿元")
        else:
            # 值较小，可能已经是万元单位，转换为亿元(除以10000)
            net_amounts = net_amount_col / 10000
            print("净流入金额单位检测：万元单位，转换为亿元")
    elif 'buy_amount' in stocks_df.columns and 'sell_amount' in stocks_df.columns:
        # 如果没有净流入但有买入卖出金额，计算净流入
        net_amounts = (stocks_df['buy_amount'] - stocks_df['sell_amount']) / 100000000
        print("使用买入减去卖出金额计算净流入")
    elif 'amount' in stocks_df.columns:
        # 如果没有净流入数据，使用成交额作为替代
        net_amounts = stocks_df['amount'] / 100000000
        print("警告：使用成交额代替净流入进行图表绘制")
    else:
        # 如果没有任何有用的数据，创建全零数组
        print("错误：没有找到任何可用于绘图的数据")
        net_amounts = np.zeros(len(stocks_df))
    
    # 绘制柱状图
    bars = plt.bar(stock_names, net_amounts, width=0.6)  # 创建柱状图，宽度为0.6
    
    # 设置柱子颜色：红色表示正值，绿色表示负值
    for i, bar in enumerate(bars):  # 遍历每个柱子
        if bar.get_height() >= 0:  # 如果净流入为正
            bar.set_color('#F63366')  # 设置为红色（净流入）
        else:  # 如果净流入为负
            bar.set_color('#09B552')  # 设置为绿色（净流出）
    
    # 添加数据标签
    for i, bar in enumerate(bars):  # 遍历每个柱子
        height = bar.get_height()  # 获取柱子高度（即净流入金额）
        if height >= 0:  # 如果净流入为正
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.05, 
                     f"+{height:.2f}", ha='center', va='bottom', fontsize=9)  # 在柱子顶部显示正值
        else:  # 如果净流入为负
            plt.text(bar.get_x() + bar.get_width()/2., height - 0.05, 
                     f"{height:.2f}", ha='center', va='top', fontsize=9)  # 在柱子底部显示负值
    
    # 格式化日期
    formatted_date = trade_date  # 初始化为原始日期
    if len(trade_date) == 8:  # 如果日期格式为YYYYMMDD
        formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"  # 转换为YYYY-MM-DD格式
    
    # 添加标题和标签
    plt.title(f"{formatted_date} {industry_name}(行业排名:{industry_rank}/{total_industries}) 个股资金净流入排行", fontsize=18, pad=15)  # 设置图表标题
    plt.xlabel('股票', fontsize=14, labelpad=10)  # 设置x轴标签
    plt.ylabel('净流入金额（亿元）', fontsize=14, labelpad=10)  # 设置y轴标签
    
    # 设置x轴标签
    plt.xticks(rotation=45, ha='right', fontsize=10)  # 将x轴标签旋转45度，右对齐，字号10
    
    # 添加网格线
    plt.grid(axis='y', linestyle='--', alpha=0.6)  # 添加水平网格线，使用虚线，透明度0.6
    
    # 美化图表
    plt.gca().spines['top'].set_visible(False)  # 去掉上边框
    plt.gca().spines['right'].set_visible(False)  # 去掉右边框
    
    # 添加均值线
    mean_value = np.mean(net_amounts)  # 计算净流入均值
    if not np.isnan(mean_value) and not np.isinf(mean_value):  # 如果均值不是NaN或无穷大
        plt.axhline(y=mean_value, color='#6A5ACD', linestyle='--', alpha=0.8)  # 绘制均值水平线
        plt.text(len(stock_names)-1, mean_value, f'平均: {mean_value:.2f}亿', 
                 ha='right', va='bottom' if mean_value >= 0 else 'top', color='#6A5ACD')  # 添加均值标签
    
    # 添加零线
    plt.axhline(y=0, color='black', alpha=0.3)  # 添加零水平线
    
    # 调整y轴范围
    max_value = max(net_amounts)  # 获取最大净流入值
    min_value = min(net_amounts)  # 获取最小净流入值
    
    if not (np.isnan(max_value) or np.isnan(min_value) or np.isinf(max_value) or np.isinf(min_value)):  # 如果值都是有效的
        y_padding = max(abs(max_value), abs(min_value)) * 0.15  # 计算y轴上下的间距
        plt.ylim(min_value - y_padding, max_value + y_padding)  # 设置y轴范围
    
    # 添加数据来源和日期
    plt.figtext(0.02, 0.02, f"数据来源: 同花顺 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                ha='left', fontsize=8, alpha=0.6)  # 在图表左下角添加数据来源和生成时间
    
    # 优化布局
    plt.tight_layout(pad=2.0)  # 调整子图间距，确保标签不重叠
    
    # 保存图片
    if save_fig:  # 如果需要保存图片
        sanitized_industry = industry_name.replace('/', '_').replace('\\', '_')  # 处理行业名称中的特殊字符
        filename = f'industry_{sanitized_industry}_stocks_{trade_date}.png'  # 生成文件名
        plt.savefig(filename, dpi=300, bbox_inches='tight')  # 保存为高分辨率PNG图片
        print(f"图表已保存为 {filename}")  # 打印保存信息
    
    # 显示图表
    if show_fig:  # 如果需要显示图表
        plt.show()  # 显示图表
    else:  # 否则
        plt.close()  # 关闭图表释放资源

# 如果作为主程序运行
if __name__ == "__main__":  # 当脚本直接运行而不是被导入时
    # 分析净流入最高的前3个行业中的前10支股票
    industry_stocks = get_top_stocks_by_industry(top_industry_count=3, top_stock_count=10)  # 调用主函数进行分析
    
    # 打印分析结果
    for industry, stocks in industry_stocks.items():  # 遍历每个行业及其股票数据
        print(f"\n行业: {industry} 的热门股票:")  # 打印行业标题
        if not stocks.empty:  # 如果有有效数据
            print(f"可用数据列: {stocks.columns.tolist()}")  # 打印可用数据列，帮助调试
            
            for i, (idx, stock) in enumerate(stocks.iterrows(), 1):  # 遍历每支股票
                name = stock['name'] if 'name' in stock else '未知'  # 获取股票名称，如果不存在则显示"未知"
                code = stock['ts_code'] if 'ts_code' in stock else '未知'  # 获取股票代码，如果不存在则显示"未知"
                
                # 计算成交额（转换为亿元）
                amount = 0
                if 'amount' in stock:
                    # 根据值大小判断单位
                    amount_val = stock['amount']
                    if amount_val > 10000000:  # 如果值很大，可能是原始单位
                        amount = amount_val / 100000000  # 转换为亿元
                    else:  # 如果值较小，可能已经是万元单位
                        amount = amount_val / 10000  # 转换为亿元
                
                # 获取净流入额（转换为亿元）
                net_amount = 0
                if 'net_amount' in stock:
                    # 根据值大小判断单位
                    net_val = stock['net_amount']
                    if isinstance(net_val, (int, float)) and abs(net_val) > 10000000:  # 如果值很大，可能是原始单位
                        net_amount = net_val / 100000000  # 转换为亿元
                    else:  # 如果值较小，可能已经是万元单位
                        net_amount = net_val / 10000 if isinstance(net_val, (int, float)) else 0  # 转换为亿元
                elif 'buy_amount' in stock and 'sell_amount' in stock:
                    net_amount = (stock['buy_amount'] - stock['sell_amount']) / 100000000
                
                # 获取涨跌幅(%)
                pct_change = stock['pct_change'] if 'pct_change' in stock else (stock['pct_chg'] if 'pct_chg' in stock else None)
                
                # 输出格式化的信息
                pct_info = f"涨跌幅 {pct_change:.2f}%" if pct_change is not None else ""
                print(f"{i}. {name}({code}): 成交额 {amount:.2f}亿元, 净流入 {net_amount:.2f}亿元 {pct_info}")  # 打印股票详细信息 