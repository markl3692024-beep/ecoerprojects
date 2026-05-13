import sqlite3
import json

conn = sqlite3.connect('C:/Users/Mark/.qclaw/workspace/ecoer-price-db/data/ecoer_pricing.db')
cur = conn.cursor()

# Create sales_rep user with password 'sales2026'
cur.execute("""
    INSERT INTO ecoer_users (username, password, full_name, role, territory, allowed_customers, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
""", ('sales_rep', 'sales2026', 'Sales Representative', 'sales_rep', 'South;West', json.dumps([])))

conn.commit()
print('sales_rep user created!')
print('Username: sales_rep')
print('Password: sales2026')
print('Territory: South;West')

# Verify
cur.execute('SELECT id, username, role, full_name, territory FROM ecoer_users')
for u in cur.fetchall():
    print(f'  User: {u}')

conn.close()
