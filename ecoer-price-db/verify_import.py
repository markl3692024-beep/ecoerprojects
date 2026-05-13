import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'ecoer_pricing.db'
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

print("=== 导入验证 ===")
print()

print("客户:")
cur.execute("SELECT customer_code, customer_name, region FROM ecoer_customers WHERE is_active = 1")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} ({row[2]})")

print()
print("产品统计:")
cur.execute("SELECT category, COUNT(*) FROM ecoer_products WHERE is_active = 1 GROUP BY category")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} 个")

print()
print("价格统计:")
cur.execute("SELECT COUNT(*), AVG(list_price), MIN(list_price), MAX(list_price) FROM ecoer_prices WHERE is_active = 1")
row = cur.fetchone()
print(f"  共 {row[0]} 条价格记录")
print(f"  平均 List Price: ${row[1]:.2f}")
print(f"  最低: ${row[2]:.2f}, 最高: ${row[3]:.2f}")

print()
print("示例产品:")
cur.execute("""
    SELECT p.sku, p.model_number, p.category, p.series, p.seer, p.tons, pr.list_price
    FROM ecoer_products p
    JOIN ecoer_prices pr ON p.id = pr.product_id
    WHERE pr.is_active = 1
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | SEER:{row[4]} | {row[5]} | ${row[6]}")

conn.close()
