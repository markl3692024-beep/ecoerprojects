import sqlite3

conn = sqlite3.connect('data/ecoer_pricing.db')
cur = conn.cursor()

print('=== Ecoer 价格查询数据库状态 ===')
print()

print('用户:')
cur.execute('SELECT username, full_name, role FROM ecoer_users')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} ({row[2]})')

print()
print('产品数量:', cur.execute('SELECT COUNT(*) FROM ecoer_products').fetchone()[0])
print('客户数量:', cur.execute('SELECT COUNT(*) FROM ecoer_customers').fetchone()[0])
print('价格数量:', cur.execute('SELECT COUNT(*) FROM ecoer_prices').fetchone()[0])

conn.close()
