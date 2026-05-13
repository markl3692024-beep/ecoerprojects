import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'ecoer_pricing.db'
EXCEL_PATH = r"C:\Users\Mark\.qclaw\media\inbound\Ecoer_Northeast_Regular_Customer_List_Price---f2a84aeb-94ad-43ef-9351-6e621c91b516.xlsx"

def import_data():
    # 读取Excel
    df = pd.read_excel(EXCEL_PATH, sheet_name=0)
    
    # 跳过第一行（表头）
    df = df.iloc[1:].reset_index(drop=True)
    
    # 重命名列
    df.columns = ['series', 'refrigerant', 'product_type', 'model', 'seer2', 'hspf2', 'afue', 'description', 'list_price']
    
    # 清理数据
    df['model'] = df['model'].astype(str).str.strip()
    df['list_price'] = pd.to_numeric(df['list_price'], errors='coerce')
    
    # 生成SKU（从model提取）
    df['sku'] = df['model'].str.replace('ABA$', '', regex=True)
    
    # 映射品类
    category_map = {
        'ODU': 'Condenser',
        'AHU': 'Air Handler', 
        'A-Coil': 'Coil',
        'Heat Kit': 'Heat Kit',
        'Thermostat': 'Thermostat'
    }
    df['category'] = df['product_type'].map(category_map).fillna('Other')
    
    # 提取吨数从description
    import re
    def extract_tons(desc):
        if pd.isna(desc):
            return None
        match = re.search(r'(\d+)\s*Ton', str(desc))
        return match.group(1) + ' Ton' if match else None
    df['tons'] = df['description'].apply(extract_tons)
    
    # 清理SEER2
    df['seer'] = df['seer2'].replace('/', None)
    
    # 清理HSPF2
    df['hspf'] = df['hspf2'].replace('/', None)
    
    print(f"准备导入 {len(df)} 个产品")
    print(df[['sku', 'model', 'category', 'series', 'list_price']].head(10))
    
    # 连接数据库
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # 创建 Northeast Regular Customer 客户
    cur.execute("""
        INSERT OR IGNORE INTO ecoer_customers (customer_code, customer_name, customer_type, region, discount_tier, default_multiplier)
        VALUES ('NE_REG', 'Northeast Regular Customer', 'Distributor', 'NY,NJ,CT,MA,PA', 'Standard', 1.0)
    """)
    
    # 获取客户ID
    cur.execute("SELECT id FROM ecoer_customers WHERE customer_code = 'NE_REG'")
    customer_id = cur.fetchone()[0]
    print(f"\n客户ID: {customer_id}")
    
    # 导入产品
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
                row['sku'],
                row['model'],
                f"Ecoer {row['series']} {row['product_type']}",
                row['category'],
                row['series'],
                'Pro 2',
                row['description'],
                str(row['seer']) if pd.notna(row['seer']) else None,
                str(row['hspf']) if pd.notna(row['hspf']) else None,
                row['tons'],
                row['refrigerant']
            ))
            
            # 获取产品ID
            cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (row['sku'],))
            product_id = cur.fetchone()[0]
            
            # 插入价格（标准价格）
            cur.execute("""
                INSERT OR REPLACE INTO ecoer_prices (
                    product_id, customer_id, list_price, modifier, sales_price, 
                    price_type, effective_date, notes
                ) VALUES (?, NULL, ?, 1.0, ?, 'standard', DATE('now'), 'Northeast Regular Customer List Price')
            """, (product_id, row['list_price'], row['list_price']))
            
            imported += 1
            
        except Exception as e:
            print(f"Error importing {row['sku']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 成功导入 {imported} 个产品")

if __name__ == '__main__':
    import_data()
