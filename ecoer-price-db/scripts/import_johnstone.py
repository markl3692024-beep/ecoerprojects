# -*- coding: utf-8 -*-
import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ecoer_prices.db"
file_path = r"C:\Users\Mark\.qclaw\media\inbound\johnstone_NY_pricing_09232025---20c1d9bf-b65a-425f-92d3-580c26c20036.xlsx"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Read data
df = pd.read_excel(file_path, sheet_name='Sheet1')

# Clean column names (remove trailing spaces)
df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]

print(f"Columns: {list(df.columns)}")
print(f"Total rows: {len(df)}")

# Clean and filter
df_clean = df[df['Brand'].notna()].copy()
df_clean = df_clean[df_clean['Type'].notna()]
df_clean = df_clean[df_clean['Brand'] != 'NaN']

print(f"Clean rows: {len(df_clean)}")

saved = 0
for idx, row in df_clean.iterrows():
    try:
        bosch_model = str(row['Model']).strip() if pd.notna(row['Model']) else None
        ecoer_model = str(row['Model.1']).strip() if pd.notna(row['Model.1']) else None
        
        if not bosch_model or bosch_model == 'nan' or not ecoer_model or ecoer_model == 'nan':
            continue
        
        # Get category
        prod_type = str(row['Type']).upper()
        if 'HANDLER' in prod_type:
            category_id = 8  # Air Handler
        elif 'OD' in prod_type or 'OUTDOOR' in prod_type:
            category_id = 9  # Condenser
        elif 'EHK' in prod_type:
            category_id = 8  # Air Handler (EHK)
        elif 'THERMO' in prod_type:
            category_id = None
        else:
            category_id = 2  # Central AC
        
        # Insert BOSCH product
        cursor.execute('''
            INSERT OR REPLACE INTO products (brand, model_number, category_id, refrigerant)
            VALUES (?, ?, ?, ?)
        ''', (str(row['Brand']), bosch_model, category_id, row.get('Refrigerant')))
        bosch_product_id = cursor.lastrowid
        
        # Insert Ecoer product
        cursor.execute('''
            INSERT OR REPLACE INTO products (brand, model_number, category_id, refrigerant)
            VALUES (?, ?, ?, ?)
        ''', ('Ecoer', ecoer_model, category_id, row.get('Refrigerant.1')))
        ecoer_product_id = cursor.lastrowid
        
        # BOSCH price (use distributor price, fallback to sales price)
        bosch_price = row['Distributor price to contactor'] if pd.notna(row['Distributor price to contactor']) else row['Bosch Sales Price']
        if bosch_price and float(bosch_price) > 0:
            cursor.execute('''
                INSERT INTO price_quotes (product_id, region_id, price, source_type, quote_date)
                VALUES (?, 2, ?, 'Johnstone Supply', '2025-09-23')
            ''', (bosch_product_id, bosch_price))
        
        # Ecoer price
        ecoer_price = row['Ecoer sales price'] if pd.notna(row['Ecoer sales price']) else None
        if ecoer_price and float(ecoer_price) > 0:
            cursor.execute('''
                INSERT INTO price_quotes (product_id, region_id, price, source_type, quote_date)
                VALUES (?, 2, ?, 'Johnstone Supply', '2025-09-23')
            ''', (ecoer_product_id, ecoer_price))
            
            # Ecoer mapping
            gap = row['Gap'] if pd.notna(row['Gap']) else 0
            cursor.execute('''
                INSERT INTO ecoer_mapping (competitor_product_id, ecoer_model, ecoer_price, price_gap_pct)
                VALUES (?, ?, ?, ?)
            ''', (bosch_product_id, ecoer_model, ecoer_price, gap))
            
            saved += 1
            
    except Exception as e:
        print(f"Error on row {idx}: {e}")

conn.commit()
print(f"\n[OK] Saved {saved} product pairs to database")
conn.close()
