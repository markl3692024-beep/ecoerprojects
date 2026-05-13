import pandas as pd
import sqlite3
from pathlib import Path
import re

DB_PATH = Path(__file__).parent / 'data' / 'ecoer_pricing.db'
EXCEL_PATH = r"C:\Users\Mark\.qclaw\media\inbound\Ecoer_Northeast_Regular_Customer_List_Price---f2a84aeb-94ad-43ef-9351-6e621c91b516.xlsx"

def import_data():
    # 读取Excel
    df = pd.read_excel(EXCEL_PATH, sheet_name=0)
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = ['series', 'refrigerant', 'product_type', 'model', 'seer2', 'hspf2', 'afue', 'description', 'list_price']
    df['model'] = df['model'].astype(str).str.strip()
    df['list_price'] = pd.to_numeric(df['list_price'], errors='coerce')
    df['sku'] = df['model'].str.replace('ABA$', '', regex=True)
    
    category_map = {
        'ODU': 'Condenser',
        'AHU': 'Air Handler', 
        'A-Coil': 'Coil',
        'Heat Kit': 'Heat Kit',
        'Thermostat': 'Thermostat'
    }
    df['category'] = df['product_type'].map(category_map).fillna('Other')
    
    def extract_tons(desc):
        if pd.isna(desc):
            return None
        match = re.search(r'(\d+)\s*Ton', str(desc))
        return match.group(1) + ' Ton' if match else None
    df['tons'] = df['description'].apply(extract_tons)
    df['seer'] = df['seer2'].replace('/', None)
    df['hspf'] = df['hspf2'].replace('/', None)
    
    print(f"准备导入 {len(df)} 个产品")
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # 1. 创建 List Price 版本
    cur.execute("""
        INSERT INTO ecoer_price_lists (price_list_code, price_list_name, description, region, effective_date)
        VALUES ('NE_REG', 'Northeast Regular Customer', 'Northeast region regular customer pricing', 'NY,NJ,CT,MA,PA', DATE('now'))
    """)
    price_list_id = cur.lastrowid
    print(f"List Price 版本 ID: {price_list_id}")
    
    # 2. 创建客户并绑定到该 List Price
    cur.execute("""
        INSERT INTO ecoer_customers (customer_code, customer_name, customer_type, region, discount_tier, price_list_id, default_modifier)
        VALUES ('NE_REG', 'Northeast Regular Customer', 'Distributor', 'NY,NJ,CT,MA,PA', 'Standard', ?, 1.0)
    """, (price_list_id,))
    print(f"客户已创建，绑定到 List Price ID: {price_list_id}")
    
    # 3. 导入产品和 List Price 明细
    imported = 0
    for idx, row in df.iterrows():
        if pd.isna(row['list_price']):
            continue
            
        try:
            # 插入产品
            cur.execute("""
                INSERT OR REPLACE INTO ecoer_products (
                    sku, model_number, product_name, category, series, sub_series,
                    description, seer, hspf, tons, refrigerant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['sku'], row['model'],
                f"Ecoer {row['series']} {row['product_type']}",
                row['category'], row['series'], 'Pro 2',
                row['description'],
                str(row['seer']) if pd.notna(row['seer']) else None,
                str(row['hspf']) if pd.notna(row['hspf']) else None,
                row['tons'], row['refrigerant']
            ))
            
            # 获取产品ID
            cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (row['sku'],))
            product_id = cur.fetchone()[0]
            
            # 插入 List Price 明细
            cur.execute("""
                INSERT OR REPLACE INTO ecoer_list_prices (price_list_id, product_id, list_price, notes)
                VALUES (?, ?, ?, 'Northeast Regular Customer List Price')
            """, (price_list_id, product_id, row['list_price']))
            
            imported += 1
        except Exception as e:
            print(f"Error: {row['sku']}: {e}")
    
    conn.commit()
    conn.close()
    print(f"成功导入 {imported} 个产品和价格")

if __name__ == '__main__':
    import_data()
