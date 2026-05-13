import sqlite3

# 检查竞品分析数据库
conn1 = sqlite3.connect('data/ecoer_prices.db')
cur1 = conn1.cursor()
print('=== 竞品分析数据库 (ecoer_prices.db) ===')
cur1.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables1 = [t[0] for t in cur1.fetchall()]
print('表:', tables1)
print('产品数:', cur1.execute('SELECT COUNT(*) FROM products').fetchone()[0])
print('价格数:', cur1.execute('SELECT COUNT(*) FROM price_quotes').fetchone()[0])
conn1.close()

print()

# 检查价格查询数据库
conn2 = sqlite3.connect('data/ecoer_pricing.db')
cur2 = conn2.cursor()
print('=== 价格查询数据库 (ecoer_pricing.db) ===')
cur2.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables2 = [t[0] for t in cur2.fetchall()]
print('表:', tables2)
print('产品数:', cur2.execute('SELECT COUNT(*) FROM ecoer_products').fetchone()[0])
print('客户数:', cur2.execute('SELECT COUNT(*) FROM ecoer_customers').fetchone()[0])
print('价格数:', cur2.execute('SELECT COUNT(*) FROM ecoer_prices').fetchone()[0])
print('用户数:', cur2.execute('SELECT COUNT(*) FROM ecoer_users').fetchone()[0])
conn2.close()
