"""
Ecoer 价格查询系统 - 独立工具
所有 Ecoer 产品、客户、价格数据由管理员手动录入
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import json
import time

DB_PATH = Path(__file__).parent.parent / 'data' / 'ecoer_pricing.db'


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def login_user(username, password):
    """用户登录验证"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, territory, allowed_customers FROM ecoer_users WHERE username = ? AND password = ? AND is_active = 1",
               (username, password))
    user = cur.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'username': user[1],
            'name': user[2],
            'role': user[3],
            'territory': user[4],
            'allowed_customers': json.loads(user[5]) if user[5] else []
        }
    return None


def get_allowed_customers(user):
    """获取用户可访问的客户"""
    conn = get_connection()
    if user['role'] == 'admin':
        df = pd.read_sql_query("SELECT id, customer_code, customer_name, discount_tier FROM ecoer_customers WHERE is_active = 1 ORDER BY customer_name", conn)
    else:
        if not user['allowed_customers']:
            conn.close()
            return pd.DataFrame()
        placeholders = ','.join('?' * len(user['allowed_customers']))
        df = pd.read_sql_query(
            f"SELECT id, customer_code, customer_name, discount_tier FROM ecoer_customers WHERE id IN ({placeholders}) AND is_active = 1 ORDER BY customer_name",
            conn, params=user['allowed_customers']
        )
    conn.close()
    return df


def search_products(search_term=None, category=None):
    """搜索 Ecoer 产品"""
    conn = get_connection()
    query = "SELECT * FROM ecoer_products WHERE is_active = 1"
    params = []
    
    if search_term:
        query += " AND (sku LIKE ? OR model_number LIKE ? OR product_name LIKE ?)"
        params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY category, sku"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_product_price(product_id, customer_id=None):
    """获取产品价格"""
    conn = get_connection()
    cur = conn.cursor()
    
    # 先查客户专属价格
    if customer_id:
        cur.execute("""
            SELECT list_price, multiplier, list_price * multiplier as final_price, '客户专属' as price_type
            FROM ecoer_prices
            WHERE product_id = ? AND customer_id = ? AND is_active = 1
            AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_id, customer_id))
        row = cur.fetchone()
        if row:
            conn.close()
            return row
    
    # 再查标准价格
    cur.execute("""
        SELECT list_price, multiplier, list_price * multiplier as final_price, '标准价格' as price_type
        FROM ecoer_prices
        WHERE product_id = ? AND customer_id IS NULL AND is_active = 1
        AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
        ORDER BY effective_date DESC LIMIT 1
    """, (product_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_components(product_id):
    """获取产品散件"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT component_sku, component_name, component_type, list_price
        FROM ecoer_components
        WHERE product_id = ?
        ORDER BY component_type, component_name
    """, conn, params=(product_id,))
    conn.close()
    return df


def render_login():
    """登录页面"""
    st.title("🔐 Ecoer 价格查询系统")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("用户登录")
        
        with st.form("login"):
            username = st.text_input("用户名", placeholder="输入用户名")
            password = st.text_input("密码", type="password", placeholder="输入密码")
            submitted = st.form_submit_button("登录", use_container_width=True)
        
        if submitted and username and password:
            user = login_user(username, password)
            if user:
                st.session_state['ecoer_user'] = user
                st.success(f"欢迎, {user['name']}! ({user['role']})")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("用户名或密码错误")
        
        with st.expander("📋 默认账号"):
            st.markdown("""
            | 账号 | 密码 | 身份 |
            |------|------|------|
            | admin | admin123 | 管理员 |
            """)
            st.info("管理员登录后可以录入产品、客户、价格数据，并创建销售代表账号。")


def render_pricing_tool():
    """主价格查询界面"""
    
    if 'ecoer_user' not in st.session_state:
        render_login()
        return
    
    user = st.session_state['ecoer_user']
    
    # 顶部栏
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(f"**👤 {user['name']}** ({user['role']})")
    with col2:
        if user['role'] == 'sales_rep':
            st.markdown(f"**🌍 负责区域:** {user.get('territory', 'N/A')}")
    with col3:
        if st.button("退出登录", use_container_width=True):
            del st.session_state['ecoer_user']
            st.rerun()
    
    st.markdown("---")
    st.header("🔍 Ecoer 产品价格查询")
    st.markdown("**公式**: `最终价格 = List Price × Multiplier`")
    
    # 获取可访问客户
    customers = get_allowed_customers(user)
    
    # ========== 查询条件 ==========
    st.subheader("筛选条件")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if not customers.empty:
            customer_options = {f"{r['customer_code']} - {r['customer_name']} ({r['discount_tier']})": r['id'] 
                              for _, r in customers.iterrows()}
            customer_options["标准价格 (无客户)"] = None
            selected = st.selectbox("选择客户", list(customer_options.keys()))
            customer_id = customer_options[selected]
        else:
            st.warning("暂无可选客户")
            customer_id = None
    
    with col2:
        conn = get_connection()
        cats = pd.read_sql_query("SELECT DISTINCT category FROM ecoer_products WHERE is_active = 1", conn)
        conn.close()
        categories = ['全部'] + cats['category'].tolist() if not cats.empty else ['全部']
        category = st.selectbox("产品品类", categories)
        category = None if category == '全部' else category
    
    with col3:
        search_term = st.text_input("输入型号/SKU", placeholder="如: EODA19H")
    
    # ========== 查询结果 ==========
    if search_term or category:
        products = search_products(search_term, category)
        
        if products.empty:
            st.warning("未找到匹配的产品")
            return
        
        st.subheader(f"📦 查询结果 ({len(products)} 个产品)")
        
        for _, product in products.iterrows():
            price_row = get_product_price(product['id'], customer_id)
            
            with st.container():
                st.markdown("---")
                
                col_info, col_price = st.columns([2, 1])
                
                with col_info:
                    st.markdown(f"**{product['product_name']}**")
                    st.markdown(f"SKU: `{product['sku']}` | 型号: `{product['model_number']}`")
                    st.markdown(f"品类: `{product['category']}` | 系列: {product['series'] or 'N/A'}")
                    if product['description']:
                        st.markdown(f"描述: {product['description']}")
                
                with col_price:
                    if price_row:
                        list_price, multiplier, final_price, price_type = price_row
                        
                        st.metric("List Price", f"${list_price:,.2f}")
                        st.caption(f"类型: {price_type}")
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            st.metric("Multiplier", f"{multiplier:.0%}")
                        with col_m2:
                            discount = (1 - multiplier) * 100
                            delta = f"-{discount:.0f}%" if discount > 0 else None
                            st.metric("最终价格", f"${final_price:,.2f}", delta=delta)
                    else:
                        st.error("暂无价格数据")
                
                # 规格参数
                if product['specs']:
                    try:
                        specs = json.loads(product['specs'])
                        with st.expander("📋 规格参数"):
                            cols = st.columns(min(len(specs), 4))
                            for i, (k, v) in enumerate(specs.items()):
                                with cols[i % len(cols)]:
                                    st.metric(str(k), str(v))
                    except:
                        st.text(product['specs'])
                
                # 散件
                components = get_components(product['id'])
                if not components.empty:
                    with st.expander("🔩 散件清单"):
                        comp_display = components.copy()
                        if price_row:
                            comp_display['最终价格'] = comp_display['list_price'] * price_row[1]
                            st.dataframe(
                                comp_display[['component_sku', 'component_name', 'component_type', 'list_price', '最终价格']],
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    'list_price': st.column_config.NumberColumn('List Price', format='$%.2f'),
                                    '最终价格': st.column_config.NumberColumn('最终价格', format='$%.2f')
                                }
                            )
                        else:
                            st.dataframe(components, use_container_width=True, hide_index=True)
    else:
        st.info("👆 请选择筛选条件或输入型号开始查询")
        
        # 显示权限概览
        with st.expander("📋 您的访问权限"):
            st.markdown("**可访问客户:**")
            if not customers.empty:
                for _, c in customers.iterrows():
                    st.markdown(f"- {c['customer_name']} ({c['customer_code']}) - {c['discount_tier']}")
            else:
                st.markdown("- 暂无授权客户")
    
    # ========== 管理员面板 ==========
    if user['role'] == 'admin':
        render_admin_panel()


def render_admin_panel():
    """管理员面板 - 数据录入和管理"""
    st.markdown("---")
    st.header("⚙️ 管理员面板")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 录入产品", "🏢 录入客户", "💰 录入价格", "👤 管理用户", "📊 数据概览"
    ])
    
    # ========== 录入产品 ==========
    with tab1:
        st.subheader("添加 Ecoer 产品")
        
        with st.form("add_product"):
            col1, col2 = st.columns(2)
            with col1:
                sku = st.text_input("SKU*", placeholder="如: EODA19H-2436")
                model = st.text_input("型号*", placeholder="如: EODA19H-2436ABA")
                name = st.text_input("产品名称*", placeholder="如: Ecoer 19 SEER Heat Pump")
            with col2:
                category = st.selectbox("品类*", ["Condenser", "Air Handler", "Heat Kit", "Thermostat", "Package Unit", "Other"])
                series = st.text_input("系列", placeholder="如: EODA")
                desc = st.text_area("产品描述")
            
            specs = st.text_area("规格参数 (JSON)", placeholder='{"SEER": 19, "Tons": "2-3", "Refrigerant": "R-454B"}')
            
            if st.form_submit_button("保存产品", use_container_width=True):
                if sku and model and name:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO ecoer_products (sku, model_number, product_name, category, series, description, specs)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (sku, model, name, category, series, desc, specs))
                        conn.commit()
                        st.success(f"产品 {sku} 已添加！")
                    except sqlite3.IntegrityError:
                        st.error(f"SKU {sku} 已存在！")
                    conn.close()
                else:
                    st.error("请填写必填项 (SKU, 型号, 产品名称)")
        
        # 显示现有产品
        st.markdown("---")
        st.subheader("现有产品")
        conn = get_connection()
        products = pd.read_sql_query("SELECT id, sku, model_number, product_name, category, series FROM ecoer_products WHERE is_active = 1 ORDER BY category, sku", conn)
        st.dataframe(products, use_container_width=True, hide_index=True)
        conn.close()
    
    # ========== 录入客户 ==========
    with tab2:
        st.subheader("添加客户")
        
        with st.form("add_customer"):
            col1, col2 = st.columns(2)
            with col1:
                code = st.text_input("客户编码*", placeholder="如: C001")
                name = st.text_input("客户名称*", placeholder="如: Johnstone Supply")
                ctype = st.selectbox("客户类型", ["Distributor", "Contractor", "Dealer", "Other"])
            with col2:
                region = st.text_input("所在地区", placeholder="如: NY")
                tier = st.selectbox("折扣等级", ["Standard", "Preferred", "VIP"])
            
            if st.form_submit_button("保存客户", use_container_width=True):
                if code and name:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO ecoer_customers (customer_code, customer_name, customer_type, region, discount_tier)
                            VALUES (?, ?, ?, ?, ?)
                        """, (code, name, ctype, region, tier))
                        conn.commit()
                        st.success(f"客户 {name} 已添加！")
                    except sqlite3.IntegrityError:
                        st.error(f"客户编码 {code} 已存在！")
                    conn.close()
                else:
                    st.error("请填写必填项 (客户编码, 客户名称)")
        
        # 显示现有客户
        st.markdown("---")
        st.subheader("现有客户")
        conn = get_connection()
        customers = pd.read_sql_query("SELECT * FROM ecoer_customers WHERE is_active = 1 ORDER BY customer_code", conn)
        st.dataframe(customers, use_container_width=True, hide_index=True)
        conn.close()
    
    # ========== 录入价格 ==========
    with tab3:
        st.subheader("设置产品价格")
        
        conn = get_connection()
        products = pd.read_sql_query("SELECT id, sku, product_name FROM ecoer_products WHERE is_active = 1", conn)
        customers = pd.read_sql_query("SELECT id, customer_code, customer_name FROM ecoer_customers WHERE is_active = 1", conn)
        conn.close()
        
        if products.empty:
            st.warning("请先添加产品！")
        else:
            with st.form("add_price"):
                product = st.selectbox("选择产品", 
                    [f"{r['sku']} - {r['product_name']}" for _, r in products.iterrows()])
                product_id = products.iloc[[f"{r['sku']} - {r['product_name']}" for _, r in products.iterrows()].index(product)]['id'].values[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    customer_options = ["标准价格 (所有客户)"] + [f"{r['customer_code']} - {r['customer_name']}" for _, r in customers.iterrows()]
                    customer_sel = st.selectbox("适用客户", customer_options)
                    customer_id = None if customer_sel == "标准价格 (所有客户)" else customers.iloc[[f"{r['customer_code']} - {r['customer_name']}" for _, r in customers.iterrows()].index(customer_sel)]['id'].values[0]
                    
                    list_price = st.number_input("List Price ($)", min_value=0.0, step=100.0)
                with col2:
                    multiplier = st.number_input("Multiplier", min_value=0.1, max_value=2.0, value=1.0, step=0.05)
                    effective = st.date_input("生效日期")
                    notes = st.text_input("备注")
                
                if st.form_submit_button("保存价格", use_container_width=True):
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO ecoer_prices (product_id, customer_id, list_price, multiplier, effective_date, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (int(product_id), int(customer_id) if customer_id else None, list_price, multiplier, effective, notes))
                    conn.commit()
                    conn.close()
                    st.success("价格已设置！")
        
        # 显示现有价格
        st.markdown("---")
        st.subheader("现有价格")
        conn = get_connection()
        prices = pd.read_sql_query("""
            SELECT p.sku, p.product_name, c.customer_name, pr.list_price, pr.multiplier, 
                   pr.list_price * pr.multiplier as final_price, pr.effective_date, pr.notes
            FROM ecoer_prices pr
            JOIN ecoer_products p ON pr.product_id = p.id
            LEFT JOIN ecoer_customers c ON pr.customer_id = c.id
            WHERE pr.is_active = 1
            ORDER BY p.sku, pr.customer_id
        """, conn)
        st.dataframe(prices, use_container_width=True, hide_index=True)
        conn.close()
    
    # ========== 管理用户 ==========
    with tab4:
        st.subheader("添加销售代表")
        
        with st.form("add_user"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("用户名*")
                password = st.text_input("密码*", type="password")
                full_name = st.text_input("姓名*")
            with col2:
                role = st.selectbox("角色", ["sales_rep", "admin"])
                territory = st.text_input("负责区域", placeholder="如: NY,NJ,CT")
            
            # 选择授权客户
            conn = get_connection()
            all_customers = pd.read_sql_query("SELECT id, customer_code, customer_name FROM ecoer_customers WHERE is_active = 1", conn)
            conn.close()
            
            if not all_customers.empty:
                selected_customers = st.multiselect(
                    "授权客户",
                    [f"{r['customer_code']} - {r['customer_name']}" for _, r in all_customers.iterrows()]
                )
                allowed_ids = json.dumps([all_customers.iloc[[f"{r['customer_code']} - {r['customer_name']}" for _, r in all_customers.iterrows()].index(c)]['id'].values[0] for c in selected_customers])
            else:
                allowed_ids = "[]"
                st.info("暂无可选客户，请先添加客户")
            
            if st.form_submit_button("保存用户", use_container_width=True):
                if username and password and full_name:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO ecoer_users (username, password, full_name, role, territory, allowed_customers)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (username, password, full_name, role, territory, allowed_ids))
                        conn.commit()
                        st.success(f"用户 {username} 已添加！")
                    except sqlite3.IntegrityError:
                        st.error(f"用户名 {username} 已存在！")
                    conn.close()
                else:
                    st.error("请填写必填项")
        
        # 显示现有用户
        st.markdown("---")
        st.subheader("现有用户")
        conn = get_connection()
        users = pd.read_sql_query("SELECT id, username, full_name, role, territory, is_active FROM ecoer_users", conn)
        st.dataframe(users, use_container_width=True, hide_index=True)
        conn.close()
    
    # ========== 数据概览 ==========
    with tab5:
        st.subheader("系统数据概览")
        conn = get_connection()
        
        col1, col2, col3, col4 = st.columns(4)
        stats = {
            '产品': "SELECT COUNT(*) FROM ecoer_products WHERE is_active = 1",
            '客户': "SELECT COUNT(*) FROM ecoer_customers WHERE is_active = 1",
            '价格记录': "SELECT COUNT(*) FROM ecoer_prices WHERE is_active = 1",
            '用户': "SELECT COUNT(*) FROM ecoer_users WHERE is_active = 1"
        }
        
        for i, (name, query) in enumerate(stats.items()):
            cur = conn.cursor()
            cur.execute(query)
            count = cur.fetchone()[0]
            [col1, col2, col3, col4][i].metric(name, count)
        
        conn.close()


if __name__ == "__main__":
    render_pricing_tool()
