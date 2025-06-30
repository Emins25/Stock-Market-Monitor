#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
市场分析AI模块
使用火山方舟大模型生成市场分析点评总结

依赖:
- 火山方舟API (Doubao-1.6-thinking模型)
- requests库
"""

import os
from typing import Dict, List, Any
import logging
from openai import OpenAI

# 设置日志
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 减少OpenAI库的调试信息
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# 火山方舟API配置
MODEL_NAME = "doubao-seed-1-6-thinking-250615"  # 官方提供的模型名称

def get_api_key():
    """
    获取API密钥，优先从环境变量获取，否则使用默认值
    """
    # 优先从环境变量获取
    api_key = os.environ.get('ARK_API_KEY')
    if api_key:
        return api_key
    
    # 如果环境变量中没有，使用默认值（请替换为实际的API密钥）
    # 注意：在生产环境中应该将API密钥存储在环境变量或配置文件中
    default_key = "3fa66838-d4bc-48be-8cc9-3be83f64b7e5"  # 用户的火山方舟API密钥
    return default_key

def call_volcano_api(prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    """
    调用火山方舟大模型API
    
    参数:
    prompt: 输入的提示词
    max_tokens: 最大生成token数
    temperature: 温度参数，控制生成的随机性
    
    返回:
    str: 生成的回复文本
    """
    api_key = get_api_key()
    
    try:
        print("🤖 正在调用AI分析...")
        
        # 初始化OpenAI客户端
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
        
        # 调用API
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            print("✅ AI分析完成")
            return content
        else:
            print("❌ API响应格式异常")
            return "API响应格式异常，无法生成分析内容"
            
    except Exception as e:
        print(f"❌ AI调用失败: {e}")
        return f"调用API时发生错误: {str(e)}"

def generate_market_analysis_summary(market_data: Dict[str, Any]) -> str:
    """
    基于市场数据生成综合分析点评总结
    
    参数:
    market_data: 包含各项市场分析数据的字典
    
    返回:
    str: 生成的市场分析点评总结
    """
    # 构建详细的分析提示词
    prompt = f"""
请作为一名资深的股票市场分析师，基于以下市场数据进行深度分析并生成一份专业的市场点评总结。

## 市场数据概览

### 1. 主要指数表现
{format_index_data(market_data.get('index_data', {}))}

### 2. 行业资金流向情况
{format_industry_data(market_data.get('industry_data', {}))}

### 3. 个股资金净流入情况
{format_stock_moneyflow_data(market_data.get('stock_moneyflow_data', {}))}

### 4. 量价背离指数
{format_divergence_data(market_data.get('divergence_data', {}))}

### 5. 资金集中度指标
{format_concentration_data(market_data.get('concentration_data', {}))}

### 6. 上涨下跌股票比值
{format_up_down_ratio_data(market_data.get('up_down_ratio_data', {}))}

### 7. 技术指标分析
{format_technical_data(market_data.get('technical_data', {}))}

### 8. 涨停板晋级率
{format_promotion_data(market_data.get('promotion_data', {}))}

### 9. 新高新低股票数量
{format_high_low_data(market_data.get('high_low_data', {}))}

### 10. 创新高优质股票筛选
{format_filtered_stocks_data(market_data.get('filtered_stocks_data', {}))}

## 分析要求

请从以下几个维度进行深入分析：

1. **市场整体表现**：综合各主要指数的表现，判断当前市场的强弱状态和趋势方向
2. **资金流向分析**：分析行业和个股的资金流向特征，识别市场主流热点和资金偏好
3. **市场情绪评估**：结合量价背离、涨停板晋级率等指标，评估当前市场情绪和风险偏好
4. **结构特征分析**：通过资金集中度、上涨下跌比等指标，分析市场的结构性特征
5. **技术面判断**：基于技术指标分析，对市场的技术面状态进行判断
6. **风险提示与机会**：基于综合分析，提出当前市场的主要风险点和潜在投资机会
7. **短期展望**：对未来1-2周的市场走向给出专业判断

## 输出要求

请生成一份结构清晰、逻辑严密的市场分析点评，约800-1200字，包含：
- 市场核心观点（2-3个要点）
- 详细分析论述
- 风险提示
- 投资建议

请用专业、客观的语言，避免过于绝对的判断，注重数据支撑和逻辑推理。
"""
    
    # 调用大模型API生成分析
    analysis_result = call_volcano_api(prompt, max_tokens=2500, temperature=0.6)
    
    return analysis_result

def format_index_data(index_data: Dict) -> str:
    """格式化指数数据"""
    if not index_data:
        return "暂无指数数据"
    
    formatted = "主要指数当日表现：\n"
    for index_code, data in index_data.items():
        if isinstance(data, dict):
            name = data.get('name', index_code)
            pct_change = data.get('pct_chg', 0)
            formatted += f"- {name}: {pct_change:.2f}%\n"
    
    return formatted

def format_industry_data(industry_data: Dict) -> str:
    """格式化行业数据"""
    if not industry_data:
        return "暂无行业数据"
    
    formatted = "行业资金流向前五名：\n"
    if 'top_industries' in industry_data:
        for i, industry in enumerate(industry_data['top_industries'][:5], 1):
            net_amount = industry.get('net_amount', 0)
            industry_name = industry.get('industry', '未知行业')
            formatted += f"{i}. {industry_name}: {net_amount:.2f}亿元\n"
    
    return formatted

def format_stock_moneyflow_data(stock_data: Dict) -> str:
    """格式化个股资金流数据"""
    if not stock_data:
        return "暂无个股资金流数据"
    
    formatted = ""
    if 'net_inflow_top' in stock_data:
        formatted += "资金净流入前五名个股：\n"
        for i, stock in enumerate(stock_data['net_inflow_top'][:5], 1):
            name = stock.get('name', '未知')
            net_amount = stock.get('net_amount', 0)
            formatted += f"{i}. {name}: {net_amount:.2f}万元\n"
    
    return formatted

def format_divergence_data(divergence_data: Dict) -> str:
    """格式化量价背离数据"""
    if not divergence_data:
        return "暂无量价背离数据"
    
    latest_value = divergence_data.get('latest_value', 0)
    avg_value = divergence_data.get('avg_value', 0)
    
    formatted = f"最新量价背离指数: {latest_value:.2f}%\n"
    formatted += f"近期平均值: {avg_value:.2f}%\n"
    
    if latest_value > 30:
        formatted += "当前量价背离指数偏高，需警惕市场虚涨风险\n"
    
    return formatted

def format_concentration_data(concentration_data: Dict) -> str:
    """格式化资金集中度数据"""
    if not concentration_data:
        return "暂无资金集中度数据"
    
    latest_value = concentration_data.get('latest_value', 0)
    avg_value = concentration_data.get('avg_value', 0)
    
    formatted = f"最新资金集中度: {latest_value:.2f}%\n"
    formatted += f"近期平均值: {avg_value:.2f}%\n"
    
    if latest_value > 60:
        formatted += "资金集中度较高，市场呈现明显抱团现象\n"
    
    return formatted

def format_up_down_ratio_data(ratio_data: Dict) -> str:
    """格式化上涨下跌比数据"""
    if not ratio_data:
        return "暂无上涨下跌比数据"
    
    latest_value = ratio_data.get('latest_value', 0)
    avg_value = ratio_data.get('avg_value', 0)
    
    formatted = f"最新上涨/下跌股票比值: {latest_value:.2f}\n"
    formatted += f"近期平均值: {avg_value:.2f}\n"
    
    if latest_value < 1:
        formatted += "上涨股票数少于下跌股票数，市场整体偏弱\n"
    elif latest_value > 2:
        formatted += "上涨股票数远多于下跌股票数，市场表现强势\n"
    
    return formatted

def format_technical_data(technical_data: Dict) -> str:
    """格式化技术指标数据"""
    if not technical_data:
        return "暂无技术指标数据"
    
    formatted = "上证指数技术指标状态：\n"
    rsi_value = technical_data.get('rsi_value', 50)
    trend_signal = technical_data.get('trend_signal', '中性')
    
    formatted += f"RSI指标: {rsi_value:.2f}\n"
    formatted += f"趋势信号: {trend_signal}\n"
    
    if rsi_value > 70:
        formatted += "RSI指标显示市场可能超买\n"
    elif rsi_value < 30:
        formatted += "RSI指标显示市场可能超卖\n"
    
    return formatted

def format_promotion_data(promotion_data: Dict) -> str:
    """格式化涨停板晋级率数据"""
    if not promotion_data:
        return "暂无涨停板晋级率数据"
    
    promotion_1to2 = promotion_data.get('promotion_1to2', 0)
    promotion_2to3 = promotion_data.get('promotion_2to3', 0)
    
    formatted = f"1进2晋级率: {promotion_1to2:.2f}%\n"
    formatted += f"2进3晋级率: {promotion_2to3:.2f}%\n"
    
    if promotion_1to2 > 20:
        formatted += "涨停板晋级率较高，市场赚钱效应较强\n"
    elif promotion_1to2 < 10:
        formatted += "涨停板晋级率较低，市场赚钱效应偏弱\n"
    
    return formatted

def format_high_low_data(high_low_data: Dict) -> str:
    """格式化新高新低数据"""
    if not high_low_data:
        return "暂无新高新低数据"
    
    new_high_52w = high_low_data.get('new_high_52w', 0)
    new_low_52w = high_low_data.get('new_low_52w', 0)
    
    formatted = f"52周新高股票数: {new_high_52w}\n"
    formatted += f"52周新低股票数: {new_low_52w}\n"
    
    if new_high_52w > new_low_52w * 2:
        formatted += "新高股票数明显多于新低股票数，市场结构健康\n"
    elif new_low_52w > new_high_52w * 2:
        formatted += "新低股票数明显多于新高股票数，市场结构偏弱\n"
    
    return formatted

def format_filtered_stocks_data(filtered_data: Dict) -> str:
    """格式化筛选股票数据"""
    if not filtered_data:
        return "暂无优质股票筛选数据"
    
    stock_count = filtered_data.get('stock_count', 0)
    
    formatted = f"符合筛选条件的优质新高股票数量: {stock_count}只\n"
    
    if stock_count > 20:
        formatted += "符合条件的优质股票较多，市场整体质量较好\n"
    elif stock_count < 5:
        formatted += "符合条件的优质股票较少，需要谨慎选择投资标的\n"
    
    return formatted

# 测试函数
def test_api_connection():
    """测试API连接"""
    test_prompt = "请简单介绍一下股票市场的基本概念。"
    result = call_volcano_api(test_prompt, max_tokens=500, temperature=0.5)
    print("API测试结果:")
    print(result)
    return result

if __name__ == "__main__":
    # 运行API连接测试
    test_api_connection() 