-- Ecoer 价格查询系统 V3
-- 支持 List Price 版本管理 + 客户选择 List Price + 设置 Modifier

-- ============================================
-- 1. List Price 版本表 (价格表版本管理)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_price_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_list_code TEXT UNIQUE NOT NULL,   -- 版本编码: NE_REG, SE_REG, 2024Q1, etc.
    price_list_name TEXT NOT NULL,          -- 版本名称: Northeast Regular, Southeast, etc.
    description TEXT,                       -- 描述
    region TEXT,                            -- 适用区域
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT 1,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 产品表
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    model_number TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    series TEXT,
    sub_series TEXT,
    description TEXT,
    short_desc TEXT,
    specs TEXT,
    seer TEXT,
    eer TEXT,
    hspf TEXT,
    tons TEXT,
    btu TEXT,
    refrigerant TEXT,
    voltage TEXT,
    phase TEXT,
    compressor_type TEXT,
    motor_type TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. List Price 明细表 (每个版本的产品价格)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_list_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    price_list_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    list_price DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_list_id) REFERENCES ecoer_price_lists(id),
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id),
    UNIQUE(price_list_id, product_id)
);

-- ============================================
-- 4. 客户表 (绑定到特定 List Price)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    customer_type TEXT,
    region TEXT,
    discount_tier TEXT DEFAULT 'Standard',
    price_list_id INTEGER,                  -- 绑定的 List Price 版本
    default_modifier DECIMAL(5,4) DEFAULT 1.0,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (price_list_id) REFERENCES ecoer_price_lists(id)
);

-- ============================================
-- 5. 客户专属 Modifier 表 (产品级别的特殊系数)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_customer_product_modifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    modifier DECIMAL(5,4) NOT NULL,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (customer_id) REFERENCES ecoer_customers(id),
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id),
    UNIQUE(customer_id, product_id)
);

-- ============================================
-- 6. 散件表
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
-- 7. 用户表
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
