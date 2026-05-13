# Ecoer Price Intelligence System
# Ecoer价格情报系统

## 快速开始

### 1. 安装依赖
```
pip install openpyxl pandas pdfplumber streamlit
```

### 2. 初始化数据库
```
python scripts/init_db.py
```

### 3. 启动Web界面
```
streamlit run app/app.py
```

### 4. 使用系统

**上传数据**:
- 支持 Excel (.xlsx, .xls) 和 PDF 文件
- 系统会自动识别品牌、型号、价格等信息
- 提取后确认数据，保存到数据库

**查询数据**:
- 按品牌、品类、地区筛选
- 查看价格统计

**分析报表**:
- 品牌价格对比
- 品类价格分析
- 地区价格分析

---

## 项目结构

```
ecoer-price-db/
├── schema/
│   └── database.sql      # 数据库Schema
├── scripts/
│   ├── init_db.py        # 数据库初始化
│   ├── parse_excel.py    # Excel解析
│   └── parse_pdf.py      # PDF解析
├── app/
│   └── app.py            # Streamlit Web界面
├── data/
│   └── ecoer_prices.db   # SQLite数据库
└── README.md
```

---

## 数据库表结构

- **products**: 产品主表 (品牌、型号、能力、能效等)
- **price_quotes**: 报价表 (价格、地区、来源、日期)
- **regions**: 地区表
- **categories**: 品类表
- **ecoer_mapping**: Ecoer对标表
- **file_uploads**: 文件上传记录

---

## 支持识别的品牌

Carrier, Trane, Lennox, Rheem, Goodman, Daikin, Mitsubishi, LG, Samsung, Fujitsu, Gree, Midea, York, American Standard, Bryant, Coleman, Ecoer

---

## 命令行使用

### 解析Excel文件
```
python scripts/parse_excel.py your_prices.xlsx
```

### 解析PDF文件
```
python scripts/parse_pdf.py your_prices.pdf
```
