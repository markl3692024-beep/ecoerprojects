# -*- coding: utf-8 -*-
"""
Ecoer Price Database - Excel解析脚本
支持解析各种格式的空调设备报价单
"""
import pandas as pd
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = Path(__file__).parent.parent / "data" / "ecoer_prices.db"


class PriceExtractor:
    """价格数据提取器"""
    
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
        ' Gree': ['Gree', 'gree'],
        'Midea': ['Midea', 'midea'],
        'York': ['York', 'york'],
        'American Standard': ['American Standard', 'american standard'],
        ' Bryant': ['Bryant', 'bryant'],
        'Coleman': ['Coleman', 'coleman'],
        ' ICP': ['ICP', 'icp'],
        'ecoer': ['ecoer', 'Ecoer', 'ECOER'],
    }
    
    # 品类关键词
    CATEGORY_PATTERNS = {
        'Mini Split': ['mini split', 'minisplit', 'mini-split', '分体'],
        'Central AC': ['central', 'central ac', 'split system'],
        'Heat Pump': ['heat pump', 'hp', '热泵'],
        'PTAC': ['ptac', 'PTAC', '窗机'],
        'Commercial Package': ['package', 'pkg', 'rtu', 'rooftop'],
        'Gas Furnace': ['furnace', 'gas', '炉'],
        'Air Handler': ['air handler', 'ahu', '处理机'],
        'Condenser': ['condenser', 'outdoor', ' outdoor unit'],
    }
    
    # 压缩机类型关键词
    COMPRESSOR_PATTERNS = {
        'Scroll': ['scroll', 'Scroll'],
        'Rotary': ['rotary', 'Rotary'],
        'Twin-Rotary': ['twin rotary', 'Twin Rotary', '双旋转'],
        'Inverter': ['inverter', 'Inverter', '变频'],
        'Variable Speed': ['variable speed', 'vs', '变速'],
    }
    
    # 单位换算
    BTU_TON_RATIO = 12000  # 1吨 = 12000 BTU/h
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
    
    def connect_db(self) -> sqlite3.Connection:
        """连接数据库"""
        return sqlite3.connect(self.db_path)
    
    def extract_brand(self, text: str) -> Optional[str]:
        """从文本中提取品牌"""
        text_upper = text.upper()
        for brand, patterns in self.BRAND_PATTERNS.items():
            for pattern in patterns:
                if pattern.upper() in text_upper:
                    return brand
        return None
    
    def extract_model_number(self, text: str) -> Optional[str]:
        """提取型号"""
        # 常见型号格式: 字母开头 + 数字 + 可选后缀
        patterns = [
            r'([A-Z]{2,}[-\s]?\d{2,}[A-Z0-9-]*)',  # TRANE-XL20i
            r'(24ACB?\d+)',  # 24ACB036
            r'(R410A[-]?\w+)',  # Rheem型号
            r'(MSZ?[-]?\w+)',  # Mitsubishi型号
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def extract_capacity(self, text: str) -> Tuple[Optional[int], Optional[float]]:
        """提取能力(容量) - 返回 BTU/h 和 吨"""
        btuh = None
        tons = None
        
        # 匹配格式: "3 Ton", "36,000 BTU", "3.5tons"
        ton_match = re.search(r'(\d+\.?\d*)\s*[Tt]on', text)
        if ton_match:
            tons = float(ton_match.group(1))
            btuh = int(tons * self.BTU_TON_RATIO)
        
        # 匹配BTU格式
        btu_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*[Bb][Tt][Uu]', text)
        if btu_match:
            btuh = int(btu_match.group(1).replace(',', ''))
            if not tons:
                tons = round(btuh / self.BTU_TON_RATIO, 1)
        
        return btuh, tons
    
    def extract_seer(self, text: str) -> Optional[float]:
        """提取SEER能效"""
        match = re.search(r'SEER\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r'(\d{1,2})\s*SEER', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def extract_eer(self, text: str) -> Optional[float]:
        """提取EER能效"""
        match = re.search(r'EER\s*(\d+\.?\d*)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r'(\d{1,2})\s*EER', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    
    def extract_price(self, value) -> Optional[float]:
        """提取价格"""
        if pd.isna(value):
            return None
        
        text = str(value)
        # 移除货币符号和逗号
        text = re.sub(r'[$¥€£]', '', text)
        text = re.sub(r',', '', text)
        
        # 匹配价格
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            price = float(match.group(1))
            # 价格合理性检查 (空调设备通常 $500 - $50000)
            if 100 < price < 100000:
                return price
        return None
    
    def extract_region(self, text: str, df_regions: pd.DataFrame) -> Optional[int]:
        """提取地区"""
        text_upper = text.upper()
        for _, row in df_regions.iterrows():
            if (row['name'].upper() in text_upper or 
                row['state'].upper() in text_upper):
                return row['id']
        return None
    
    def extract_category(self, text: str) -> Optional[str]:
        """提取品类"""
        text_lower = text.lower()
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    return category
        return 'Central AC'  # 默认品类
    
    def extract_compressor_type(self, text: str) -> Optional[str]:
        """提取压缩机类型"""
        text_lower = text.lower()
        for comp_type, patterns in self.COMPRESSOR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    return comp_type
        return None
    
    def process_excel(self, file_path: str, sheet_name: int = 0) -> Dict:
        """处理Excel文件"""
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # 读取地区数据
        conn = self.connect_db()
        df_regions = pd.read_sql("SELECT * FROM regions", conn)
        conn.close()
        
        results = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # 合并所有列为文本进行模式匹配
                combined_text = ' '.join([str(v) for v in row.values if pd.notna(v)])
                
                record = {
                    'brand': self.extract_brand(combined_text),
                    'model_number': self.extract_model_number(combined_text),
                    'capacity_btuh': self.extract_capacity(combined_text)[0],
                    'capacity_tons': self.extract_capacity(combined_text)[1],
                    'efficiency_seer': self.extract_seer(combined_text),
                    'efficiency_eer': self.extract_eer(combined_text),
                    'category': self.extract_category(combined_text),
                    'compressor_type': self.extract_compressor_type(combined_text),
                    'price': None,
                    'region_id': None,
                    'source_name': None,
                    'source_type': 'File Import',
                    'quote_date': datetime.now().date().isoformat(),
                }
                
                # 尝试从各列提取价格
                for col, value in row.items():
                    if record['price'] is None:
                        record['price'] = self.extract_price(value)
                    if record['region_id'] is None:
                        rid = self.extract_region(str(value), df_regions)
                        if rid:
                            record['region_id'] = rid
                
                # 只添加有品牌或型号的记录
                if record['brand'] or record['model_number']:
                    results.append(record)
                else:
                    errors.append(f"Row {idx + 2}: 无法识别品牌/型号")
                    
            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
        
        return {
            'total_rows': len(df),
            'extracted_records': len(results),
            'errors': errors[:10],  # 只返回前10个错误
            'records': results
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
        
        # 从metadata获取默认値
        default_region_id = metadata.get('region_id') if metadata else None
        default_quote_date = metadata.get('quote_date') if metadata else None
        default_source_name = metadata.get('source_name') if metadata else 'File Import'
        
        for record in records:
            try:
                # 获取品类ID
                category_id = None
                if record.get('category'):
                    cursor.execute(
                        "SELECT id FROM categories WHERE name = ?",
                        (record['category'],)
                    )
                    result = cursor.fetchone()
                    if result:
                        category_id = result[0]
                
                # 检查产品是否已存在
                cursor.execute(
                    """SELECT id FROM products 
                       WHERE brand = ? AND model_number = ?""",
                    (record.get('brand'), record.get('model_number'))
                )
                result = cursor.fetchone()
                
                if result:
                    product_id = result[0]
                    # 更新产品信息
                    cursor.execute("""
                        UPDATE products SET
                            capacity_btuh = COALESCE(?, capacity_btuh),
                            capacity_tons = COALESCE(?, capacity_tons),
                            efficiency_seer = COALESCE(?, efficiency_seer),
                            efficiency_eer = COALESCE(?, efficiency_eer),
                            compressor_type = COALESCE(?, compressor_type),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        record.get('capacity_btuh'),
                        record.get('capacity_tons'),
                        record.get('efficiency_seer'),
                        record.get('efficiency_eer'),
                        record.get('compressor_type'),
                        product_id
                    ))
                else:
                    # 插入新产品
                    cursor.execute("""
                        INSERT INTO products (
                            brand, model_number, category_id,
                            capacity_btuh, capacity_tons,
                            efficiency_seer, efficiency_eer,
                            compressor_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.get('brand'),
                        record.get('model_number'),
                        category_id,
                        record.get('capacity_btuh'),
                        record.get('capacity_tons'),
                        record.get('efficiency_seer'),
                        record.get('efficiency_eer'),
                        record.get('compressor_type'),
                    ))
                    product_id = cursor.lastrowid
                
                # 插入报价记录
                if record.get('price'):
                    # 使用metadata中的値或record中的値
                    region_id = record.get('region_id') or default_region_id
                    quote_date = record.get('quote_date') or default_quote_date
                    source_name = record.get('source_name') or default_source_name
                    
                    cursor.execute("""
                        INSERT INTO price_quotes (
                            product_id, region_id, price,
                            source_name, source_type, quote_date, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product_id,
                        region_id,
                        record.get('price'),
                        source_name,
                        record.get('source_type', 'File Import'),
                        quote_date,
                        json.dumps(record, ensure_ascii=False)
                    ))
                    saved_count += 1
                    
            except Exception as e:
                print(f"Error saving record: {e}")
        
        conn.commit()
        conn.close()
        return saved_count


def main():
    """命令行入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python parse_excel.py <excel_file>")
        print("示例: python parse_excel.py prices.xlsx")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"📄 正在处理: {file_path}")
    
    extractor = PriceExtractor()
    result = extractor.process_excel(file_path)
    
    print(f"\n📊 处理结果:")
    print(f"   总行数: {result['total_rows']}")
    print(f"   提取记录: {result['extracted_records']}")
    
    if result['errors']:
        print(f"\n⚠️ 前10个错误:")
        for err in result['errors'][:10]:
            print(f"   - {err}")
    
    if result['records']:
        print(f"\n📋 提取的数据预览:")
        for rec in result['records'][:5]:
            print(f"   {rec.get('brand', 'Unknown'):15} {rec.get('model_number', 'N/A'):20} "
                  f"${rec.get('price', 'N/A'):>10} SEER:{rec.get('efficiency_seer', 'N/A')}")
        
        # 保存到数据库
        saved = extractor.save_to_database(result['records'])
        print(f"\n✅ 已保存 {saved} 条报价到数据库")


if __name__ == "__main__":
    main()
