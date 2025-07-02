#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
周度股票市场监测系统
Weekly Stock Market Monitor System

基于日度监测系统进行修改，以周度为维度对股票市场进行观测和分析

主要功能：
1. 市场指数周度表现：主要指数的周度涨跌幅分析
2. 行业资金流向分析：
   - 周度行业资金净流入排序（前10和后10）
   - 行业每日资金净流入累计值的柱状图展示
   - 全市场个股资金净流入排名前十
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib as mpl
from cycler import cycler
import tushare as ts
import warnings

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入工具模块
from tushare_utils import get_data_with_retry

warnings.filterwarnings('ignore')

class WeeklyMarketMonitor:
    """周度市场监测类"""
    
    def __init__(self, token=None):
        """
        初始化监测系统
        
        参数:
        token: tushare API token
        """
        # 设置默认token
        if token is None:
            token = '284b804f2f919ea85cb7e6dfe617ff81f123c80b4cd3c4b13b35d736'
        
        # 初始化tushare
        ts.set_token(token)
        self.pro = ts.pro_api()
        
        # 设置图表样式
        self._set_chart_style()
        
        # 定义主要指数
        self.major_indices = {
            '399300.SZ': '沪深300指数',
            '000001.SH': '上证指数', 
            '399001.SZ': '深证成指',
            '399006.SZ': '创业板指',
            '000688.SH': '科创50指数',
            '399905.SZ': '中证500指数',
            '399852.SZ': '中证1000指数',
            '932000.CSI': '中证2000指数'
        }
        
    def _set_chart_style(self):
        """设置统一的图表样式"""
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体为黑体
        plt.rcParams['axes.unicode_minus'] = False    # 正确显示负号
        
        # 设置图表样式
        plt.style.use('ggplot')
        
        # 设置全局配色方案
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        mpl.rcParams['axes.prop_cycle'] = cycler(color=colors)
        
        # 设置其他样式参数
        plt.rcParams['lines.linewidth'] = 2
        plt.rcParams['lines.markersize'] = 8
        plt.rcParams['grid.linestyle'] = '--'
        plt.rcParams['grid.alpha'] = 0.7
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 120
    
    def get_week_dates(self, end_date=None):
        """
        获取指定日期所在周的起止日期
        
        参数:
        end_date: 结束日期，格式为YYYYMMDD字符串，默认为当前日期
        
        返回:
        tuple: (周一日期, 周五日期) 格式为YYYYMMDD字符串
        """
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y%m%d')
        
        # 获取周一（0为周一，6为周日）
        weekday = end_date.weekday()
        monday = end_date - timedelta(days=weekday)
        friday = monday + timedelta(days=4)
        
        return monday.strftime('%Y%m%d'), friday.strftime('%Y%m%d')
    
    def get_trading_dates(self, start_date, end_date):
        """
        获取指定日期范围内的交易日期
        
        参数:
        start_date: 开始日期，格式为YYYYMMDD字符串
        end_date: 结束日期，格式为YYYYMMDD字符串
        
        返回:
        list: 交易日期列表
        """
        try:
            cal_df = get_data_with_retry(
                self.pro.trade_cal,
                start_date=start_date,
                end_date=end_date,
                exchange='SSE'
            )
            
            if cal_df.empty:
                print(f"警告：无法获取{start_date}到{end_date}的交易日历")
                return []
            
            # 筛选交易日
            trading_dates = cal_df[cal_df['is_open'] == 1]['cal_date'].tolist()
            return sorted(trading_dates)
            
        except Exception as e:
            print(f"获取交易日期时出错: {e}")
            return []
    
    def analyze_weekly_index_performance(self, end_date=None, save_fig=True):
        """
        分析市场指数周度表现
        
        参数:
        end_date: 分析截止日期，格式为YYYYMMDD字符串
        save_fig: 是否保存图表
        
        返回:
        pd.DataFrame: 指数周度涨跌幅数据
        """
        print("正在分析市场指数周度表现...")
        
        # 获取本周起止日期
        week_start, week_end = self.get_week_dates(end_date)
        print(f"分析周期：{week_start} 至 {week_end}")
        
        # 获取交易日期
        trading_dates = self.get_trading_dates(week_start, week_end)
        if not trading_dates:
            print("警告：本周无交易日数据")
            return pd.DataFrame()
        
        weekly_start = trading_dates[0]  # 本周第一个交易日
        weekly_end = trading_dates[-1]   # 本周最后一个交易日
        
        results = []
        
        for ts_code, name in self.major_indices.items():
            try:
                # 获取指数行情数据
                df = get_data_with_retry(
                    self.pro.index_daily,
                    ts_code=ts_code,
                    start_date=weekly_start,
                    end_date=weekly_end
                )
                
                if df.empty:
                    print(f"警告：无法获取{name}({ts_code})的数据")
                    continue
                
                # 按日期排序
                df = df.sort_values('trade_date')
                
                if len(df) >= 2:
                    # 计算周度涨跌幅
                    start_close = df.iloc[0]['close']
                    end_close = df.iloc[-1]['close']
                    weekly_return = ((end_close - start_close) / start_close) * 100
                    
                    results.append({
                        'ts_code': ts_code,
                        'name': name,
                        'start_price': start_close,
                        'end_price': end_close,
                        'weekly_return': weekly_return
                    })
                    
                    print(f"{name}: {weekly_return:.2f}%")
                
            except Exception as e:
                print(f"处理{name}时出错: {e}")
                continue
        
        if not results:
            print("警告：未获取到任何指数数据")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('weekly_return', ascending=False)
        
        # 生成图表
        if save_fig:
            self._plot_weekly_index_performance(df_results, week_start, week_end)
        
        return df_results
    
    def _plot_weekly_index_performance(self, df, week_start, week_end):
        """绘制指数周度表现图表"""
        plt.figure(figsize=(14, 8))
        
        # 设置颜色：上涨为红色，下跌为绿色
        colors = ['red' if x >= 0 else 'green' for x in df['weekly_return']]
        
        bars = plt.bar(range(len(df)), df['weekly_return'], color=colors, alpha=0.7)
        
        # 设置标签
        plt.xticks(range(len(df)), df['name'], rotation=45, ha='right')
        plt.ylabel('周度涨跌幅 (%)')
        plt.title(f'主要指数周度表现 ({week_start} - {week_end})', fontsize=16, fontweight='bold')
        
        # 添加数值标签
        for i, (bar, value) in enumerate(zip(bars, df['weekly_return'])):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.3),
                    f'{value:.2f}%', ha='center', va='bottom' if height >= 0 else 'top',
                    fontweight='bold')
        
        # 添加零线
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存图表
        filename = f'weekly_index_performance_{week_end}.png'
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        print(f"指数周度表现图已保存：{filename}")
        plt.close()
    
    def analyze_weekly_industry_moneyflow(self, end_date=None, save_fig=True):
        """
        分析行业资金流向周度数据
        
        参数:
        end_date: 分析截止日期
        save_fig: 是否保存图表
        
        返回:
        tuple: (周度排序数据, 累计流向数据)
        """
        print("正在分析行业资金流向周度数据...")
        
        # 获取本周起止日期
        week_start, week_end = self.get_week_dates(end_date)
        
        # 获取交易日期
        trading_dates = self.get_trading_dates(week_start, week_end)
        if not trading_dates:
            print("警告：本周无交易日数据")
            return pd.DataFrame(), pd.DataFrame()
        
        # 获取每日行业资金流向数据
        daily_data = []
        for date in trading_dates:
            try:
                df = get_data_with_retry(
                    self.pro.moneyflow_ind_ths,
                    trade_date=date
                )
                
                if not df.empty:
                    df['trade_date'] = date
                    daily_data.append(df)
                    print(f"获取{date}行业资金流向数据：{len(df)}行")
                    
            except Exception as e:
                print(f"获取{date}行业资金流向数据时出错: {e}")
                continue
        
        if not daily_data:
            print("警告：未获取到任何行业资金流向数据")
            return pd.DataFrame(), pd.DataFrame()
        
        # 合并所有数据
        all_data = pd.concat(daily_data, ignore_index=True)
        
        # 转换金额单位为亿元
        all_data['net_amount_yi'] = all_data['net_amount'] / 10000
        
        # 1. 计算周度净流入排序
        weekly_summary = all_data.groupby('industry')['net_amount_yi'].sum().reset_index()
        weekly_summary = weekly_summary.sort_values('net_amount_yi', ascending=False)
        
        # 2. 计算每日累计流向
        cumulative_data = self._calculate_cumulative_flow(all_data, trading_dates)
        
        # 生成图表
        if save_fig:
            self._plot_weekly_industry_flow(weekly_summary, cumulative_data, week_start, week_end)
        
        return weekly_summary, cumulative_data
    
    def _calculate_cumulative_flow(self, data, trading_dates):
        """计算行业每日累计资金流向"""
        industries = data['industry'].unique()
        cumulative_results = {}
        
        for industry in industries:
            industry_data = data[data['industry'] == industry].copy()
            industry_data = industry_data.sort_values('trade_date')
            
            # 计算累计值
            cumulative_flow = []
            cumulative_sum = 0
            
            for date in trading_dates:
                day_data = industry_data[industry_data['trade_date'] == date]
                if not day_data.empty:
                    daily_flow = day_data['net_amount_yi'].iloc[0]
                else:
                    daily_flow = 0
                
                cumulative_sum += daily_flow
                cumulative_flow.append(cumulative_sum)
            
            cumulative_results[industry] = cumulative_flow
        
        # 转换为DataFrame
        cumulative_df = pd.DataFrame(cumulative_results, index=trading_dates)
        return cumulative_df.T  # 转置，行业为行，日期为列
    
    def _plot_weekly_industry_flow(self, weekly_summary, cumulative_data, week_start, week_end):
        """绘制行业资金流向图表"""
        # 1. 周度排序柱状图
        plt.figure(figsize=(16, 10))
        
        # 前10和后10行业
        top10 = weekly_summary.head(10)
        bottom10 = weekly_summary.tail(10)
        
        # 子图1：前10行业
        plt.subplot(2, 2, 1)
        colors_top = ['red' if x >= 0 else 'green' for x in top10['net_amount_yi']]
        bars = plt.bar(range(len(top10)), top10['net_amount_yi'], color=colors_top, alpha=0.7)
        plt.xticks(range(len(top10)), top10['industry'], rotation=45, ha='right')
        plt.ylabel('资金净流入 (亿元)')
        plt.title('资金净流入前10行业')
        plt.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, value in zip(bars, top10['net_amount_yi']):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -3),
                    f'{value:.1f}', ha='center', va='bottom' if height >= 0 else 'top',
                    fontsize=9)
        
        # 子图2：后10行业
        plt.subplot(2, 2, 2)
        colors_bottom = ['red' if x >= 0 else 'green' for x in bottom10['net_amount_yi']]
        bars = plt.bar(range(len(bottom10)), bottom10['net_amount_yi'], color=colors_bottom, alpha=0.7)
        plt.xticks(range(len(bottom10)), bottom10['industry'], rotation=45, ha='right')
        plt.ylabel('资金净流入 (亿元)')
        plt.title('资金净流入后10行业')
        plt.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, value in zip(bars, bottom10['net_amount_yi']):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + (1 if height >= 0 else -3),
                    f'{value:.1f}', ha='center', va='bottom' if height >= 0 else 'top',
                    fontsize=9)
        
        # 子图3&4：累计流向图（选择资金流入最大和最小的几个行业）
        top5_industries = weekly_summary.head(5)['industry'].tolist()
        bottom5_industries = weekly_summary.tail(5)['industry'].tolist()
        
        # 子图3：资金流入最大的5个行业累计图
        plt.subplot(2, 2, 3)
        dates = cumulative_data.columns
        date_labels = [d[4:6] + '/' + d[6:8] for d in dates]  # 转换为MM/DD格式
        
        for industry in top5_industries:
            if industry in cumulative_data.index:
                plt.plot(date_labels, cumulative_data.loc[industry], marker='o', linewidth=2, label=industry)
        
        plt.xlabel('交易日期')
        plt.ylabel('累计资金净流入 (亿元)')
        plt.title('资金流入前5行业累计流向')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        
        # 子图4：资金流入最小的5个行业累计图
        plt.subplot(2, 2, 4)
        for industry in bottom5_industries:
            if industry in cumulative_data.index:
                plt.plot(date_labels, cumulative_data.loc[industry], marker='o', linewidth=2, label=industry)
        
        plt.xlabel('交易日期')
        plt.ylabel('累计资金净流入 (亿元)')
        plt.title('资金流入后5行业累计流向')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        
        plt.suptitle(f'行业资金流向分析 ({week_start} - {week_end})', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # 保存图表
        filename = f'weekly_industry_moneyflow_{week_end}.png'
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        print(f"行业资金流向图已保存：{filename}")
        plt.close()
    
    def analyze_weekly_stock_moneyflow(self, end_date=None, top_n=10, save_fig=True):
        """
        分析全市场个股资金净流入周度排名
        
        参数:
        end_date: 分析截止日期
        top_n: 显示前N名股票
        save_fig: 是否保存图表
        
        返回:
        pd.DataFrame: 个股周度资金净流入排名
        """
        print("正在分析全市场个股资金净流入周度排名...")
        
        # 获取本周起止日期
        week_start, week_end = self.get_week_dates(end_date)
        
        # 获取交易日期
        trading_dates = self.get_trading_dates(week_start, week_end)
        if not trading_dates:
            print("警告：本周无交易日数据")
            return pd.DataFrame()
        
        # 获取每日个股资金流向数据
        daily_stock_data = []
        for date in trading_dates:
            try:
                df = get_data_with_retry(
                    self.pro.moneyflow_ths,
                    trade_date=date
                )
                
                if not df.empty:
                    df['trade_date'] = date
                    daily_stock_data.append(df)
                    print(f"获取{date}个股资金流向数据：{len(df)}行")
                    
            except Exception as e:
                print(f"获取{date}个股资金流向数据时出错: {e}")
                continue
        
        if not daily_stock_data:
            print("警告：未获取到任何个股资金流向数据")
            return pd.DataFrame()
        
        # 合并所有数据
        all_stock_data = pd.concat(daily_stock_data, ignore_index=True)
        
        # 转换金额单位为亿元
        all_stock_data['net_amount_yi'] = all_stock_data['net_amount'] / 10000
        
        # 计算周度净流入排序
        weekly_stock_summary = all_stock_data.groupby(['ts_code', 'name'])['net_amount_yi'].sum().reset_index()
        weekly_stock_summary = weekly_stock_summary.sort_values('net_amount_yi', ascending=False)
        
        # 取前N名
        top_stocks = weekly_stock_summary.head(top_n)
        
        # 生成图表
        if save_fig:
            self._plot_weekly_stock_flow(top_stocks, week_start, week_end)
        
        return top_stocks
    
    def _plot_weekly_stock_flow(self, top_stocks, week_start, week_end):
        """绘制个股资金流向图表"""
        plt.figure(figsize=(14, 8))
        
        # 创建股票标签（股票名称+代码）
        stock_labels = [f"{name}\n({code})" for code, name in zip(top_stocks['ts_code'], top_stocks['name'])]
        
        colors = ['red' if x >= 0 else 'green' for x in top_stocks['net_amount_yi']]
        bars = plt.bar(range(len(top_stocks)), top_stocks['net_amount_yi'], color=colors, alpha=0.7)
        
        plt.xticks(range(len(top_stocks)), stock_labels, rotation=45, ha='right')
        plt.ylabel('资金净流入 (亿元)')
        plt.title(f'个股资金净流入周度排名前{len(top_stocks)}名 ({week_start} - {week_end})', 
                 fontsize=16, fontweight='bold')
        
        # 添加数值标签
        for bar, value in zip(bars, top_stocks['net_amount_yi']):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height >= 0 else -1),
                    f'{value:.1f}', ha='center', va='bottom' if height >= 0 else 'top',
                    fontweight='bold')
        
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存图表
        filename = f'weekly_stock_moneyflow_{week_end}.png'
        plt.savefig(filename, dpi=120, bbox_inches='tight')
        print(f"个股资金流向图已保存：{filename}")
        plt.close()
    
    def generate_weekly_report(self, end_date=None):
        """
        生成完整的周度市场监测报告
        
        参数:
        end_date: 分析截止日期，格式为YYYYMMDD字符串
        
        返回:
        dict: 包含所有分析结果的字典
        """
        print("\n" + "="*60)
        print("周度股票市场监测报告生成工具")
        print("Weekly Stock Market Monitor System")
        print("="*60)
        
        start_time = datetime.now()
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取分析日期
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        week_start, week_end = self.get_week_dates(end_date)
        print(f"分析周期: {week_start} 至 {week_end}")
        
        results = {}
        
        try:
            # 1. 市场指数周度表现分析
            print(f"\n[1/3] 分析市场指数周度表现...")
            index_results = self.analyze_weekly_index_performance(end_date, save_fig=True)
            results['index_performance'] = index_results
            
            # 2. 行业资金流向分析
            print(f"\n[2/3] 分析行业资金流向...")
            industry_weekly, industry_cumulative = self.analyze_weekly_industry_moneyflow(end_date, save_fig=True)
            results['industry_weekly'] = industry_weekly
            results['industry_cumulative'] = industry_cumulative
            
            # 3. 个股资金净流入分析
            print(f"\n[3/3] 分析个股资金净流入...")
            stock_results = self.analyze_weekly_stock_moneyflow(end_date, top_n=10, save_fig=True)
            results['stock_moneyflow'] = stock_results
            
            # 生成文字报告
            self._generate_text_report(results, week_start, week_end)
            
            end_time = datetime.now()
            duration = end_time - start_time
            print(f"\n报告生成完成！")
            print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"耗时: {duration.total_seconds():.1f}秒")
            
            return results
            
        except Exception as e:
            print(f"生成报告时出错: {e}")
            return results
    
    def _generate_text_report(self, results, week_start, week_end):
        """生成文字版报告"""
        report_lines = []
        report_lines.append("="*60)
        report_lines.append("周度股票市场监测报告")
        report_lines.append(f"Weekly Stock Market Monitor Report")
        report_lines.append("="*60)
        report_lines.append(f"报告日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"分析周期: {week_start} 至 {week_end}")
        report_lines.append("")
        
        # 1. 指数表现总结
        if 'index_performance' in results and not results['index_performance'].empty:
            report_lines.append("一、市场指数周度表现")
            report_lines.append("-" * 30)
            df_index = results['index_performance']
            for _, row in df_index.iterrows():
                status = "↑" if row['weekly_return'] >= 0 else "↓"
                report_lines.append(f"{row['name']}: {row['weekly_return']:.2f}% {status}")
            report_lines.append("")
        
        # 2. 行业资金流向总结
        if 'industry_weekly' in results and not results['industry_weekly'].empty:
            report_lines.append("二、行业资金流向分析")
            report_lines.append("-" * 30)
            df_industry = results['industry_weekly']
            
            report_lines.append("资金净流入前5行业:")
            for _, row in df_industry.head(5).iterrows():
                report_lines.append(f"  {row['industry']}: {row['net_amount_yi']:.1f}亿元")
            
            report_lines.append("\n资金净流出前5行业:")
            for _, row in df_industry.tail(5).iterrows():
                report_lines.append(f"  {row['industry']}: {row['net_amount_yi']:.1f}亿元")
            report_lines.append("")
        
        # 3. 个股资金流向总结
        if 'stock_moneyflow' in results and not results['stock_moneyflow'].empty:
            report_lines.append("三、个股资金净流入排名")
            report_lines.append("-" * 30)
            df_stock = results['stock_moneyflow']
            for i, (_, row) in enumerate(df_stock.iterrows(), 1):
                report_lines.append(f"{i:2d}. {row['name']}({row['ts_code']}): {row['net_amount_yi']:.1f}亿元")
            report_lines.append("")
        
        report_lines.append("="*60)
        report_lines.append("报告结束")
        
        # 保存文字报告
        report_filename = f'Weekly_Market_Report_{week_end}.txt'
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"文字报告已保存：{report_filename}")


def main():
    """主函数"""
    # 创建监测系统实例
    monitor = WeeklyMarketMonitor()
    
    # 生成周度报告
    results = monitor.generate_weekly_report()
    
    return results


if __name__ == "__main__":
    main() 