#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库工具模块
提供数据库连接、表创建、数据存储和查询功能
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_utils')

# 数据库相关常量
DB_DIR = 'database'
DB_FILE = os.path.join(DB_DIR, 'market_data.db')

def ensure_db_dir():
    """确保数据库目录存在"""
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        logger.info(f"创建数据库目录: {DB_DIR}")

def get_db_connection():
    """
    获取数据库连接
    
    返回:
        sqlite3.Connection: 数据库连接对象
    """
    ensure_db_dir()
    conn = sqlite3.connect(DB_FILE)
    return conn

def create_tables():
    """创建必要的数据库表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建新高新低数据表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS high_low_stats (
        trade_date TEXT PRIMARY KEY,
        high_count_52w INTEGER,
        low_count_52w INTEGER,
        net_high_52w INTEGER,
        high_count_26w INTEGER,
        low_count_26w INTEGER,
        net_high_26w INTEGER,
        created_at TEXT
    )
    ''')
    
    # 创建股票数据表，用于缓存行情数据
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_daily_data (
        ts_code TEXT,
        trade_date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        pre_close REAL,
        change REAL,
        pct_chg REAL,
        vol REAL,
        amount REAL,
        PRIMARY KEY (ts_code, trade_date)
    )
    ''')
    
    # 创建数据库状态表，记录最后更新时间等信息
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS db_status (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("数据库表创建完成")

def save_high_low_stats(trade_date, high_count_52w, low_count_52w, high_count_26w, low_count_26w):
    """
    保存新高新低统计数据到数据库
    
    参数:
        trade_date: 交易日期，格式为'YYYYMMDD'
        high_count_52w: 52周新高数量
        low_count_52w: 52周新低数量
        high_count_26w: 26周新高数量
        low_count_26w: 26周新低数量
    
    返回:
        bool: 是否成功保存
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        net_high_52w = high_count_52w - low_count_52w
        net_high_26w = high_count_26w - low_count_26w
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 使用REPLACE INTO语法，如果记录已存在则替换
        cursor.execute('''
        REPLACE INTO high_low_stats 
        (trade_date, high_count_52w, low_count_52w, net_high_52w, high_count_26w, low_count_26w, net_high_26w, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (trade_date, high_count_52w, low_count_52w, net_high_52w, high_count_26w, low_count_26w, net_high_26w, created_at))
        
        conn.commit()
        conn.close()
        logger.info(f"交易日 {trade_date} 的新高新低数据已保存到数据库")
        return True
    except Exception as e:
        logger.error(f"保存新高新低数据时出错: {e}")
        return False

def save_stock_daily_data(df_daily):
    """
    保存股票日线数据到数据库
    
    参数:
        df_daily: 包含股票日线数据的DataFrame，必须包含ts_code和trade_date列
    
    返回:
        int: 保存的记录数量
    """
    if df_daily.empty:
        logger.warning("没有日线数据可保存")
        return 0
    
    try:
        conn = get_db_connection()
        # 确保必要的列存在
        required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close']
        for col in required_columns:
            if col not in df_daily.columns:
                logger.error(f"日线数据中缺少必要的列: {col}")
                return 0
        
        # 添加缺失的列，填充空值
        optional_columns = ['pre_close', 'change', 'pct_chg', 'vol', 'amount']
        for col in optional_columns:
            if col not in df_daily.columns:
                df_daily[col] = None
        
        # 使用临时表和INSERT OR IGNORE策略来避免主键冲突
        cursor = conn.cursor()
        
        # 创建临时表存储新数据
        cursor.execute('''
        CREATE TEMPORARY TABLE temp_stock_data (
            ts_code TEXT,
            trade_date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            pre_close REAL,
            change REAL,
            pct_chg REAL,
            vol REAL,
            amount REAL,
            PRIMARY KEY (ts_code, trade_date)
        )
        ''')
        
        # 准备数据并执行批量插入
        columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 
                  'pre_close', 'change', 'pct_chg', 'vol', 'amount']
        placeholders = ', '.join(['?'] * len(columns))
        
        insert_query = f'''
        INSERT INTO temp_stock_data ({', '.join(columns)})
        VALUES ({placeholders})
        '''
        
        # 准备数据
        data_to_insert = []
        for _, row in df_daily.iterrows():
            data_row = [row.get(col, None) for col in columns]
            data_to_insert.append(data_row)
        
        # 批量插入临时表
        cursor.executemany(insert_query, data_to_insert)
        
        # 从临时表插入到主表，忽略已存在的记录
        cursor.execute('''
        INSERT OR IGNORE INTO stock_daily_data
        SELECT * FROM temp_stock_data
        ''')
        
        # 获取实际插入的记录数
        inserted_count = cursor.rowcount
        
        # 关闭连接
        conn.commit()
        conn.close()
        
        if inserted_count > 0:
            logger.info(f"已保存 {inserted_count} 条股票日线数据到数据库")
        else:
            logger.debug("没有新的股票日线数据需要保存")
            
        return inserted_count
    except Exception as e:
        logger.error(f"保存股票日线数据时出错: {e}")
        return 0

def get_high_low_stats(start_date=None, end_date=None, days=None):
    """
    从数据库获取指定日期范围内的新高新低统计数据
    
    参数:
        start_date: 开始日期，格式为'YYYYMMDD'
        end_date: 结束日期，格式为'YYYYMMDD'
        days: 如果提供，将返回end_date前days天的数据
    
    返回:
        DataFrame: 包含新高新低统计数据的DataFrame
    """
    try:
        conn = get_db_connection()
        
        query = "SELECT * FROM high_low_stats"
        params = []
        
        # 构建查询条件
        conditions = []
        
        if start_date:
            conditions.append("trade_date >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("trade_date <= ?")
            params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # 添加排序
        query += " ORDER BY trade_date ASC"
        
        # 执行查询
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        # 如果提供了days参数，只返回最后days天的数据
        if days and len(df) > days:
            df = df.tail(days)
        
        # 添加格式化的日期列，便于绘图使用
        if not df.empty:
            df['formatted_date'] = df['trade_date'].apply(
                lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}" if len(x) == 8 else x
            )
            df['date'] = pd.to_datetime(df['trade_date'])
        
        return df
    except Exception as e:
        logger.error(f"获取新高新低统计数据时出错: {e}")
        return pd.DataFrame()

def get_stock_daily_data(ts_code, start_date, end_date):
    """
    从数据库获取股票日线数据
    
    参数:
        ts_code: 股票代码
        start_date: 开始日期，格式为'YYYYMMDD'
        end_date: 结束日期，格式为'YYYYMMDD'
    
    返回:
        DataFrame: 包含股票日线数据的DataFrame
    """
    try:
        conn = get_db_connection()
        
        query = """
        SELECT * FROM stock_daily_data 
        WHERE ts_code = ? AND trade_date >= ? AND trade_date <= ?
        ORDER BY trade_date ASC
        """
        
        df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
        conn.close()
        
        return df
    except Exception as e:
        logger.error(f"获取股票 {ts_code} 的日线数据时出错: {e}")
        return pd.DataFrame()

def get_latest_trade_date_in_db():
    """
    获取数据库中最新的交易日期
    
    返回:
        str: 最新交易日期，格式为'YYYYMMDD'，如果没有数据则返回None
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(trade_date) FROM high_low_stats")
        latest_date = cursor.fetchone()[0]
        
        conn.close()
        
        return latest_date
    except Exception as e:
        logger.error(f"获取数据库中最新交易日期时出错: {e}")
        return None

def update_db_status(key, value):
    """
    更新数据库状态信息
    
    参数:
        key: 状态键
        value: 状态值
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "REPLACE INTO db_status (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"数据库状态已更新: {key} = {value}")
    except Exception as e:
        logger.error(f"更新数据库状态时出错: {e}")

def get_db_status(key, default=None):
    """
    获取数据库状态信息
    
    参数:
        key: 状态键
        default: 如果键不存在，返回的默认值
    
    返回:
        str: 状态值
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM db_status WHERE key = ?", (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else default
    except Exception as e:
        logger.error(f"获取数据库状态时出错: {e}")
        return default

def clear_old_stock_data(days_to_keep=120):
    """
    清理旧的股票日线数据，保留最近days_to_keep天的数据
    
    参数:
        days_to_keep: 要保留的天数
    
    返回:
        int: 清理的记录数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有交易日期
        cursor.execute("SELECT DISTINCT trade_date FROM stock_daily_data ORDER BY trade_date DESC")
        all_dates = [row[0] for row in cursor.fetchall()]
        
        if len(all_dates) <= days_to_keep:
            logger.info(f"股票日线数据不足 {days_to_keep} 天，无需清理")
            return 0
        
        # 获取要保留的日期
        dates_to_keep = all_dates[:days_to_keep]
        cutoff_date = dates_to_keep[-1]
        
        # 删除旧数据
        cursor.execute("DELETE FROM stock_daily_data WHERE trade_date < ?", (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"已清理 {deleted_count} 条旧的股票日线数据，保留 {days_to_keep} 天数据")
        return deleted_count
    except Exception as e:
        logger.error(f"清理旧股票数据时出错: {e}")
        return 0

# 初始化数据库
def init_database():
    """初始化数据库，创建必要的表"""
    ensure_db_dir()
    create_tables()
    logger.info("数据库初始化完成")

# 当模块加载时自动初始化数据库
init_database()

def recreate_tables():
    """清理所有表并重新创建数据库结构"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # 删除所有表
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        conn.commit()
        logger.info("所有表已删除")
        
        # 重新创建表
        create_tables()
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"重建数据库表时出错: {e}")
        return False 