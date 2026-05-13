-- =====================================================
-- Ecoer Price Intelligence Database Schema
-- 空调设备竞品价格数据库
-- =====================================================

-- 地区表
CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- 地区名称 (如: Los Angeles, New York)
    state TEXT NOT NULL,          -- 州 (如: CA, NY, TX)
    zone TEXT,                    -- 气候区 (如: Hot-Humid, Mixed-Humid)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 品类表
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,    -- 品类名称
    description TEXT,             -- 描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 产品主表
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,                  -- 品牌 (Carrier, Trane, Lennox, etc.)
    model_number TEXT NOT NULL,           -- 型号
    category_id INTEGER,                  -- 品类ID
    capacity_btuh INTEGER,                -- 能力 BTU/h
    capacity_tons REAL,                   -- 能力 吨
    efficiency_seer REAL,                 -- SEER能效
    efficiency_eer REAL,                  -- EER能效
    efficiency_hspf REAL,                 -- HSPF制热能效
    compressor_type TEXT,                 -- 压缩机类型 (Scroll, Rotary, Twin-Rotary, etc.)
    motor_type TEXT,                      -- 电机类型 (PSC, ECM, VS, etc.)
    refrigerant TEXT,                     -- 制冷剂 (R-410A, R-32, etc.)
    voltage TEXT,                         -- 电压 (208V, 230V, 460V, etc.)
    phase TEXT,                           -- 相数 (Single, Three)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(brand, model_number)
);

-- 报价表
CREATE TABLE IF NOT EXISTS price_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,          -- 产品ID
    region_id INTEGER,                    -- 地区ID
    price REAL NOT NULL,                  -- 价格
    currency TEXT DEFAULT 'USD',          -- 货币
    unit TEXT DEFAULT 'Each',              -- 单位 (Each, System, Ton, etc.)
    source_name TEXT,                     -- 来源名称 (Distributor name, etc.)
    source_type TEXT,                     -- 来源类型 (Distributor, Dealer, Online, Manufacturer)
    quote_date DATE,                      -- 报价日期
    effective_date DATE,                  -- 生效日期
    expiration_date DATE,                -- 过期日期
    is_promotional INTEGER DEFAULT 0,    -- 是否促销价
    is_map_price INTEGER DEFAULT 0,       -- 是否MAP价
    notes TEXT,                           -- 备注
    raw_data TEXT,                        -- 原始数据(JSON格式保存)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- Ecoer对标表
CREATE TABLE IF NOT EXISTS ecoer_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_product_id INTEGER,       -- 竞品ID
    ecoer_model TEXT NOT NULL,            -- Ecoer对应型号
    ecoer_price REAL,                     -- Ecoer建议价
    ecoer_msrp REAL,                      -- Ecoer MSRP
    positioning TEXT,                     -- 市场定位 (Premium, Mid-Range, Budget)
    price_gap_pct REAL,                   -- 价格差异百分比
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (competitor_product_id) REFERENCES products(id)
);

-- 文件上传记录表
CREATE TABLE IF NOT EXISTS file_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT,                       -- excel, pdf, image
    file_size INTEGER,                    -- 文件大小(bytes)
    record_count INTEGER,                 -- 提取的记录数
    status TEXT DEFAULT 'pending',        -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_capacity ON products(capacity_btuh);
CREATE INDEX IF NOT EXISTS idx_price_quotes_product ON price_quotes(product_id);
CREATE INDEX IF NOT EXISTS idx_price_quotes_region ON price_quotes(region_id);
CREATE INDEX IF NOT EXISTS idx_price_quotes_date ON price_quotes(quote_date);

-- 预置品类数据
INSERT OR IGNORE INTO categories (name, description) VALUES 
    ('Mini Split', '分体式小空调'),
    ('Central AC', '中央空调'),
    ('Heat Pump', '热泵'),
    ('PTAC', '窗机空调'),
    ('Commercial Package', '商用整机'),
    ('Geothermal', '地源热泵'),
    ('Gas Furnace', '燃气炉'),
    ('Air Handler', '空气处理机'),
    ('Condenser', '冷凝器'),
    ('Evaporator Coil', '蒸发器线圈');
