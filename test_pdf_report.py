#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试 create_pdf_report 函数
"""

from create_pdf_report import create_pdf_report

def main():
    # 创建一个测试用的filtered_stocks
    test_filtered_stocks = {
        'stocks': [
            {
                'ts_code': '000001.SZ',
                'name': '平安银行',
                'industry': '银行',
                'total_mv': 248.56,
                'rebound_ratio': 0.32
            },
            {
                'ts_code': '600036.SH',
                'name': '招商银行',
                'industry': '银行',
                'total_mv': 1023.45,
                'rebound_ratio': 0.28
            },
            {
                'ts_code': '601318.SH',
                'name': '中国平安',
                'industry': '保险',
                'total_mv': 1245.67,
                'rebound_ratio': 0.35
            }
        ],
        'figure_path': None  # 不指定图片，让函数自动查找
    }
    
    # 测试修复后的函数
    pdf_file = create_pdf_report("test_report_fixed.pdf", filtered_stocks=test_filtered_stocks)
    print(f"报告已生成: {pdf_file}")

if __name__ == "__main__":
    main() 