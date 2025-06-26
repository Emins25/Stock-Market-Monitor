#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tushare API 工具模块
提供通用的 API 访问和数据处理功能
"""

import time
import logging
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('tushare_utils')

def get_data_with_retry(func, max_retries=3, retry_delay=2, extended_wait=True, **kwargs):
    """
    带智能重试机制的数据获取函数，处理API访问频率限制问题
    
    参数:
        func: tushare接口函数
        max_retries: 最大重试次数，默认为3
        retry_delay: 初始重试延迟（秒），默认为2秒
        extended_wait: 是否在错误时使用指数退避延迟，默认为True
        **kwargs: 传递给接口的参数
    
    返回:
        pd.DataFrame: 获取的数据，失败时返回空DataFrame
    """
    remaining_tries = max_retries
    current_delay = retry_delay
    
    while remaining_tries > 0:
        try:
            data = func(**kwargs)
            return data
        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是API访问频率限制错误
            if "每分钟最多访问该接口" in error_msg:
                logger.warning(f"遇到API访问频率限制: {error_msg}")
                logger.info(f"暂停60秒后继续...")
                time.sleep(60)  # 暂停60秒后继续尝试
                # 不减少尝试次数，因为这是API限制问题
                continue
                
            remaining_tries -= 1
            logger.warning(f"获取数据时出错 (尝试 {max_retries - remaining_tries}/{max_retries}): {error_msg}")
            
            if remaining_tries > 0:
                if extended_wait:
                    # 使用指数退避策略，每次失败后延迟时间翻倍
                    logger.info(f"等待 {current_delay} 秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= 2
                else:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
            else:
                logger.error(f"已达到最大重试次数，获取数据失败")
    
    # 所有尝试都失败，返回空DataFrame
    return pd.DataFrame()

def batch_process(items, batch_size=20, process_func=None, *args, **kwargs):
    """
    批量处理列表项目，避免一次性请求过多数据导致API限制
    
    参数:
        items: 要处理的项目列表
        batch_size: 每批处理的项目数
        process_func: 处理每批项目的函数
        *args, **kwargs: 传递给process_func的额外参数
    
    返回:
        list: 所有批次处理结果的列表
    """
    if not items or not process_func:
        return []
    
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        logger.info(f"处理批次 {batch_num}/{total_batches} ({len(batch)} 项目)")
        
        try:
            batch_result = process_func(batch, *args, **kwargs)
            results.append(batch_result)
            
            # 如果不是最后一批，短暂暂停以避免API限制
            if batch_num < total_batches:
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"处理批次 {batch_num} 时出错: {e}")
    
    return results 