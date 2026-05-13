import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'ecoer_pricing.db'
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

print("=== 检查产品描述 ===")
print()

cur.execute("""
    SELECT sku, model_number, description, short_desc 
    FROM ecoer_products 
    WHERE is_active = 1 
    LIMIT 10
""")

for row in cur.fetchall():
    print(f"SKU: {row[0]}")
    print(f"Model: {row[1]}")
    print(f"Description: {row[2]}")
    print(f"Short Desc: {row[3]}")
    print("-" * 50)

conn.close()
