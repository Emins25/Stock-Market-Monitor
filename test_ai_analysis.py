#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from openai import OpenAI
import warnings

# 抑制不必要的警告信息
warnings.filterwarnings('ignore', category=Warning)

def test_api_basic():
    """基础API连接测试"""
    
    # 配置信息
    api_key = "3fa66838-d4bc-48be-8cc9-3be83f64b7e5"
    model_name = "doubao-seed-1-6-thinking-250615"  # 官方提供的模型名称
    
    try:
        print("开始测试API连接...")
        print(f"API端点: https://ark.cn-beijing.volces.com/api/v3")
        print(f"模型: {model_name}")
        
        # 初始化OpenAI客户端
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
        
        # 调用API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "你好，请简单介绍一下你自己"}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        print("API调用成功！")
        
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            print(f"\nAI回复: {content}")
        else:
            print("API响应格式异常，无choices内容")
            
    except Exception as e:
        print(f"API调用失败: {e}")

def test_ai_analysis():
    """测试AI分析功能"""
    from market_analysis_ai import generate_market_analysis_summary
    
    sample_data = {
        'index_data': {
            '000001.SH': {'name': '上证指数', 'pct_chg': 1.23}
        },
        'industry_data': {
            'top_industries': [{'industry': '证券', 'net_amount': 45.67}]
        },
        'stock_moneyflow_data': {
            'net_inflow_top': [{'name': '中信证券', 'net_amount': 12534.56}]
        },
        'divergence_data': {'latest_value': 25.5, 'avg_value': 22.3},
        'concentration_data': {'latest_value': 58.7, 'avg_value': 55.2},
        'up_down_ratio_data': {'latest_value': 1.34, 'avg_value': 1.28},
        'technical_data': {'rsi_value': 62.5, 'trend_signal': '多头趋势'},
        'promotion_data': {'promotion_1to2': 15.8, 'promotion_2to3': 35.2},
        'high_low_data': {'new_high_52w': 145, 'new_low_52w': 67},
        'filtered_stocks_data': {'stock_count': 23}
    }
    
    print("\n开始测试AI分析功能...")
    result = generate_market_analysis_summary(sample_data)
    print("AI分析结果:")
    print(result)
    return result

if __name__ == "__main__":
    print("=" * 60)
    print("火山方舟API测试")
    print("=" * 60)
    
    # 测试基础API连接
    test_api_basic()
    
    # 测试AI分析功能
    test_ai_analysis() 