-- 价格查询系统数据库结构
-- 核心逻辑: Final Price = List Price × Multiplier

-- ============================================
-- 1. 客户表 (Customers)
-- ============================================
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,      -- 客户编码
    customer_name TEXT NOT NULL,              -- 客户名称
    customer_type TEXT,                       -- 客户类型: Distributor, Contractor, Dealer
    region_id INTEGER,                        -- 默认地区
    discount_tier TEXT DEFAULT 'Standard',    -- 折扣等级: Standard, Preferred, VIP
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- ============================================
-- 2. 产品主表 (Product Masters) - 管理员维护
-- ============================================
CREATE TABLE IF NOT EXISTS product_masters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,                 -- SKU/型号
    model_number TEXT,                        -- 型号
    product_name TEXT NOT NULL,               -- 产品名称
    category_id INTEGER,                      -- 品类
    description TEXT,                         -- 产品描述
    specs TEXT,                               -- 规格参数(JSON)
    -- 散件清单 (JSON数组)
    components TEXT,                          -- [{"sku":"xxx","name":"xxx","qty":1}]
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- ============================================
-- 3. 价格表 (List Prices) - 按地区+客户设置
-- ============================================
CREATE TABLE IF NOT EXISTS list_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_master_id INTEGER NOT NULL,
    region_id INTEGER,                        -- NULL = 全国通用
    customer_id INTEGER,                      -- NULL = 非特定客户(按地区)
    list_price DECIMAL(10,2) NOT NULL,        -- 标价
    currency TEXT DEFAULT 'USD',
    effective_date DATE DEFAULT CURRENT_DATE, -- 生效日期
    expiry_date DATE,                         -- 失效日期
    is_active BOOLEAN DEFAULT 1,
    created_by TEXT,                          -- 管理员账号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_master_id) REFERENCES product_masters(id),
    FOREIGN KEY (region_id) REFERENCES regions(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    UNIQUE(product_master_id, region_id, customer_id, effective_date)
);

-- ============================================
-- 4. 折扣系数表 (Multipliers) - 按客户+地区
-- ============================================
CREATE TABLE IF NOT EXISTS multipliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,                      -- NULL = 默认系数
    region_id INTEGER,                        -- NULL = 全国通用
    category_id INTEGER,                      -- NULL = 全品类通用
    multiplier DECIMAL(5,4) NOT NULL,         -- 折扣系数 (0.5 = 50%)
    multiplier_name TEXT,                     -- 系数名称
    effective_date DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT 1,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (region_id) REFERENCES regions(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- ============================================
-- 5. 散件价格表 (Component Prices)
-- ============================================
CREATE TABLE IF NOT EXISTS component_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_master_id INTEGER NOT NULL,       -- 所属产品
    component_sku TEXT NOT NULL,              -- 散件SKU
    component_name TEXT,                      -- 散件名称
    component_type TEXT,                      -- 类型: Motor, Compressor, Coil, etc.
    list_price DECIMAL(10,2),                 -- 散件标价
    cost_price DECIMAL(10,2),                 -- 成本价(管理员可见)
    is_replacement BOOLEAN DEFAULT 0,         -- 是否可替换件
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_master_id) REFERENCES product_masters(id)
);

-- ============================================
-- 6. 价格历史表 (Price History) - 审计追踪
-- ============================================
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,                 -- 修改的表
    record_id INTEGER NOT NULL,               -- 记录ID
    field_name TEXT,                          -- 修改的字段
    old_value TEXT,                           -- 旧值
    new_value TEXT,                           -- 新值
    changed_by TEXT,                          -- 修改人
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 7. 用户权限表 (User Permissions)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'viewer',               -- admin, editor, viewer
    password_hash TEXT,                       -- 简单密码保护
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 初始数据
-- ============================================

-- 默认管理员账号 (密码: admin123)
INSERT OR IGNORE INTO users (username, display_name, role, password_hash) 
VALUES ('admin', 'Administrator', 'admin', 'admin123');

-- 示例客户
INSERT OR IGNORE INTO customers (customer_code, customer_name, customer_type, discount_tier)
VALUES 
    ('C001', 'Johnstone Supply', 'Distributor', 'Preferred'),
    ('C002', 'Green Earth', 'Distributor', 'Standard'),
    ('C003', 'James Wu HVAC', 'Contractor', 'VIP');

-- 示例折扣系数
INSERT OR IGNORE INTO multipliers (customer_id, region_id, category_id, multiplier, multiplier_name)
VALUES 
    (NULL, NULL, NULL, 1.0, 'Standard'),
    (1, NULL, NULL, 0.85, 'Johnstone Preferred'),
    (2, NULL, NULL, 0.90, 'Green Earth Standard'),
    (3, NULL, NULL, 0.75, 'James Wu VIP');
