import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'ecoer_pricing.db'
conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

print("=== V3 数据库验证 ===")
print()

print("1. List Price 版本:")
cur.execute("SELECT id, price_list_code, price_list_name, region FROM ecoer_price_lists WHERE is_active = 1")
for row in cur.fetchall():
    print(f"   ID:{row[0]} | {row[1]}: {row[2]} ({row[3]})")

print()
print("2. 客户及绑定的 List Price:")
cur.execute("""
    SELECT c.customer_code, c.customer_name, pl.price_list_code, c.default_modifier
    FROM ecoer_customers c
    LEFT JOIN ecoer_price_lists pl ON c.price_list_id = pl.id
    WHERE c.is_active = 1
""")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]} | List: {row[2]} | Modifier: {row[3]:.0%}")

print()
print("3. List Price 价格数量:")
cur.execute("SELECT price_list_id, COUNT(*) FROM ecoer_list_prices WHERE is_active = 1 GROUP BY price_list_id")
for row in cur.fetchall():
    print(f"   List ID {row[0]}: {row[1]} 个产品价格")

print()
print("4. 示例产品价格:")
cur.execute("""
    SELECT p.sku, p.product_name, lp.list_price, pl.price_list_code
    FROM ecoer_list_prices lp
    JOIN ecoer_products p ON lp.product_id = p.id
    JOIN ecoer_price_lists pl ON lp.price_list_id = pl.id
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]} | ${row[2]} ({row[3]})")

conn.close()
