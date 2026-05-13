-- Ecoer 价格查询系统 (独立数据库)
-- 专门用于 Ecoer 产品价格管理，与竞品分析完全独立

-- ============================================
-- 1. 产品表 (Ecoer Products)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,                 -- SKU编码
    model_number TEXT NOT NULL,               -- 型号
    product_name TEXT NOT NULL,               -- 产品名称
    category TEXT NOT NULL,                   -- 品类: Condenser, Air Handler, Heat Kit, Thermostat
    series TEXT,                              -- 系列
    description TEXT,                         -- 产品描述
    specs TEXT,                               -- 规格参数 (JSON)
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 客户表 (Customers)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code TEXT UNIQUE NOT NULL,       -- 客户编码
    customer_name TEXT NOT NULL,              -- 客户名称
    customer_type TEXT,                       -- 类型: Distributor, Contractor, Dealer
    region TEXT,                              -- 所在地区
    discount_tier TEXT DEFAULT 'Standard',    -- 折扣等级
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 3. 价格表 (Prices) - List Price + Multiplier
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER,                      -- NULL = 通用价格
    list_price DECIMAL(10,2) NOT NULL,        -- 标价
    multiplier DECIMAL(5,4) DEFAULT 1.0,      -- 折扣系数
    final_price DECIMAL(10,2),                -- 最终价格 (可计算，也可存储)
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
    component_type TEXT,                      -- 类型
    list_price DECIMAL(10,2),                 -- 散件标价
    is_replacement BOOLEAN DEFAULT 0,         -- 是否可替换
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES ecoer_products(id)
);

-- ============================================
-- 5. 用户表 (Users)
-- ============================================
CREATE TABLE IF NOT EXISTS ecoer_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,                   -- 明文密码(演示用)
    full_name TEXT,
    role TEXT DEFAULT 'sales_rep',            -- admin, sales_rep
    territory TEXT,                           -- 负责区域
    allowed_customers TEXT,                   -- 授权客户ID列表 (JSON数组)
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 初始数据 - Ecoer 产品
-- ============================================
INSERT OR IGNORE INTO ecoer_products (sku, model_number, product_name, category, series, description, specs) VALUES
('EODA19H-2436', 'EODA19H-2436ABA', 'Ecoer 19 SEER Heat Pump Condenser', 'Condenser', 'EODA', 
 '19 SEER Variable Speed Heat Pump Condenser, 2-3 tons, R-454B',
 '{"SEER": 19, "HSPF": 10, "Tons": "2-3", "Refrigerant": "R-454B", "Compressor": "Variable Speed", "Voltage": "208/230V"}'),

('EAHDEN-36', 'EAHDEN-36ABA', 'Ecoer Communicating Air Handler', 'Air Handler', 'EAHDEN',
 'Communicating Air Handler for Ecoer Heat Pump, 3 tons, ECM Motor',
 '{"Tons": 3, "Motor": "ECM", "Voltage": "208/230V", "Communication": "Ecoer Protocol"}'),

('EHK10B', 'EHK10B', 'Ecoer 10kW Electric Heat Kit', 'Heat Kit', 'EHK',
 '10kW Electric Heat Kit for Air Handler, Single Phase',
 '{"kW": 10, "Voltage": "240V", "Phase": "Single", "Stages": 1}'),

('EST02', 'EST02', 'Ecoer Smart Thermostat', 'Thermostat', 'EST',
 'Wi-Fi Smart Thermostat with Ecoer Communicating Protocol, Touch Screen',
 '{"Connectivity": "Wi-Fi", "Protocol": "Ecoer Comm", "Display": "Touch", "App": "Ecoer Control"}');

-- ============================================
-- 初始数据 - 客户
-- ============================================
INSERT OR IGNORE INTO ecoer_customers (customer_code, customer_name, customer_type, region, discount_tier) VALUES
('C001', 'Johnstone Supply', 'Distributor', 'NY', 'Preferred'),
('C002', 'Green Earth', 'Distributor', 'CA', 'Standard'),
('C003', 'James Wu HVAC', 'Contractor', 'MA', 'VIP'),
('C004', 'ABC Supply', 'Distributor', 'TX', 'Standard');

-- ============================================
-- 初始数据 - 价格 (不同客户不同价格)
-- ============================================
-- EODA19H-2436 价格
INSERT OR IGNORE INTO ecoer_prices (product_id, customer_id, list_price, multiplier, effective_date) VALUES
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), NULL, 4500.00, 1.00, '2025-01-01'),  -- 标准价格
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 1, 4500.00, 0.85, '2025-01-01'),    -- Johnstone 85折
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 2, 4500.00, 0.90, '2025-01-01'),    -- Green Earth 9折
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 3, 4500.00, 0.75, '2025-01-01');    -- James Wu 75折

-- EAHDEN-36 价格
INSERT OR IGNORE INTO ecoer_prices (product_id, customer_id, list_price, multiplier, effective_date) VALUES
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), NULL, 2800.00, 1.00, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), 1, 2800.00, 0.85, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), 2, 2800.00, 0.90, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), 3, 2800.00, 0.75, '2025-01-01');

-- EHK10B 价格
INSERT OR IGNORE INTO ecoer_prices (product_id, customer_id, list_price, multiplier, effective_date) VALUES
((SELECT id FROM ecoer_products WHERE sku='EHK10B'), NULL, 350.00, 1.00, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EHK10B'), 1, 350.00, 0.85, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EHK10B'), 2, 350.00, 0.90, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EHK10B'), 3, 350.00, 0.75, '2025-01-01');

-- EST02 价格
INSERT OR IGNORE INTO ecoer_prices (product_id, customer_id, list_price, multiplier, effective_date) VALUES
((SELECT id FROM ecoer_products WHERE sku='EST02'), NULL, 450.00, 1.00, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EST02'), 1, 450.00, 0.85, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EST02'), 2, 450.00, 0.90, '2025-01-01'),
((SELECT id FROM ecoer_products WHERE sku='EST02'), 3, 450.00, 0.75, '2025-01-01');

-- ============================================
-- 初始数据 - 散件
-- ============================================
INSERT OR IGNORE INTO ecoer_components (product_id, component_sku, component_name, component_type, list_price) VALUES
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 'COMP-19H', 'Variable Speed Compressor', 'Compressor', 1200.00),
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 'PCB-19H', 'Main Control Board', 'Electronics', 350.00),
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 'FAN-19H', 'Condenser Fan Motor', 'Motor', 280.00),
((SELECT id FROM ecoer_products WHERE sku='EODA19H-2436'), 'COIL-19H', 'Condenser Coil', 'Coil', 450.00),
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), 'MTR-36', 'ECM Blower Motor', 'Motor', 380.00),
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), 'PCB-36', 'Air Handler Control Board', 'Electronics', 280.00),
((SELECT id FROM ecoer_products WHERE sku='EAHDEN-36'), 'HEATER-36', 'Electric Heat Strip', 'Heating', 220.00);

-- ============================================
-- 初始数据 - 用户
-- ============================================
INSERT OR IGNORE INTO ecoer_users (username, password, full_name, role, territory, allowed_customers) VALUES
('admin', 'admin123', 'Administrator', 'admin', 'All', '[1,2,3,4]'),
('rep_ny', 'rep123', 'Mike Johnson', 'sales_rep', 'NY,NJ,CT', '[1]'),
('rep_ca', 'rep123', 'Sarah Lee', 'sales_rep', 'CA,NV,AZ', '[2]'),
('rep_ma', 'rep123', 'David Chen', 'sales_rep', 'MA,RI,VT,NH', '[3]'),
('rep_tx', 'rep123', 'Robert Wilson', 'sales_rep', 'TX,OK,LA', '[4]');
