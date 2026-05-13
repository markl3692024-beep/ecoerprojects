-- 价格查询系统 V2 - 多层级权限控制
-- 核心: 不同 Sales Rep 看到不同客户/地区的价格

-- ============================================
-- 1. 销售代表表 (Sales Reps)
-- ============================================
CREATE TABLE IF NOT EXISTS sales_reps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,            -- 登录账号
    password_hash TEXT NOT NULL,              -- 密码 (简单明文，生产环境需加密)
    full_name TEXT NOT NULL,                  -- 姓名
    email TEXT,
    phone TEXT,
    territory TEXT,                           -- 负责区域 (如: "NY,NJ,CT" 或 "West Coast")
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 2. 客户权限关联表 (Rep-Customer Access)
-- ============================================
CREATE TABLE IF NOT EXISTS rep_customer_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_rep_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    access_level TEXT DEFAULT 'read',         -- read, write, admin
    granted_by TEXT,                          -- 授权人
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sales_rep_id, customer_id),
    FOREIGN KEY (sales_rep_id) REFERENCES sales_reps(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- ============================================
-- 3. 地区权限关联表 (Rep-Region Access)
-- ============================================
CREATE TABLE IF NOT EXISTS rep_region_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sales_rep_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    access_level TEXT DEFAULT 'read',
    granted_by TEXT,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sales_rep_id, region_id),
    FOREIGN KEY (sales_rep_id) REFERENCES sales_reps(id),
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- ============================================
-- 4. 价格可见性表 (Price Visibility)
-- ============================================
CREATE TABLE IF NOT EXISTS price_visibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_price_id INTEGER NOT NULL,
    visible_to_rep_id INTEGER,                -- NULL = 所有有权限的rep可见
    visible_to_customer_id INTEGER,           -- NULL = 所有客户可见
    is_restricted BOOLEAN DEFAULT 0,          -- 1 = 仅限特定人员查看
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (list_price_id) REFERENCES list_prices(id),
    FOREIGN KEY (visible_to_rep_id) REFERENCES sales_reps(id),
    FOREIGN KEY (visible_to_customer_id) REFERENCES customers(id)
);

-- ============================================
-- 5. 登录会话表 (Sessions)
-- ============================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_type TEXT NOT NULL,                  -- 'admin', 'sales_rep'
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 初始数据 - 销售代表
-- ============================================
INSERT OR IGNORE INTO sales_reps (username, password_hash, full_name, territory) VALUES
    ('rep_ny', 'rep123', 'Mike Johnson', 'NY,NJ,CT'),
    ('rep_ca', 'rep123', 'Sarah Lee', 'CA,NV,AZ'),
    ('rep_ma', 'rep123', 'David Chen', 'MA,RI,VT,NH');

-- ============================================
-- 初始数据 - 客户权限分配
-- ============================================
-- rep_ny 可以访问 Johnstone (NY客户)
INSERT OR IGNORE INTO rep_customer_access (sales_rep_id, customer_id, granted_by)
SELECT sr.id, c.id, 'admin'
FROM sales_reps sr, customers c
WHERE sr.username = 'rep_ny' AND c.customer_code = 'C001';

-- rep_ca 可以访问 Green Earth (CA客户)
INSERT OR IGNORE INTO rep_customer_access (sales_rep_id, customer_id, granted_by)
SELECT sr.id, c.id, 'admin'
FROM sales_reps sr, customers c
WHERE sr.username = 'rep_ca' AND c.customer_code = 'C002';

-- rep_ma 可以访问 James Wu (MA客户)
INSERT OR IGNORE INTO rep_customer_access (sales_rep_id, customer_id, granted_by)
SELECT sr.id, c.id, 'admin'
FROM sales_reps sr, customers c
WHERE sr.username = 'rep_ma' AND c.customer_code = 'C003';

-- ============================================
-- 初始数据 - 地区权限分配
-- ============================================
-- rep_ny 可以访问 NY 地区
INSERT OR IGNORE INTO rep_region_access (sales_rep_id, region_id, granted_by)
SELECT sr.id, r.id, 'admin'
FROM sales_reps sr, regions r
WHERE sr.username = 'rep_ny' AND r.state = 'NY';

-- rep_ca 可以访问 CA 地区
INSERT OR IGNORE INTO rep_region_access (sales_rep_id, region_id, granted_by)
SELECT sr.id, r.id, 'admin'
FROM sales_reps sr, regions r
WHERE sr.username = 'rep_ca' AND r.state = 'CA';

-- rep_ma 可以访问 MA 地区
INSERT OR IGNORE INTO rep_region_access (sales_rep_id, region_id, granted_by)
SELECT sr.id, r.id, 'admin'
FROM sales_reps sr, regions r
WHERE sr.username = 'rep_ma' AND r.state = 'MA';
