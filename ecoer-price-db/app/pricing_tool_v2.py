"""
价格查询工具 V2 - 多层级权限控制
不同 Sales Rep 登录后只能看到授权的客户/地区价格
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import json
import hashlib
import time

DB_PATH = Path(__file__).parent.parent / 'data' / 'ecoer_prices.db'


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()[:20]


def login_user(username, password):
    """用户登录验证 - 支持 admin 和 sales_rep"""
    conn = get_connection()
    cur = conn.cursor()
    
    # 先检查 admin
    cur.execute("SELECT id, role FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
               (username, password))
    admin = cur.fetchone()
    if admin:
        conn.close()
        return {'type': 'admin', 'id': admin[0], 'name': username, 'role': admin[1]}
    
    # 再检查 sales_rep
    cur.execute("SELECT id, full_name, territory FROM sales_reps WHERE username = ? AND password_hash = ? AND is_active = 1",
               (username, password))
    rep = cur.fetchone()
    if rep:
        conn.close()
        return {'type': 'sales_rep', 'id': rep[0], 'name': rep[1], 'territory': rep[2]}
    
    conn.close()
    return None


def get_rep_customers(rep_id):
    """获取销售代表授权的客户列表"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT c.id, c.customer_code, c.customer_name, c.discount_tier
        FROM rep_customer_access rca
        JOIN customers c ON rca.customer_id = c.id
        WHERE rca.sales_rep_id = ? AND c.is_active = 1
        ORDER BY c.customer_name
    """, conn, params=(rep_id,))
    conn.close()
    return df


def get_rep_regions(rep_id):
    """获取销售代表授权的地区列表"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT DISTINCT r.id, r.state, r.name
        FROM rep_region_access rra
        JOIN regions r ON rra.region_id = r.id
        WHERE rra.sales_rep_id = ?
        ORDER BY r.state
    """, conn, params=(rep_id,))
    conn.close()
    return df


def get_accessible_customers(user):
    """根据用户类型返回可访问的客户"""
    if user['type'] == 'admin':
        conn = get_connection()
        df = pd.read_sql_query("SELECT id, customer_code, customer_name, discount_tier FROM customers WHERE is_active = 1 ORDER BY customer_name", conn)
        conn.close()
        return df
    else:
        return get_rep_customers(user['id'])


def get_accessible_regions(user):
    """根据用户类型返回可访问的地区"""
    if user['type'] == 'admin':
        conn = get_connection()
        df = pd.read_sql_query("SELECT DISTINCT id, state, name FROM regions ORDER BY state", conn)
        conn.close()
        return df
    else:
        return get_rep_regions(user['id'])


def search_products(search_term, user, region_id=None, customer_id=None):
    """搜索产品 - 带权限过滤"""
    conn = get_connection()
    
    # 基础查询
    query = """
        SELECT DISTINCT pm.id, pm.sku, pm.model_number, pm.product_name,
               c.name as category, pm.description, pm.specs, pm.components
        FROM product_masters pm
        LEFT JOIN categories c ON pm.category_id = c.id
        WHERE pm.is_active = 1
    """
    params = []
    
    if search_term:
        query += " AND (pm.sku LIKE ? OR pm.model_number LIKE ? OR pm.product_name LIKE ?)"
        params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_authorized_price(product_master_id, user, region_id=None, customer_id=None):
    """
    获取授权价格 - 带权限验证
    优先级: 客户+地区 > 客户 > 地区 > 通用
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # 检查用户是否有权访问该客户/地区
    if user['type'] == 'sales_rep':
        if customer_id:
            cur.execute("SELECT 1 FROM rep_customer_access WHERE sales_rep_id = ? AND customer_id = ?",
                       (user['id'], customer_id))
            if not cur.fetchone():
                conn.close()
                return None, None, "无权访问该客户"
        
        if region_id:
            cur.execute("SELECT 1 FROM rep_region_access WHERE sales_rep_id = ? AND region_id = ?",
                       (user['id'], region_id))
            if not cur.fetchone():
                conn.close()
                return None, None, "无权访问该地区"
    
    # 查找 List Price (带优先级)
    list_price = None
    price_source = ""
    
    # 优先级1: 客户+地区
    if customer_id and region_id:
        cur.execute("""
            SELECT list_price FROM list_prices
            WHERE product_master_id = ? AND customer_id = ? AND region_id = ?
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_master_id, customer_id, region_id))
        row = cur.fetchone()
        if row:
            list_price = row[0]
            price_source = "客户专属价格"
    
    # 优先级2: 客户
    if list_price is None and customer_id:
        cur.execute("""
            SELECT list_price FROM list_prices
            WHERE product_master_id = ? AND customer_id = ? AND region_id IS NULL
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_master_id, customer_id))
        row = cur.fetchone()
        if row:
            list_price = row[0]
            price_source = "客户通用价格"
    
    # 优先级3: 地区
    if list_price is None and region_id:
        cur.execute("""
            SELECT list_price FROM list_prices
            WHERE product_master_id = ? AND region_id = ? AND customer_id IS NULL
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_master_id, region_id))
        row = cur.fetchone()
        if row:
            list_price = row[0]
            price_source = "地区价格"
    
    # 优先级4: 通用
    if list_price is None:
        cur.execute("""
            SELECT list_price FROM list_prices
            WHERE product_master_id = ? AND region_id IS NULL AND customer_id IS NULL
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_master_id,))
        row = cur.fetchone()
        if row:
            list_price = row[0]
            price_source = "标准价格"
    
    # 获取 Multiplier
    multiplier = get_authorized_multiplier(cur, user, customer_id, region_id)
    
    conn.close()
    return list_price, multiplier, price_source


def get_authorized_multiplier(cur, user, customer_id=None, region_id=None):
    """获取授权折扣系数"""
    conditions = [
        ("customer_id = ? AND region_id = ?", (customer_id, region_id)),
        ("customer_id = ? AND region_id IS NULL", (customer_id,)),
        ("customer_id IS NULL AND region_id = ?", (region_id,)),
        ("customer_id IS NULL AND region_id IS NULL", ()),
    ]
    
    for condition, params in conditions:
        cur.execute(f"""
            SELECT multiplier FROM multipliers
            WHERE {condition}
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, params)
        row = cur.fetchone()
        if row:
            return row[0]
    
    return 1.0


def get_component_prices(product_master_id, multiplier=1.0):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT component_sku, component_name, component_type, list_price
        FROM component_prices
        WHERE product_master_id = ?
        ORDER BY component_type, component_name
    """, conn, params=(product_master_id,))
    conn.close()
    if not df.empty:
        df['最终价格'] = df['list_price'] * multiplier
    return df


def render_login_page():
    """登录页面"""
    st.title("🔐 Ecoer 价格查询系统")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("用户登录")
        
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            
            col_a, col_b = st.columns(2)
            with col_a:
                submitted = st.form_submit_button("登录", use_container_width=True)
            with col_b:
                demo = st.form_submit_button("演示账号", use_container_width=True)
        
        if submitted and username and password:
            user = login_user(username, password)
            if user:
                st.session_state['user'] = user
                st.success(f"欢迎, {user['name']}! ({user['type']})")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("用户名或密码错误")
        
        if demo:
            st.info("""
            **演示账号:**
            - 管理员: `admin` / `admin123`
            - NY销售: `rep_ny` / `rep123`
            - CA销售: `rep_ca` / `rep123`
            - MA销售: `rep_ma` / `rep123`
            """)


def render_pricing_tool_v2():
    """主价格查询界面"""
    
    # 检查登录状态
    if 'user' not in st.session_state:
        render_login_page()
        return
    
    user = st.session_state['user']
    
    # 顶部栏
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(f"**👤 {user['name']}** ({user['type']})")
    with col2:
        if user['type'] == 'sales_rep':
            st.markdown(f"**🌍 负责区域:** {user.get('territory', 'N/A')}")
    with col3:
        if st.button("退出登录", use_container_width=True):
            del st.session_state['user']
            st.rerun()
    
    st.markdown("---")
    st.header("🔍 价格查询")
    st.markdown("**公式**: `最终价格 = List Price × Multiplier`")
    
    # 获取用户可访问的数据
    accessible_customers = get_accessible_customers(user)
    accessible_regions = get_accessible_regions(user)
    
    # ========== 查询条件 ==========
    st.subheader("筛选条件")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not accessible_regions.empty:
            region_options = {f"{r['state']} - {r['name']}": r['id'] for _, r in accessible_regions.iterrows()}
            region_options["全部地区"] = None
            selected_region_label = st.selectbox("选择地区", list(region_options.keys()))
            region_id = region_options[selected_region_label]
        else:
            st.warning("无权访问任何地区")
            region_id = None
    
    with col2:
        if not accessible_customers.empty:
            customer_options = {f"{r['customer_code']} - {r['customer_name']} ({r['discount_tier']})": r['id'] 
                              for _, r in accessible_customers.iterrows()}
            customer_options["默认客户"] = None
            selected_customer_label = st.selectbox("选择客户", list(customer_options.keys()))
            customer_id = customer_options[selected_customer_label]
        else:
            st.warning("无权访问任何客户")
            customer_id = None
    
    with col3:
        search_term = st.text_input("输入型号/SKU", placeholder="如: EODA19H")
    
    # ========== 查询结果 ==========
    if search_term:
        products = search_products(search_term, user, region_id, customer_id)
        
        if products.empty:
            st.warning(f"未找到匹配 '{search_term}' 的产品")
            return
        
        st.subheader(f"📦 查询结果 ({len(products)} 个产品)")
        
        for _, product in products.iterrows():
            with st.container():
                st.markdown("---")
                
                # 获取授权价格
                list_price, multiplier, price_source = get_authorized_price(
                    product['id'], user, region_id, customer_id
                )
                
                col_info, col_price = st.columns([2, 1])
                
                with col_info:
                    st.markdown(f"**{product['product_name']}**")
                    st.markdown(f"SKU: `{product['sku']}` | 型号: `{product['model_number']}`")
                    st.markdown(f"品类: {product['category']}")
                    if product['description']:
                        st.markdown(f"描述: {product['description']}")
                
                with col_price:
                    if list_price:
                        final_price = list_price * multiplier
                        
                        # 价格卡片
                        st.metric("List Price", f"${list_price:,.2f}")
                        st.caption(f"来源: {price_source}")
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            st.metric("Multiplier", f"{multiplier:.2%}")
                        with col_m2:
                            discount = (1 - multiplier) * 100
                            st.metric("最终价格", f"${final_price:,.2f}", 
                                    delta=f"-{discount:.0f}%" if discount > 0 else None)
                    else:
                        st.error("暂无价格数据")
                        if user['type'] == 'admin':
                            if st.button("设置价格", key=f"set_{product['id']}"):
                                st.session_state['set_price_product'] = product['id']
                                st.rerun()
                
                # 规格参数
                if product['specs']:
                    try:
                        specs = json.loads(product['specs'])
                        with st.expander("📋 规格参数"):
                            spec_cols = st.columns(len(specs))
                            for i, (k, v) in enumerate(specs.items()):
                                with spec_cols[i % len(spec_cols)]:
                                    st.metric(k, str(v))
                    except:
                        st.markdown(f"规格: {product['specs']}")
                
                # 散件价格
                components = get_component_prices(product['id'], multiplier)
                if not components.empty:
                    with st.expander("🔩 散件清单"):
                        st.dataframe(
                            components[['component_sku', 'component_name', 'component_type', 'list_price', '最终价格']],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                'list_price': st.column_config.NumberColumn('List Price', format='$%.2f'),
                                '最终价格': st.column_config.NumberColumn('最终价格', format='$%.2f')
                            }
                        )
    else:
        # 显示可访问的数据概览
        st.info("👆 请输入型号或选择筛选条件开始查询")
        
        # 显示权限概览
        with st.expander("📋 您的访问权限"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**可访问客户:**")
                if not accessible_customers.empty:
                    for _, c in accessible_customers.iterrows():
                        st.markdown(f"- {c['customer_name']} ({c['customer_code']}) - {c['discount_tier']}")
                else:
                    st.markdown("- 无")
            
            with col2:
                st.markdown("**可访问地区:**")
                if not accessible_regions.empty:
                    seen = set()
                    for _, r in accessible_regions.iterrows():
                        key = f"{r['state']} - {r['name']}"
                        if key not in seen:
                            st.markdown(f"- {key}")
                            seen.add(key)
                else:
                    st.markdown("- 无")
    
    # ========== 管理员面板 ==========
    if user['type'] == 'admin':
        render_admin_panel()


def render_admin_panel():
    """管理员面板 - 权限管理"""
    st.markdown("---")
    st.header("⚙️ 管理员面板")
    
    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
        "👥 销售代表管理", "🏷️ 客户权限", "🌍 地区权限", "💰 价格管理", "📊 系统状态"
    ])
    
    with admin_tab1:
        st.subheader("销售代表列表")
        conn = get_connection()
        reps = pd.read_sql_query("SELECT * FROM sales_reps", conn)
        st.dataframe(reps, use_container_width=True)
        conn.close()
    
    with admin_tab2:
        st.subheader("客户权限分配")
        conn = get_connection()
        access = pd.read_sql_query("""
            SELECT sr.username, sr.full_name, c.customer_code, c.customer_name, rca.access_level
            FROM rep_customer_access rca
            JOIN sales_reps sr ON rca.sales_rep_id = sr.id
            JOIN customers c ON rca.customer_id = c.id
        """, conn)
        st.dataframe(access, use_container_width=True)
        conn.close()
    
    with admin_tab3:
        st.subheader("地区权限分配")
        conn = get_connection()
        access = pd.read_sql_query("""
            SELECT sr.username, sr.full_name, r.state, r.name, rra.access_level
            FROM rep_region_access rra
            JOIN sales_reps sr ON rra.sales_rep_id = sr.id
            JOIN regions r ON rra.region_id = r.id
        """, conn)
        st.dataframe(access, use_container_width=True)
        conn.close()
    
    with admin_tab4:
        st.subheader("价格数据")
        conn = get_connection()
        prices = pd.read_sql_query("""
            SELECT pm.sku, pm.product_name, lp.list_price, r.state, c.customer_name, lp.effective_date
            FROM list_prices lp
            JOIN product_masters pm ON lp.product_master_id = pm.id
            LEFT JOIN regions r ON lp.region_id = r.id
            LEFT JOIN customers c ON lp.customer_id = c.id
            ORDER BY pm.sku
        """, conn)
        st.dataframe(prices, use_container_width=True)
        conn.close()
    
    with admin_tab5:
        st.subheader("系统状态")
        conn = get_connection()
        
        stats = pd.read_sql_query("""
            SELECT '产品' as item, COUNT(*) as count FROM product_masters WHERE is_active = 1
            UNION ALL SELECT '客户', COUNT(*) FROM customers WHERE is_active = 1
            UNION ALL SELECT '销售代表', COUNT(*) FROM sales_reps WHERE is_active = 1
            UNION ALL SELECT '价格记录', COUNT(*) FROM list_prices WHERE is_active = 1
            UNION ALL SELECT '散件', COUNT(*) FROM component_prices
        """, conn)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        for i, (_, row) in enumerate(stats.iterrows()):
            cols = [col1, col2, col3, col4, col5]
            cols[i].metric(row['item'], row['count'])
        
        conn.close()


if __name__ == "__main__":
    render_pricing_tool_v2()
