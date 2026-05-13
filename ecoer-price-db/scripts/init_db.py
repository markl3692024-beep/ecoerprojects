# -*- coding: utf-8 -*-
"""
Ecoer Price Database - 数据库初始化脚本
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ecoer_prices.db"
SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "database.sql"


def init_database():
    """初始化数据库"""
    # 确保data目录存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # 创建数据库连接
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 执行schema
    cursor.executescript(schema)
    conn.commit()
    
    # 插入示例地区数据
    sample_regions = [
        ('Los Angeles', 'CA', 'Hot-Humid'),
        ('San Francisco', 'CA', 'Marine'),
        ('Phoenix', 'AZ', 'Hot-Dry'),
        ('Dallas', 'TX', 'Hot-Humid'),
        ('Houston', 'TX', 'Hot-Humid'),
        ('Miami', 'FL', 'Hot-Humid'),
        ('New York', 'NY', 'Mixed-Humid'),
        ('Chicago', 'IL', 'Mixed'),
        ('Denver', 'CO', 'Cold-Dry'),
        ('Seattle', 'WA', 'Marine'),
        ('Atlanta', 'GA', 'Hot-Humid'),
        ('Boston', 'MA', 'Mixed-Humid'),
        ('Detroit', 'MI', 'Cold-Humid'),
        ('Minneapolis', 'MN', 'Cold'),
        ('Las Vegas', 'NV', 'Hot-Dry'),
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO regions (name, state, zone) VALUES (?, ?, ?)",
        sample_regions
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    
    print(f"[OK] Database initialized: {DB_PATH}")


if __name__ == "__main__":
    init_database()
