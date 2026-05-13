# -*- coding: utf-8 -*-
"""
Ecoer Price Database - PDF解析脚本
支持文本PDF和扫描PDF(需要OCR)
"""
import pdfplumber
import pandas as pd
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = Path(__file__).parent.parent / "data" / "ecoer_prices.db"


class PDFExtractor:
    """PDF价格数据提取器"""
    
    # 品牌关键词
    BRAND_PATTERNS = {
        'Carrier': ['Carrier', 'carrier'],
        'Trane': ['Trane', 'trane'],
        'Lennox': ['Lennox', 'lennox'],
        'Rheem': ['Rheem', 'rheem'],
        'Goodman': ['Goodman', 'goodman'],
        'Daikin': ['Daikin', 'daikin'],
        'Mitsubishi': ['Mitsubishi', 'mitsubishi'],
        'LG': ['LG ', 'LG-', 'lg'],
        'Samsung': ['Samsung', 'samsung'],
        'Fujitsu': ['Fujitsu', 'fujitsu'],
        'Gree': ['Gree', 'gree'],
        'Midea': ['Midea', 'midea'],
        'York': ['York', 'york'],
        'American Standard': ['American Standard', 'american standard'],
        'Bryant': ['Bryant', 'bryant'],
        'Coleman': ['Coleman', 'coleman'],
        'Ecoer': ['ecoer', 'Ecoer', 'ECOER'],
    }
    
    BTU_TON_RATIO = 12000
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
    
    def connect_db(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
    
    def extract_brand(self, text: str) -> Optional[str]:
        text_upper = text.upper()
        for brand, patterns in self.BRAND_PATTERNS.items():
            for pattern in patterns:
                if pattern.upper() in text_upper:
                    return brand
        return None
    
    def extract_model_number(self, text: str) -> Optional[str]:
        patterns = [
            r'([A-Z]{2,}[-\s]?\d{2,}[A-Z0-9-]*)',
            r'(24ACB?\d+)',
            r'(R410A[-]?\w+)',
            r'(MSZ?[-]?\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def extract_capacity(self, text: str) -> Tuple[Optional[int], Optional[float]]:
        btuh = None
        tons = None
        
        ton_match = re.search(r'(\d+\.?\d*)\s*[Tt]on', text)
        if ton_match:
            tons = float(ton_match.group(1))
            btuh = int(tons * self.BTU_TON_RATIO)
        
        btu_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*[Bb][Tt][Uu]', text)
        if btu_match:
            btuh = int(btu_match.group(1).replace(',', ''))
            if not tons:
                tons = round(btuh / self.BTU_TON_RATIO, 1)
        
        return btuh, tons
    
    def extract_seer(self, text: str) -> Optional[float]:
        match = re.search(r'SEER\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r'(\d{1,2})\s*SEER', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def extract_price(self, text: str) -> Optional[float]:
        match = re.search(r'\$[\s]?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
        if match:
            price = float(match.group(1).replace(',', ''))
            if 100 < price < 100000:
                return price
        return None
    
    def extract_region(self, text: str, df_regions: pd.DataFrame) -> Optional[int]:
        text_upper = text.upper()
        for _, row in df_regions.iterrows():
            if row['name'].upper() in text_upper or row['state'].upper() in text_upper:
                return row['id']
        return None
    
    def process_pdf(self, file_path: str) -> Dict:
        """处理PDF文件"""
        all_text = []
        tables = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                # 提取文本
                text = page.extract_text()
                if text:
                    all_text.append(text)
                
                # 提取表格
                page_tables = page.extract_tables()
                for table in page_tables:
                    if table:
                        tables.extend(table)
        
        # 读取地区数据
        conn = self.connect_db()
        df_regions = pd.read_sql("SELECT * FROM regions", conn)
        conn.close()
        
        results = []
        combined_text = '\n'.join(all_text)
        
        # 尝试从表格中提取
        if tables:
            for table in tables:
                for row in table:
                    row_text = ' '.join([str(c) for c in row if c])
                    
                    brand = self.extract_brand(row_text)
                    model = self.extract_model_number(row_text)
                    price = self.extract_price(row_text)
                    
                    if brand or model:
                        record = {
                            'brand': brand,
                            'model_number': model,
                            'capacity_btuh': self.extract_capacity(row_text)[0],
                            'capacity_tons': self.extract_capacity(row_text)[1],
                            'efficiency_seer': self.extract_seer(row_text),
                            'price': price,
                            'region_id': self.extract_region(row_text, df_regions),
                            'source_type': 'PDF Import',
                            'quote_date': datetime.now().date().isoformat(),
                        }
                        results.append(record)
        
        # 如果表格没有提取到，尝试从全文提取
        if not results:
            # 简单的行分析
            lines = combined_text.split('\n')
            for line in lines:
                brand = self.extract_brand(line)
                model = self.extract_model_number(line)
                price = self.extract_price(line)
                
                if (brand or model) and price:
                    record = {
                        'brand': brand,
                        'model_number': model,
                        'capacity_btuh': self.extract_capacity(line)[0],
                        'capacity_tons': self.extract_capacity(line)[1],
                        'efficiency_seer': self.extract_seer(line),
                        'price': price,
                        'region_id': self.extract_region(line, df_regions),
                        'source_type': 'PDF Import',
                        'quote_date': datetime.now().date().isoformat(),
                    }
                    results.append(record)
        
        return {
            'total_pages': len(all_text),
            'tables_found': len(tables),
            'extracted_records': len(results),
            'records': results,
            'full_text_preview': combined_text[:2000]  # 预览前2000字符
        }
    
    def save_to_database(self, records: List[Dict], metadata: Dict = None) -> int:
        """
        保存记录到数据库
        
        Args:
            records: 记录列表
            metadata: 可选元数据字典，包含:
                - region_id: 地区ID
                - quote_date: 报价日期 (YYYY-MM-DD)
                - source_name: 来源名称
        """
        conn = self.connect_db()
        cursor = conn.cursor()
        saved_count = 0
        
        # 从metadata获取默认值
        default_region_id = metadata.get('region_id') if metadata else None
        default_quote_date = metadata.get('quote_date') if metadata else None
        default_source_name = metadata.get('source_name') if metadata else 'PDF Import'
        
        for record in records:
            try:
                if not record.get('brand') and not record.get('model_number'):
                    continue
                
                # 检查产品是否已存在
                cursor.execute(
                    """SELECT id FROM products 
                       WHERE brand = ? AND model_number = ?""",
                    (record.get('brand'), record.get('model_number'))
                )
                result = cursor.fetchone()
                
                if result:
                    product_id = result[0]
                else:
                    cursor.execute("""
                        INSERT INTO products (brand, model_number, capacity_btuh, capacity_tons, efficiency_seer)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        record.get('brand'),
                        record.get('model_number'),
                        record.get('capacity_btuh'),
                        record.get('capacity_tons'),
                        record.get('efficiency_seer'),
                    ))
                    product_id = cursor.lastrowid
                
                if record.get('price'):
                    # 使用metadata中的值或record中的值
                    region_id = record.get('region_id') or default_region_id
                    quote_date = record.get('quote_date') or default_quote_date
                    source_name = record.get('source_name') or default_source_name
                    
                    cursor.execute("""
                        INSERT INTO price_quotes (product_id, region_id, price, source_name, source_type, quote_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        product_id,
                        region_id,
                        record.get('price'),
                        source_name,
                        record.get('source_type', 'PDF Import'),
                        quote_date,
                    ))
                    saved_count += 1
                    
            except Exception as e:
                print(f"Error: {e}")
        
        conn.commit()
        conn.close()
        return saved_count


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python parse_pdf.py <pdf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"📄 正在处理PDF: {file_path}")
    
    extractor = PDFExtractor()
    result = extractor.process_pdf(file_path)
    
    print(f"\n📊 处理结果:")
    print(f"   页数: {result['total_pages']}")
    print(f"   发现表格: {result['tables_found']}")
    print(f"   提取记录: {result['extracted_records']}")
    
    if result['records']:
        print(f"\n📋 提取的数据:")
        for rec in result['records'][:5]:
            print(f"   {rec.get('brand', 'Unknown'):15} {rec.get('model_number', 'N/A'):20} "
                  f"${rec.get('price', 'N/A')}")
        
        saved = extractor.save_to_database(result['records'])
        print(f"\n✅ 已保存 {saved} 条记录")


if __name__ == "__main__":
    main()
