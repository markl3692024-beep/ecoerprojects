#!/usr/bin/env python3
"""
Goodman Product Catalog Import Script
Extracts products and prices from Goodman catalog PDF
Source: Daikin North East / JAMESWU HVAC
Date: 03/04/2026
"""

import pdfplumber
import sqlite3
import re
import os
from datetime import datetime

DB_PATH = r'C:\Users\Mark\.qclaw\workspace\ecoer-price-db\data\ecoer_prices.db'
PDF_PATH = r'C:\Users\Mark\.qclaw\media\inbound\Goodman_Catalog_Catalog_for_JAMESWU_HVAC_1---f54648f5-f839-45d1-b3e3-9ce9fcc4b573.pdf'

def extract_model_price(text):
    """Extract model number and price from text like 'MODEL123* $1,234'"""
    # Pattern: model number (may have * suffix) followed by price
    pattern = r'([A-Z0-9]{6,}[A-Z]?)\*\s*\$([0-9,]+)'
    matches = re.findall(pattern, text)
    return [(m[0], m[1].replace(',', '')) for m in matches]

def parse_capacity(model):
    """Extract capacity in tons/BTU from model number"""
    # Common patterns: 
    # 18 = 1.5 ton, 24 = 2 ton, 30 = 2.5 ton, 36 = 3 ton, 42 = 3.5 ton, 48 = 4 ton, 60 = 5 ton
    patterns = [
        r'(18|24|30|36|42|48|60|72|90|120)',  # BTU hundreds
    ]
    for p in patterns:
        m = re.search(p, model)
        if m:
            btuh = int(m.group(1)) * 100
            # Convert to tons (approximate)
            tons = btuh / 12000
            return btuh, round(tons, 1)
    return None, None

def determine_category(model):
    """Determine product category from model number"""
    if 'AHVE' in model or 'AMST' in model or 'AMVT' in model or 'MBVK' in model:
        return 'Air Handler'
    elif 'CAP' in model or 'CAPF' in model or 'CAPT' in model:
        return 'Evaporator Coil'
    elif 'CHP' in model or 'CHPE' in model:
        return 'Heat Pump'
    elif 'GLX' in model or 'GLZ' in model or 'GZV' in model or 'GXV' in model:
        return 'Condenser'
    elif 'GDV' in model or 'GD9' in model or 'GR9' in model or 'GM9' in model:
        return 'Furnace'
    elif 'GCV' in model or 'GMVC' in model:
        return 'Gas Furnace'
    elif model.startswith('0') or len(model) <= 10:
        return 'Accessory'
    else:
        return 'Other'

def determine_seer(model):
    """Extract SEER rating from model if available"""
    # SEER patterns in model numbers
    if '7C' in model or '7A' in model:
        return 17.0  # GLXT7C = 17 SEER
    elif '6S' in model:
        return 16.0  # GZV6S
    elif '5B' in model:
        return 15.0  # GLXS5B = 15.2 SEER2
    elif '4B' in model:
        return 14.0  # GLXS4B = 14.3 SEER2
    elif '3B' in model:
        return 13.0  # GLXS3B = 13.4 SEER2
    return None

def main():
    print('=' * 60)
    print('Goodman Product Catalog Import')
    print('=' * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    products_saved = 0
    prices_saved = 0
    skipped = 0
    
    # Process PDF
    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        print(f'Processing {total_pages} pages...')
        
        for page_num, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text()
            if not text:
                continue
            
            # Extract model/price pairs
            pairs = extract_model_price(text)
            
            for model, price_str in pairs:
                # Skip accessories (start with 0)
                category = determine_category(model)
                
                # Parse price
                try:
                    price = float(price_str)
                    if price == 0:
                        skipped += 1
                        continue
                except:
                    skipped += 1
                    continue
                
                # Parse capacity
                btuh, tons = parse_capacity(model)
                
                # Get SEER
                seer = determine_seer(model)
                
                # Determine brand
                brand = 'Goodman'
                if model.startswith('AM') and 'AMST' not in model and 'AMVT' not in model:
                    brand = 'Amana'
                
                # Get category ID
                cursor.execute("SELECT id FROM categories WHERE name = ?", (category,))
                result = cursor.execute("SELECT id FROM categories WHERE name = ?", (category,)).fetchone()
                if not result:
                    cursor.execute("INSERT INTO categories (name) VALUES (?)", (category,))
                    category_id = cursor.lastrowid
                else:
                    category_id = result[0]
                
                # Insert product
                try:
                    cursor.execute('''
                        INSERT INTO products (brand, model_number, category_id, capacity_btuh, capacity_tons, 
                                           efficiency_seer, refrigerant)
                        VALUES (?, ?, ?, ?, ?, ?, 'R-32')
                    ''', (brand, model, category_id, btuh, tons, seer))
                    product_id = cursor.lastrowid
                    products_saved += 1
                except sqlite3.IntegrityError:
                    # Product exists, get ID
                    result = cursor.execute(
                        "SELECT id FROM products WHERE model_number = ?", (model,)
                    ).fetchone()
                    if result:
                        product_id = result[0]
                        # Update with more info
                        cursor.execute('''
                            UPDATE products SET brand = ?, capacity_btuh = ?, capacity_tons = ?,
                                               efficiency_seer = ?
                            WHERE id = ?
                        ''', (brand, btuh, tons, seer, product_id))
                    else:
                        product_id = None
                
                # Insert price quote
                if product_id:
                    cursor.execute('''
                        INSERT INTO price_quotes (product_id, region_id, price, currency, unit,
                                                source_name, source_type, quote_date)
                        VALUES (?, 2, ?, 'USD', 'unit', 'JAMESWU HVAC', 'distributor', '2026-03-04')
                    ''', (product_id, price))
                    prices_saved += 1
                
                if (products_saved + prices_saved) % 50 == 0:
                    conn.commit()
    
    conn.commit()
    
    print()
    print('=== Import Summary ===')
    print(f'Products saved: {products_saved}')
    print(f'Prices saved: {prices_saved}')
    print(f'Skipped: {skipped}')
    print()
    
    # Summary by category
    print('By Category:')
    cursor.execute('''
        SELECT c.name, COUNT(p.id) as cnt
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.brand IN ('Goodman', 'Amana')
        GROUP BY c.name
        ORDER BY cnt DESC
    ''')
    for row in cursor.fetchall():
        print(f'  {row[0]}: {row[1]}')
    
    conn.close()
    print()
    print('[OK] Goodman catalog imported!')

if __name__ == '__main__':
    main()
