import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'ecoer_pricing.db'

def init_database():
    """初始化 V2 数据库"""
    # 删除旧数据库
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("已删除旧数据库")
    
    # 创建新数据库
    conn = sqlite3.connect(str(DB_PATH))
    
    # 读取并执行 schema
    schema_path = Path(__file__).parent / 'schema' / 'ecoer_pricing_v2.sql'
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    
    conn.commit()
    conn.close()
    print(f"数据库已初始化: {DB_PATH}")

if __name__ == '__main__':
    init_database()
