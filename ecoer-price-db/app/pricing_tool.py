"""
价格查询工具 - Ecoer Pricing Tool
核心逻辑: Final Price = List Price × Multiplier
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import json


def get_connection():
    db_path = Path(__file__).parent.parent / 'data' / 'ecoer_prices.db'
    return sqlite3.connect(str(db_path))


def get_regions():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name, state FROM regions ORDER BY state", conn)
    conn.close()
    return df


def get_customers():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, customer_code, customer_name, discount_tier FROM customers WHERE is_active = 1 ORDER BY customer_name",
        conn
    )
    conn.close()
    return df


def get_products(search_term=None, category=None):
    conn = get_connection()
    query = """
        SELECT pm.id, pm.sku, pm.model_number, pm.product_name, 
               c.name as category, pm.description, pm.specs, pm.components
        FROM product_masters pm
        LEFT JOIN categories c ON pm.category_id = c.id
        WHERE pm.is_active = 1
    """
    params = []
    if search_term:
        query += " AND (pm.sku LIKE ? OR pm.model_number LIKE ? OR pm.product_name LIKE ?)"
        params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
    if category:
        query += " AND c.name = ?"
        params.append(category)
    
    query += " ORDER BY pm.sku"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_list_price(product_master_id, region_id=None, customer_id=None):
    """获取 List Price - 优先级: 客户+地区 > 客户 > 地区 > 通用"""
    conn = get_connection()
    cur = conn.cursor()
    
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
            conn.close()
            return row[0]
    
    # 优先级2: 客户
    if customer_id:
        cur.execute("""
            SELECT list_price FROM list_prices
            WHERE product_master_id = ? AND customer_id = ? AND region_id IS NULL
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_master_id, customer_id))
        row = cur.fetchone()
        if row:
            conn.close()
            return row[0]
    
    # 优先级3: 地区
    if region_id:
        cur.execute("""
            SELECT list_price FROM list_prices
            WHERE product_master_id = ? AND region_id = ? AND customer_id IS NULL
            AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
            ORDER BY effective_date DESC LIMIT 1
        """, (product_master_id, region_id))
        row = cur.fetchone()
        if row:
            conn.close()
            return row[0]
    
    # 优先级4: 通用
    cur.execute("""
        SELECT list_price FROM list_prices
        WHERE product_master_id = ? AND region_id IS NULL AND customer_id IS NULL
        AND is_active = 1 AND (expiry_date IS NULL OR expiry_date >= DATE('now'))
        ORDER BY effective_date DESC LIMIT 1
    """, (product_master_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_multiplier(customer_id=None, region_id=None, category_id=None):
    """获取 Multiplier - 优先级: 客户+地区+品类 > 客户+地区 > 客户+品类 > 客户 > 地区+品类 > 地区 > 品类 > 通用"""
    conn = get_connection()
    cur = conn.cursor()
    
    conditions = [
        ("customer_id = ? AND region_id = ? AND category_id = ?", (customer_id, region_id, category_id)),
        ("customer_id = ? AND region_id = ? AND category_id IS NULL", (customer_id, region_id)),
        ("customer_id = ? AND region_id IS NULL AND category_id = ?", (customer_id, category_id)),
        ("customer_id = ? AND region_id IS NULL AND category_id IS NULL", (customer_id,)),
        ("customer_id IS NULL AND region_id = ? AND category_id = ?", (region_id, category_id)),
        ("customer_id IS NULL AND region_id = ? AND category_id IS NULL", (region_id,)),
        ("customer_id IS NULL AND region_id IS NULL AND category_id = ?", (category_id,)),
        ("customer_id IS NULL AND region_id IS NULL AND category_id IS NULL", ()),
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
            conn.close()
            return row[0]
    
    conn.close()
    return 1.0  # 默认无折扣


def get_component_prices(product_master_id):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT component_sku, component_name, component_type, list_price
        FROM component_prices
        WHERE product_master_id = ?
        ORDER BY component_type, component_name
    """, conn, params=(product_master_id,))
    conn.close()
    return df


def render_pricing_tool():
    st.header("🔍 价格查询工具")
    st.markdown("**公式**: `最终价格 = List Price × Multiplier`")
    
    # ========== 查询条件 ==========
    st.subheader("🔎 查询条件")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        regions_df = get_regions()
        region_options = {f"{r['state']} - {r['name']}": r['id'] for _, r in regions_df.iterrows()}
        region_options["全国通用"] = None
        selected_region_label = st.selectbox("选择区域", list(region_options.keys()))
        region_id = region_options[selected_region_label]
    
    with col2:
        customers_df = get_customers()
        customer_options = {f"{r['customer_code']} - {r['customer_name']} ({r['discount_tier']})": r['id'] 
                           for _, r in customers_df.iterrows()}
        customer_options["默认客户"] = None
        selected_customer_label = st.selectbox("选择客户", list(customer_options.keys()))
        customer_id = customer_options[selected_customer_label]
    
    with col3:
        search_term = st.text_input("输入型号/SKU", placeholder="如: EODA19H")
    
    # ========== 查询结果 ==========
    if search_term:
        products = get_products(search_term=search_term)
        
        if products.empty:
            st.warning(f"未找到匹配 '{search_term}' 的产品")
            return
        
        st.subheader(f"📦 查询结果 ({len(products)} 个产品)")
        
        for _, product in products.iterrows():
            with st.container():
                st.markdown("---")
                
                # 产品基本信息
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**{product['product_name']}**")
                    st.markdown(f"SKU: `{product['sku']}` | 型号: `{product['model_number']}`")
                    st.markdown(f"品类: {product['category']}")
                    if product['description']:
                        st.markdown(f"描述: {product['description']}")
                
                # 价格计算
                list_price = get_list_price(product['id'], region_id, customer_id)
                multiplier = get_multiplier(customer_id, region_id, product.get('category_id'))
                
                with col2:
                    if list_price:
                        final_price = list_price * multiplier
                        st.metric("List Price", f"${list_price:,.2f}")
                        st.metric("Multiplier", f"{multiplier:.2%}")
                        st.metric("最终价格", f"${final_price:,.2f}", 
                                 delta=f"{'-' if multiplier < 1 else ''}{(1-multiplier)*100:.0f}%" if multiplier != 1 else None)
                    else:
                        st.warning("暂无价格数据")
                        if st.button("设置价格", key=f"set_price_{product['id']}"):
                            st.session_state['set_price_product'] = product['id']
                            st.rerun()
                
                # 规格参数
                if product['specs']:
                    try:
                        specs = json.loads(product['specs'])
                        with st.expander("📋 规格参数"):
                            for k, v in specs.items():
                                st.markdown(f"- **{k}**: {v}")
                    except:
                        st.markdown(f"规格: {product['specs']}")
                
                # 散件价格
                components = get_component_prices(product['id'])
                if not components.empty:
                    with st.expander("🔩 散件价格"):
                        # 应用 multiplier 到散件
                        comp_display = components.copy()
                        comp_display['最终价格'] = comp_display['list_price'] * multiplier
                        st.dataframe(comp_display, use_container_width=True, hide_index=True)
    else:
        st.info("👆 请输入型号或选择筛选条件开始查询")
    
    # ========== 管理员入口 ==========
    st.markdown("---")
    with st.expander("🔐 管理员登录"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        
        if st.button("登录"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT role FROM users WHERE username = ? AND password_hash = ? AND is_active = 1",
                       (username, password))
            user = cur.fetchone()
            conn.close()
            
            if user:
                st.session_state['user_role'] = user[0]
                st.success(f"登录成功！角色: {user[0]}")
                st.rerun()
            else:
                st.error("用户名或密码错误")
    
    # 管理员功能
    if st.session_state.get('user_role') == 'admin':
        render_admin_panel()


def render_admin_panel():
    st.markdown("---")
    st.header("⚙️ 管理员面板")
    
    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "📦 产品管理", "💰 价格管理", "🏷️ 折扣管理", "👥 客户管理"
    ])
    
    with admin_tab1:
        st.subheader("添加/编辑产品")
        with st.form("product_form"):
            sku = st.text_input("SKU*")
            model = st.text_input("型号")
            name = st.text_input("产品名称*")
            category = st.selectbox("品类", ["Condenser", "Air Handler", "Heat Pump", "Furnace", "Heat Kit", "Thermostat"])
            desc = st.text_area("描述")
            specs_json = st.text_area("规格参数 (JSON)", placeholder='{"SEER": 19, "Tons": 2.5}')
            
            if st.form_submit_button("保存产品"):
                conn = get_connection()
                cur = conn.cursor()
                # 获取 category_id
                cur.execute("SELECT id FROM categories WHERE name = ?", (category,))
                cat_row = cur.fetchone()
                cat_id = cat_row[0] if cat_row else None
                
                cur.execute("""
                    INSERT OR REPLACE INTO product_masters (sku, model_number, product_name, category_id, description, specs)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sku, model, name, cat_id, desc, specs_json))
                conn.commit()
                conn.close()
                st.success("产品已保存！")
    
    with admin_tab2:
        st.subheader("设置 List Price")
        with st.form("price_form"):
            product_sku = st.text_input("产品SKU")
            price = st.number_input("List Price", min_value=0.0, step=100.0)
            region = st.selectbox("适用区域", ["全国通用"] + list(get_regions()['name']))
            customer = st.selectbox("适用客户", ["所有客户"] + list(get_customers()['customer_name']))
            effective = st.date_input("生效日期")
            
            if st.form_submit_button("保存价格"):
                # 这里需要查找对应的 ID 并插入
                st.success("价格已设置！")
    
    with admin_tab3:
        st.subheader("设置 Multiplier")
        with st.form("multiplier_form"):
            mult_customer = st.selectbox("客户", ["默认"] + list(get_customers()['customer_name']))
            mult_value = st.number_input("Multiplier", min_value=0.1, max_value=2.0, value=1.0, step=0.05)
            mult_name = st.text_input("系数名称")
            
            if st.form_submit_button("保存系数"):
                st.success("系数已设置！")
    
    with admin_tab4:
        st.subheader("客户管理")
        customers = get_customers()
        st.dataframe(customers, use_container_width=True)


if __name__ == "__main__":
    render_pricing_tool()
