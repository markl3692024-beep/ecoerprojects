# -*- coding: utf-8 -*-
import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ecoer_prices.db"
file_path = r"C:\Users\Mark\.qclaw\media\inbound\Green_Earth_Pricebook_All_Rows_March_2026---af82f1ca-226d-4188-b1c5-f6c9a02ea61b.xlsx"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Read main data sheet
df = pd.read_excel(file_path, sheet_name='Green_Earth_Pricebook_All_Rows ')
df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]

print(f"Total rows: {len(df)}")
print(f"Brands: {df['Brand'].unique()}")
print(f"Categories: {df['Category'].unique()}")

# Map categories to our category table
category_map = {
    'Gas Furnace': 'Furnace',
    'Packaged GE': 'Packaged AC/Gas',
    'Packaged HP': 'Heat Pump',
    'Air Handler': 'Air Handler',
    'Condenser': 'Condenser',
    'Residential AC': 'Central AC',
    'Commercial AC': 'Commercial AC',
}

saved = 0
skipped = 0

for idx, row in df.iterrows():
    try:
        brand = str(row['Brand']).strip() if pd.notna(row['Brand']) else None
        model = str(row['part_no']).strip() if pd.notna(row['part_no']) else None
        category = str(row['Category']).strip() if pd.notna(row['Category']) else None
        
        if not brand or not model or brand == 'nan' or model == 'nan' or brand == 'nan' or model == 'nan':
            skipped += 1
            continue
        
        # Get category_id
        cat_name = category_map.get(category, category)
        cursor.execute('SELECT id FROM categories WHERE name LIKE ? LIMIT 1', (f'%{cat_name}%',))
        result = cursor.fetchone()
        category_id = result[0] if result else None
        
        # Extract capacity
        capacity = row.get('Capacity')
        if pd.notna(capacity):
            capacity = str(capacity)
        
        # Extract capacity (try to parse tons or BTU)
        cap_str = str(row.get('Capacity', '')) if pd.notna(row.get('Capacity')) else ''
        capacity_tons = None
        capacity_btuh = None
        if 'Ton' in cap_str or 'ton' in cap_str:
            try:
                capacity_tons = float(''.join(filter(lambda x: x.isdigit() or x == '.', cap_str)))
            except:
                pass
        
        # Get SEER2/AFUE
        seer_val = row.get('SEER2/AFUE')
        seer = float(seer_val) if pd.notna(seer_val) else None
        
        # Get voltage
        voltage = str(row.get('Voltage')).strip() if pd.notna(row.get('Voltage')) else None
        
        # Insert product
        cursor.execute('''
            INSERT OR REPLACE INTO products (brand, model_number, category_id, refrigerant, capacity_tons, capacity_btuh, efficiency_seer, voltage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (brand, model, category_id, row.get('Refrigerant'), capacity_tons, capacity_btuh, seer, voltage))
        product_id = cursor.lastrowid
        
        # Distributor price
        dist_price = row.get('Distributior price')
        if pd.notna(dist_price) and float(dist_price) > 0:
            cursor.execute('''
                INSERT INTO price_quotes (product_id, region_id, price, source_name, source_type, quote_date)
                VALUES (?, 2, ?, 'Green Earth', 'distributor', '2026-03-01')
            ''', (product_id, dist_price))
        
        # Manufacturer price
        mfg_price = row.get('Manufacturer Price')
        if pd.notna(mfg_price) and float(mfg_price) > 0:
            cursor.execute('''
                INSERT INTO price_quotes (product_id, region_id, price, source_name, source_type, quote_date)
                VALUES (?, 2, ?, 'Green Earth', 'manufacturer', '2026-03-01')
            ''', (product_id, mfg_price))
        
        saved += 1
        
    except Exception as e:
        print(f"Error on row {idx}: {e}")
        skipped += 1

conn.commit()

# Summary by brand
print(f"\n=== Import Summary ===")
print(f"Saved: {saved} products")
print(f"Skipped: {skipped}")

cursor.execute('''
    SELECT brand, COUNT(*) as cnt 
    FROM products 
    GROUP BY brand 
    ORDER BY cnt DESC
''')
print("\nBy Brand:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} products")

conn.close()
print("\n[OK] Green Earth data imported!")
