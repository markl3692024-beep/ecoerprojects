-- Ecoer 价格查询系统 V2
-- 增强版：支持详细产品参数、搜索联想、灵活的价格逻辑

-- ============================================
-- 1. 产品表 (Ecoer Products) - 增强版
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,                 -- SKU编码
    model_number TEXT NOT NULL,               -- 完整型号
    product_name TEXT NOT NULL,               -- 产品名称
    category TEXT NOT NULL,                   -- 品类: Condenser, Air Handler, Heat Kit, Thermostat, Package Unit
    series TEXT,                              -- 系列: TDI Pro, EODA, EOA, etc.
    sub_series TEXT,                          -- 子系列
    description TEXT,                         -- 产品描述
    short_desc TEXT,                          -- 简短描述（搜索显示用）
    specs TEXT,                               -- 规格参数 (JSON格式)
    -- 关键参数字段（用于筛选和搜索）
    seer TEXT,                                -- SEER值
    eer TEXT,                                 -- EER值
    hspf TEXT,                                -- HSPF值
    tons TEXT,                                -- 吨数/容量
    btu TEXT,                                 -- BTU
    refrigerant TEXT,                         -- 制冷剂
    voltage TEXT,                             -- 电压
    phase TEXT,                               -- 相数
    compressor_type TEXT,                     -- 压缩机类型
    motor_type TEXT,                          -- 电机类型
    -- 状态
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 搜索索引
CREATE INDEX IF NOT EXISTS idx_products_sku ON ecoer_products(sku);
CREATE INDEX IF NOT EXISTS idx_products_model ON ecoer_products(model_number);
CREATE INDEX IF NOT EXISTS idx_products_series ON ecoer_products(series);
CREATE INDEX IF NOT EXISTS idx_products_category ON ecoer_products(category);

-- ============================================
-- 2. 客户表 (Customers)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,       -- 客户编码
    customer_name TEXT NOT NULL,              -- 客户名称
    customer_type TEXT,                       -- Distributor, Contractor, Dealer
    region TEXT,                              -- 所在地区
    discount_tier TEXT DEFAULT 'Standard',    -- 折扣等级
    default_multiplier DECIMAL(5,4) DEFAULT 1.0,  -- 客户默认系数
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. 价格表 (Prices) - 支持多种价格逻辑
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER,                      -- NULL = 标准价格（所有客户）
    -- 价格构成
    list_price DECIMAL(10,2) NOT NULL,        -- (a) List Price 原价
    modifier DECIMAL(5,4) DEFAULT 1.0,        -- (b) Modifier 系数
    sales_price DECIMAL(10,2),                -- (c) Sales Price = List Price × Modifier
    -- 价格类型
    price_type TEXT DEFAULT 'standard',       -- standard, customer_specific, promotional
    currency TEXT DEFAULT 'USD',
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id),
    FOREIGN KEY (customer_id) REFERENCES ecoer_customers(id)
);

-- 价格索引
CREATE INDEX IF NOT EXISTS idx_prices_product ON ecoer_prices(product_id);
CREATE INDEX IF NOT EXISTS idx_prices_customer ON ecoer_prices(customer_id);

-- ============================================
-- 4. 产品-客户专属系数表 (灵活设置)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_product_customer_modifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    modifier DECIMAL(5,4) NOT NULL,           -- 专属系数
    list_price_override DECIMAL(10,2),        -- 可选: 专属List Price
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id),
    FOREIGN KEY (customer_id) REFERENCES ecoer_customers(id),
    UNIQUE(product_id, customer_id)
);

-- ============================================
-- 5. 散件表 (Components)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    component_sku TEXT NOT NULL,
    component_name TEXT NOT NULL,
    component_type TEXT,
    list_price DECIMAL(10,2),
    modifier DECIMAL(5,4) DEFAULT 1.0,
    is_replacement BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id)
);

-- ============================================
-- 6. 用户表 (Users)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'sales_rep',
    territory TEXT,
    allowed_customers TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 初始数据
-- ============================================
INSERT OR IGNORE INTO ecoer_users (username, password, full_name, role, territory, allowed_customers) VALUES
('admin', 'admin123', 'Administrator', 'admin', 'All', '[]');
