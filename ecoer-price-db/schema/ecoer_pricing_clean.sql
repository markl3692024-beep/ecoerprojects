-- Ecoer 价格查询系统 - 干净的数据库结构
-- 只包含 Ecoer 产品，所有数据由管理员手动录入

-- ============================================
-- 1. 产品表 (Ecoer Products)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,                 -- SKU编码 (如: EODA19H-2436)
    model_number TEXT NOT NULL,               -- 完整型号
    product_name TEXT NOT NULL,               -- 产品名称
    category TEXT NOT NULL,                   -- 品类
    series TEXT,                              -- 系列
    description TEXT,                         -- 产品描述
    specs TEXT,                               -- 规格参数 (JSON格式)
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 客户表 (Customers)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,       -- 客户编码 (如: C001)
    customer_name TEXT NOT NULL,              -- 客户名称
    customer_type TEXT,                       -- 类型: Distributor, Contractor, Dealer
    region TEXT,                              -- 所在地区/州
    discount_tier TEXT DEFAULT 'Standard',    -- 折扣等级
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. 价格表 (Prices)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER,                      -- NULL = 标准价格
    list_price DECIMAL(10,2) NOT NULL,        -- 标价
    multiplier DECIMAL(5,4) DEFAULT 1.0,      -- 折扣系数
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

-- ============================================
-- 4. 散件表 (Components)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    component_sku TEXT NOT NULL,              -- 散件SKU
    component_name TEXT NOT NULL,             -- 散件名称
    component_type TEXT,                      -- 类型: Compressor, Motor, PCB, Coil, etc.
    list_price DECIMAL(10,2),                 -- 散件标价
    is_replacement BOOLEAN DEFAULT 0,         -- 是否可替换件
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id)
);

-- ============================================
-- 5. 用户表 (Users)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'sales_rep',            -- admin, sales_rep
    territory TEXT,                           -- 负责区域
    allowed_customers TEXT,                   -- JSON数组 [1,2,3]
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 初始数据 - 只有管理员账号
-- ============================================
INSERT OR IGNORE INTO ecoer_users (username, password, full_name, role, territory, allowed_customers) VALUES
('admin', 'admin123', 'Administrator', 'admin', 'All', '[]');
