"""
Ecoer Price Query System V3
- List Price Version Management
- Customer List Price + Modifier Setup
- Batch Upload/Download/Update
"""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import json
import time
import io
from datetime import datetime
import re

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'ecoer_pricing.db'

def get_connection():
    return sqlite3.connect(str(DB_PATH))

def normalize_col(name):
    """Normalize column name for flexible matching"""
    name = name.lower().strip()
    name = re.sub(r'[\s\-_]+', '', name)
    return name

def auto_match_columns(uploaded_df, expected_columns):
    """Auto-match uploaded columns to expected columns."""
    uploaded_cols = list(uploaded_df.columns)
    norm_uploaded = {normalize_col(c): c for c in uploaded_cols}
    
    matched = {}
    for exp_col in expected_columns:
        norm_exp = normalize_col(exp_col)
        matched[exp_col] = norm_uploaded.get(norm_exp)
    
    return matched

def login_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, full_name, role, territory, allowed_customers 
        FROM ecoer_users 
        WHERE username = ? AND password = ? AND is_active = 1
    """, (username, password))
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

def get_price_lists():
    """Get all List Price versions"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT id, price_list_code, price_list_name, description, region, effective_date, is_active
        FROM ecoer_price_lists
        WHERE is_active = 1
        ORDER BY price_list_code
    """, conn)
    conn.close()
    return df

def get_customers():
    """Get all customers"""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT c.*, pl.price_list_code, pl.price_list_name
        FROM ecoer_customers c
        LEFT JOIN ecoer_price_lists pl ON c.price_list_id = pl.id
        WHERE c.is_active = 1
        ORDER BY c.customer_code
    """, conn)
    conn.close()
    return df

def get_products(search_term=None, category=None, series=None):
    """Search products"""
    conn = get_connection()
    query = "SELECT * FROM ecoer_products WHERE is_active = 1"
    params = []
    
    if search_term:
        query += """ AND (
            sku LIKE ? OR model_number LIKE ? OR 
            product_name LIKE ? OR series LIKE ? OR description LIKE ?
        )"""
        like_term = f'%{search_term}%'
        params.extend([like_term] * 5)
    
    if category and category != 'All':
        query += " AND category = ?"
        params.append(category)
    
    if series and series != 'All':
        query += " AND series = ?"
        params.append(series)
    
    query += " ORDER BY series, sku"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_product_price(product_id, price_list_id, customer_id=None):
    """Get product price - based on List Price + Customer Modifier"""
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Get List Price
    cur.execute("""
        SELECT lp.list_price, pl.price_list_code, pl.price_list_name
        FROM ecoer_list_prices lp
        JOIN ecoer_price_lists pl ON lp.price_list_id = pl.id
        WHERE lp.product_id = ? AND lp.price_list_id = ? AND lp.is_active = 1
    """, (product_id, price_list_id))
    list_price_row = cur.fetchone()
    
    if not list_price_row:
        conn.close()
        return None
    
    list_price = list_price_row[0]
    price_list_code = list_price_row[1]
    price_list_name = list_price_row[2]
    
    # 2. Get Customers Modifier
    modifier = 1.0
    modifier_source = "Standard (100%)"
    
    if customer_id:
        # First SearchProductLevelSpecific Modifier
        cur.execute("""
            SELECT modifier, notes FROM ecoer_customer_product_modifiers
            WHERE customer_id = ? AND product_id = ? AND is_active = 1
        """, (customer_id, product_id))
        product_modifier = cur.fetchone()
        
        if product_modifier:
            modifier = product_modifier[0]
            modifier_source = f"ProductExclusive ({modifier:.0%})"
        else:
            # Search Customer AgainDefault Modifier
            cur.execute("SELECT default_modifier FROM ecoer_customers WHERE id = ?", (customer_id,))
            customer_modifier = cur.fetchone()
            if customer_modifier and customer_modifier[0]:
                modifier = customer_modifier[0]
                modifier_source = f"Customer Default ({modifier:.0%})"
    
    sales_price = list_price * modifier
    
    conn.close()
    return {
        'list_price': list_price,
        'modifier': modifier,
        'sales_price': sales_price,
        'price_list_code': price_list_code,
        'price_list_name': price_list_name,
        'modifier_source': modifier_source
    }

def get_filter_options():
    """Get Filter Options"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT DISTINCT category FROM ecoer_products WHERE is_active = 1 ORDER BY category")
    categories = [r[0] for r in cur.fetchall()]
    
    cur.execute("SELECT DISTINCT series FROM ecoer_products WHERE is_active = 1 AND series IS NOT NULL ORDER BY series")
    series = [r[0] for r in cur.fetchall()]
    
    conn.close()
    return categories, series

# ========== Page Configuration ==========
st.set_page_config(page_title="Price Query System V3", page_icon="💰", layout="wide")

if st.sidebar.button("← Return to Home"):
    st.switch_page("home.py")

st.title("💰 Ecoer Price Query System V3")
st.markdown("**List Price Version Management + Customer Modifier**")
st.markdown("---")

# ========== Login Status Management ==========
if 'pricing_user' not in st.session_state:
    st.session_state['pricing_user'] = None

# ========== Login interface ==========
if st.session_state['pricing_user'] is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("User Login")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            user = login_user(username, password)
            if user:
                st.session_state['pricing_user'] = user
                st.success(f"Welcome, {user['name']}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid username or password")
        
        with st.expander("Default Account"):
            st.markdown("admin / admin123")
    
    st.stop()

user = st.session_state['pricing_user']

# Top Bar
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown(f"**{user['name']}** ({user['role']})")
with col3:
    if st.button("Logout", use_container_width=True):
        st.session_state['pricing_user'] = None
        st.rerun()

st.markdown("---")

# ========== Feature Selection ==========
if user['role'] == 'admin':
    menu = st.sidebar.radio("Menu", [
        "🔍 Price Query",
        "📋 List Price Management",
        "🏢 Customer Management",
        "📦 Product Management",
        "📥 Bulk Upload/Download"
    ])
else:
    menu = st.sidebar.radio("Menu", ["🔍 Price Query"])

# ==================== Price Query ====================
if menu == "🔍 Price Query":
    st.header("🔍 Product Price Query")
    st.markdown("Formula: `Sales Price = List Price × Modifier`")
    
    customers = get_customers()
    price_lists = get_price_lists()
    categories, series_list = get_filter_options()
    
    # ========== Select Customer ==========
    st.subheader("1. Select Customer")
    if not customers.empty:
        customer_options = {}
        for _, r in customers.iterrows():
            label = f"{r['customer_code']} - {r['customer_name']}"
            if pd.notna(r['price_list_code']):
                label += f" (List: {r['price_list_code']})"
            customer_options[label] = {
                'id': r['id'],
                'code': r['customer_code'],
                'name': r['customer_name'],
                'price_list_id': r['price_list_id'],
                'price_list_code': r['price_list_code'],
                'default_modifier': r['default_modifier']
            }
        
        selected_label = st.selectbox("Customer", list(customer_options.keys()))
        selected_customer = customer_options[selected_label]
        
        # Show Customer Information
        info_cols = st.columns(3)
        with info_cols[0]:
            st.info(f"List Price: **{selected_customer['price_list_code'] or 'Not Bound'}**")
        with info_cols[1]:
            st.info(f"Default Modifier: **{selected_customer['default_modifier']:.0%}**")
        with info_cols[2]:
            st.info(f"Discount Tier: **{customers[customers['id']==selected_customer['id']]['discount_tier'].values[0]}**")
    else:
        st.warning("No customers available")
        selected_customer = None
    
    st.markdown("---")
    
    # ========== Search products ==========
    st.subheader("2. Search Products")
    
    search_term = st.text_input("Enter Model/SKU/Keyword", placeholder="Such as: EO, TDI, 19H...")
    
    with st.expander("Advanced Filter"):
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            filter_category = st.selectbox("Category", ['All'] + categories) if categories else st.selectbox("Category", ['All'])
        with fcol2:
            filter_series = st.selectbox("Series", ['All'] + series_list) if series_list else st.selectbox("Series", ['All'])
    
    if st.button("🔍 Search", use_container_width=True) or search_term:
        products = get_products(
            search_term,
            filter_category if filter_category != 'All' else None,
            filter_series if filter_series != 'All' else None
        )
        
        if products.empty:
            st.warning("No matching products found")
        else:
            st.subheader(f"Found {len(products)}  Products")
            
            for _, product in products.iterrows():
                if selected_customer and selected_customer['price_list_id']:
                    price_info = get_product_price(
                        product['id'], 
                        selected_customer['price_list_id'],
                        selected_customer['id']
                    )
                else:
                    price_info = None
                
                with st.container():
                    st.markdown("---")
                    
                    # ProductInformation
                    col_info, col_price = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"**{product['product_name']}**")
                        st.markdown(f"SKU: `{product['sku']}` | Model: `{product['model_number']}`")
                        
                        tags = []
                        if product['series']:
                            tags.append(f"Series: {product['series']}")
                        if product['category']:
                            tags.append(f"Category: {product['category']}")
                        st.markdown(" | ".join([f"`{t}`" for t in tags]))
                        
                        # Description
                        if product['description']:
                            st.markdown(f"📝 {product['description']}")
                    
                    with col_price:
                        if price_info:
                            st.metric("List Price", f"${price_info['list_price']:,.2f}")
                            st.caption(f"From: {price_info['price_list_code']}")
                            
                            pcol1, pcol2 = st.columns(2)
                            with pcol1:
                                st.metric("Modifier", f"{price_info['modifier']:.0%}")
                            with pcol2:
                                discount = (1 - price_info['modifier']) * 100
                                st.metric("Sales Price", f"${price_info['sales_price']:,.2f}", 
                                         delta=f"-{discount:.0f}%" if discount > 0 else None)
                            
                            st.caption(f"Coefficient Source: {price_info['modifier_source']}")
                        else:
                            st.error("No price data available")
                    
                    # Specifications
                    specs = []
                    if product['seer']:
                        specs.append(("SEER", product['seer']))
                    if product['hspf']:
                        specs.append(("HSPF", product['hspf']))
                    if product['tons']:
                        specs.append(("Tons", product['tons']))
                    if product['refrigerant']:
                        specs.append(("Refrigerant", product['refrigerant']))
                    
                    if specs:
                        with st.expander("Specifications"):
                            spec_cols = st.columns(len(specs))
                            for i, (k, v) in enumerate(specs):
                                with spec_cols[i]:
                                    st.metric(str(k), str(v))

# ==================== List Price Management ====================
elif menu == "📋 List Price Management" and user['role'] == 'admin':
    st.header("📋 List Price Version Management")
    
    price_lists = get_price_lists()
    
    # Create New List Price
    with st.expander("➕ Create New List Price Version"):
        with st.form("create_price_list"):
            col1, col2 = st.columns(2)
            with col1:
                code = st.text_input("Version Code*", placeholder="Such as: NE_REG, SE_2024Q1")
                name = st.text_input("Version Name*", placeholder="Such as: Northeast Regular")
            with col2:
                region = st.text_input("Applicable Region", placeholder="Such as: NY,NJ,CT")
                effective = st.date_input("Effective Date")
            
            desc = st.text_area("Description")
            
            if st.form_submit_button("Create Version", use_container_width=True):
                if code and name:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO ecoer_price_lists (price_list_code, price_list_name, description, region, effective_date)
                            VALUES (?, ?, ?, ?, ?)
                        """, (code, name, desc, region, effective))
                        conn.commit()
                        st.success(f"List Price Version {code} Created！")
                        time.sleep(0.5)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Version Code {code} Already exists！")
                    conn.close()
    
    # Show Existing Versions
    st.subheader("Existing List Price Versions")
    if not price_lists.empty:
        st.dataframe(price_lists, use_container_width=True, hide_index=True)
        
        # Select VersionView/Edit
        selected_pl = st.selectbox("Select Version to View Details", 
                                   [f"{r['price_list_code']} - {r['price_list_name']}" for _, r in price_lists.iterrows()])
        selected_pl_id = price_lists[price_lists['price_list_code'] == selected_pl.split(' - ')[0]]['id'].values[0]
        
        # Show Price Details for This Version
        conn = get_connection()
        prices = pd.read_sql_query("""
            SELECT p.sku, p.model_number, p.product_name, p.category, p.series, lp.list_price
            FROM ecoer_list_prices lp
            JOIN ecoer_products p ON lp.product_id = p.id
            WHERE lp.price_list_id = ? AND lp.is_active = 1
            ORDER BY p.category, p.sku
        """, conn, params=(selected_pl_id,))
        conn.close()
        
        st.caption(f"This version contains {len(prices)} product prices")
        st.dataframe(prices, use_container_width=True, hide_index=True)
        
        # Download Template
        st.markdown("---")
        st.subheader("Bulk Update Prices")
        
        template = pd.DataFrame({
            'sku': ['EODA19H-2436', 'EAHDEN-24'],
            'model_number': ['EODA19H-2436ABA', 'EAHDEN-24'],
            'product_name': ['Heat Pump R454b 3 Ton Top Discharge', 'Air Handler 2 Ton'],
            'category': ['Condenser', 'Air Handler'],
            'series': ['EODA', 'EAHD'],
            'seer': ['20', '16'],
            'tons': ['3', '2'],
            'refrigerant': ['R454b', 'R410a'],
            'description': ['', ''],
            'list_price': [7900.00, 4222.50],
            'notes': ['', '']
        })
        
        buffer = io.BytesIO()
        template.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        col_dl, col_ul = st.columns(2)
        with col_dl:
            st.download_button("📥 Download Upload Template", buffer, 
                             f"price_list_template_{selected_pl.split(' - ')[0]}.xlsx",
                             use_container_width=True)
        
        with col_ul:
            uploaded = st.file_uploader("Upload Price Update", type=['xlsx', 'csv'])
            if uploaded:
                try:
                    if uploaded.name.endswith('.csv'):
                        df_up = pd.read_csv(uploaded)
                    else:
                        df_up = pd.read_excel(uploaded, header=1)
                    
                    st.success(f"Read {len(df_up)} rows of data")
                    
                    # Auto-match columns
                    expected_up = ['sku', 'model', 'model_number', 'product_name', 'category', 
                                  'series', 'seer', 'tons', 'refrigerant', 'description', 
                                  'list_price', 'notes']
                    col_mapping = auto_match_columns(df_up, expected_up)
                    
                    st.info("Auto-detected column mapping:")
                    mapped_lines = []
                    for k, v in col_mapping.items():
                        if v:
                            mapped_lines.append(f"**{k}** ← {v}")
                        else:
                            mapped_lines.append(f"**{k}** ← (not found)")
                    st.write(" | ".join(mapped_lines))
                    
                    if st.button("Confirm Price Update", type="primary"):
                        conn = get_connection()
                        cur = conn.cursor()
                        updated = 0
                        
                        for _, row in df_up.iterrows():
                            prod = None
                            for key in ['sku', 'model', 'model_number']:
                                src_col = col_mapping.get(key)
                                if not src_col:
                                    continue
                                val = str(row.get(src_col, '')).strip()
                                if not val:
                                    continue
                                cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (val,))
                                prod = cur.fetchone()
                                if prod:
                                    break
                                cur.execute("SELECT id FROM ecoer_products WHERE model_number = ?", (val,))
                                prod = cur.fetchone()
                                if prod:
                                    break
                                val_clean = val.replace('ABA', '').strip()
                                if val_clean != val:
                                    cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (val_clean,))
                                    prod = cur.fetchone()
                                    if prod:
                                        break
                            
                            if prod:
                                prod_id = prod[0]
                                lp_col = col_mapping.get('list_price')
                                list_price = float(row[lp_col]) if lp_col and lp_col in row else 0
                                notes_col = col_mapping.get('notes')
                                notes_val = str(row[notes_col]) if notes_col and notes_col in row else ''
                                
                                cur.execute("""
                                    INSERT OR REPLACE INTO ecoer_list_prices 
                                    (price_list_id, product_id, list_price, notes)
                                    VALUES (?, ?, ?, ?)
                                """, (selected_pl_id, prod_id, list_price, notes_val))
                                updated += 1
                                
                                update_fields = []
                                update_values = []
                                for prod_col in ['product_name', 'category', 'series', 'seer', 'tons',
                                              'refrigerant', 'description', 'model_number']:
                                    src_col = col_mapping.get(prod_col)
                                    if src_col and src_col in row and pd.notna(row[src_col]) and str(row[src_col]).strip():
                                        update_fields.append(f"{prod_col} = ?")
                                        update_values.append(str(row[src_col]).strip())
                                
                                if update_fields:
                                    update_values.append(prod_id)
                                    cur.execute(f"UPDATE ecoer_products SET {', '.join(update_fields)} WHERE id = ?", update_values)
                        
                        conn.commit()
                        conn.close()
                        st.success(f"Updated {updated} product prices!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Upload failed: {e}")
    else:
        st.info("No List Price versions available, please create one first")

# ==================== Customer Management ====================
elif menu == "🏢 Customer Management" and user['role'] == 'admin':
    st.header("🏢 Customer Management")
    
    customers = get_customers()
    price_lists = get_price_lists()
    
    # Create New Customer
    with st.expander("➕ Create New Customer"):
        with st.form("create_customer"):
            col1, col2 = st.columns(2)
            with col1:
                code = st.text_input("Customer Code*", placeholder="Such as: C001")
                name = st.text_input("Customer Name*", placeholder="Such as: Johnstone Supply")
                ctype = st.selectbox("Customer Type", ["Distributor", "Contractor", "Dealer", "Other"])
            with col2:
                region = st.text_input("Region", placeholder="Such as: NY,NJ")
                tier = st.selectbox("Discount Tier", ["Standard", "Preferred", "VIP"])
                default_mod = st.number_input("Default Modifier", min_value=0.1, max_value=2.0, value=1.0, step=0.05)
            
            # Select Bound List Price
            if not price_lists.empty:
                pl_options = ["(Do Not Bind)"] + [f"{r['price_list_code']} - {r['price_list_name']}" for _, r in price_lists.iterrows()]
                selected_pl = st.selectbox("Bind List Price Version", pl_options)
                price_list_id = None if selected_pl == "(Do Not Bind)" else price_lists[price_lists['price_list_code'] == selected_pl.split(' - ')[0]]['id'].values[0]
            else:
                st.warning("No List Price versions available, please create one first")
                price_list_id = None
            
            if st.form_submit_button("Save Customer", use_container_width=True):
                if code and name:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO ecoer_customers 
                            (customer_code, customer_name, customer_type, region, discount_tier, price_list_id, default_multiplier)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (code, name, ctype, region, tier, price_list_id, default_mod))
                        conn.commit()
                        st.success(f"Customer {name} Created！")
                        time.sleep(0.5)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Customer Code {code} Already exists！")
                    conn.close()
    
    # ShowExisting Customers
    st.subheader("Existing Customers")
    if not customers.empty:
        st.dataframe(customers[['customer_code', 'customer_name', 'customer_type', 'region', 'discount_tier', 'price_list_code', 'default_multiplier']], 
                    use_container_width=True, hide_index=True)
        
        # Set CustomerSpecific Modifier
        st.markdown("---")
        st.subheader("Set Customer-Specific Product Modifier")
        
        col_cust, col_prod = st.columns(2)
        with col_cust:
            selected_cust = st.selectbox("Select Customer", [f"{r['customer_code']} - {r['customer_name']}" for _, r in customers.iterrows()])
            cust_id = customers[customers['customer_code'] == selected_cust.split(' - ')[0]]['id'].values[0]
        
        conn = get_connection()
        products = pd.read_sql_query("SELECT id, sku, product_name FROM ecoer_products WHERE is_active = 1", conn)
        conn.close()
        
        with col_prod:
            selected_prod = st.selectbox("Select Product", [f"{r['sku']} - {r['product_name']}" for _, r in products.iterrows()])
            prod_id = products[products['sku'] == selected_prod.split(' - ')[0]]['id'].values[0]
        
        mod = st.number_input("Specific Modifier", min_value=0.1, max_value=2.0, value=1.0, step=0.05)
        notes = st.text_input("Notes")
        
        if st.button("Save Specific Modifier"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO ecoer_customer_product_modifiers
                (customer_id, product_id, modifier, notes)
                VALUES (?, ?, ?, ?)
            """, (int(cust_id), int(prod_id), mod, notes))
            conn.commit()
            conn.close()
            st.success("Specific Modifier set!")
    else:
        st.info("No customers available")

# ==================== ProductManagement ====================
elif menu == "📦 Product Management" and user['role'] == 'admin':
    st.header("📦 Product Management")
    
    conn = get_connection()
    products = pd.read_sql_query("""
        SELECT id, sku, model_number, product_name, category, series, seer, tons, refrigerant, is_active
        FROM ecoer_products
        ORDER BY category, sku
    """, conn)
    conn.close()
    
    st.dataframe(products, use_container_width=True, hide_index=True)
    
    # Add New Product
    with st.expander("➕ Add New Product"):
        with st.form("add_product"):
            col1, col2 = st.columns(2)
            with col1:
                sku = st.text_input("SKU*")
                model = st.text_input("Model*")
                name = st.text_input("Product Name*")
            with col2:
                category = st.selectbox("Category", ["Condenser", "Air Handler", "Coil", "Heat Kit", "Thermostat", "Package Unit", "Other"])
                series = st.text_input("Series")
            
            desc = st.text_area("Description")
            
            if st.form_submit_button("Save Product"):
                if sku and model and name:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO ecoer_products (sku, model_number, product_name, category, series, description)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (sku, model, name, category, series, desc))
                        conn.commit()
                        st.success(f"Product {sku} added！")
                        time.sleep(0.5)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"SKU {sku} Already exists！")
                    conn.close()

# ==================== Batch Upload/Download ====================
elif menu == "📥 Bulk Upload/Download" and user['role'] == 'admin':
    st.header("📥 Bulk Upload / 📤 Download")
    
    tab1, tab2, tab3 = st.tabs(["Upload List Price", "Download Price List", "Bulk Update Customer Modifier"])
    
    with tab1:
        st.subheader("Bulk Upload List Price")
        st.markdown("""
        **Excel Format:**
        | sku | model_number | product_name | category | series | seer | tons | refrigerant | description | list_price | notes |
        |-----|--------------|--------------|----------|--------|------|------|-------------|-------------|------------|-------|
        | EODA19H-2436 | EODA19H-2436ABA | Heat Pump 3 Ton | Condenser | EODA | 20 | 3 | R454b | | 7900 | |
        """)
        
        price_lists = get_price_lists()
        if not price_lists.empty:
            selected_pl = st.selectbox("Select List Price Version", 
                                     [f"{r['price_list_code']} - {r['price_list_name']}" for _, r in price_lists.iterrows()])
            pl_id = price_lists[price_lists['price_list_code'] == selected_pl.split(' - ')[0]]['id'].values[0]
            
            uploaded = st.file_uploader("Select File", type=['xlsx', 'csv'])
            if uploaded:
                try:
                    if uploaded.name.endswith('.csv'):
                        df = pd.read_csv(uploaded)
                    else:
                        df = pd.read_excel(uploaded, header=1)
                    
                    st.success(f"Read {len(df)} rows")
                    st.dataframe(df.head())
                    
                    # Auto-match columns
                    expected = ['sku', 'model', 'model_number', 'product_name', 'category', 
                               'series', 'seer', 'tons', 'refrigerant', 'description', 
                               'list_price', 'notes']
                    col_mapping = auto_match_columns(df, expected)
                    
                    # Show mapping results
                    st.info("Auto-detected column mapping:")
                    mapped_lines = []
                    for k, v in col_mapping.items():
                        if v:
                            mapped_lines.append(f"**{k}** ← {v}")
                        else:
                            mapped_lines.append(f"**{k}** ← (not found)")
                    st.write(" | ".join(mapped_lines))
                    
                    # Allow manual override for key columns
                    with st.expander("Manual column mapping override"):
                        key_cols = ['sku', 'model', 'model_number', 'list_price', 'notes']
                        for key in key_cols:
                            options = ['(not mapped)'] + list(df.columns)
                            current = col_mapping.get(key, '')
                            idx = options.index(current) if current in options else 0
                            selected = st.selectbox(f"Map '{key}' to:", options, index=idx, key=f"map_{key}")
                            col_mapping[key] = None if selected == '(not mapped)' else selected
                    
                    if st.button("Confirm Import", type="primary"):
                        conn = get_connection()
                        cur = conn.cursor()
                        imported = 0
                        not_found = []
                        
                        for _, row in df.iterrows():
                            # Try multiple product ID columns
                            prod = None
                            for key in ['sku', 'model', 'model_number']:
                                src_col = col_mapping.get(key)
                                if not src_col:
                                    continue
                                val = str(row.get(src_col, '')).strip()
                                if not val:
                                    continue
                                cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (val,))
                                prod = cur.fetchone()
                                if prod:
                                    break
                                cur.execute("SELECT id FROM ecoer_products WHERE model_number = ?", (val,))
                                prod = cur.fetchone()
                                if prod:
                                    break
                                # Try without ABA suffix
                                val_clean = val.replace('ABA', '').strip()
                                if val_clean != val:
                                    cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (val_clean,))
                                    prod = cur.fetchone()
                                    if prod:
                                        break
                            
                            if prod:
                                prod_id = prod[0]
                                lp_col = col_mapping.get('list_price')
                                list_price = float(row[lp_col]) if lp_col and lp_col in row else 0
                                notes_col = col_mapping.get('notes')
                                notes_val = str(row[notes_col]) if notes_col and notes_col in row else ''
                                
                                cur.execute("""
                                    INSERT OR REPLACE INTO ecoer_list_prices
                                    (price_list_id, product_id, list_price, notes)
                                    VALUES (?, ?, ?, ?)
                                """, (pl_id, prod_id, list_price, notes_val))
                                imported += 1
                                
                                # Update product info if provided
                                update_fields = []
                                update_values = []
                                for prod_col in ['product_name', 'category', 'series', 'seer', 'tons', 
                                                'refrigerant', 'description', 'model_number']:
                                    src_col = col_mapping.get(prod_col)
                                    if src_col and src_col in row and pd.notna(row[src_col]) and str(row[src_col]).strip():
                                        update_fields.append(f"{prod_col} = ?")
                                        update_values.append(str(row[src_col]).strip())
                                
                                if update_fields:
                                    update_values.append(prod_id)
                                    cur.execute(f"UPDATE ecoer_products SET {', '.join(update_fields)} WHERE id = ?", update_values)
                            else:
                                for key in ['sku', 'model', 'model_number']:
                                    src_col = col_mapping.get(key)
                                    if src_col:
                                        val = str(row.get(src_col, '')).strip()
                                        if val:
                                            not_found.append(val)
                                            break
                        
                        if not_found:
                            st.warning(f"{len(not_found)} products not found: {', '.join(not_found[:10])}{'...' if len(not_found) > 10 else ''}")
                        
                        conn.commit()
                        conn.close()
                        st.success(f"Successfully imported {imported} prices!")
                        st.balloons()
                except Exception as e:
                    st.error(f"Import failed: {e}")
        else:
            st.warning("Please create a List Price version first")
    
    with tab2:
        st.subheader("Download Price List")
        
        price_lists = get_price_lists()
        if not price_lists.empty:
            selected_pl = st.selectbox("Select Version", 
                                     [f"{r['price_list_code']} - {r['price_list_name']}" for _, r in price_lists.iterrows()],
                                     key="dl_pl")
            pl_id = price_lists[price_lists['price_list_code'] == selected_pl.split(' - ')[0]]['id'].values[0]
            
            conn = get_connection()
            df = pd.read_sql_query("""
                SELECT p.sku, p.model_number, p.product_name, p.category, p.series, 
                       p.seer, p.tons, p.refrigerant, p.description, 
                       lp.list_price, lp.notes
                FROM ecoer_list_prices lp
                JOIN ecoer_products p ON lp.product_id = p.id
                WHERE lp.price_list_id = ? AND lp.is_active = 1
                ORDER BY p.category, p.sku
            """, conn, params=(pl_id,))
            conn.close()
            
            st.caption(f"Total {len(df)} records")
            st.dataframe(df, use_container_width=True)
            
            if not df.empty:
                col1, col2 = st.columns(2)
                with col1:
                    buffer = io.BytesIO()
                    df.to_excel(buffer, index=False, engine='openpyxl')
                    buffer.seek(0)
                    st.download_button("📥 Excel", buffer, f"{selected_pl.split(' - ')[0]}_prices.xlsx", use_container_width=True)
                with col2:
                    buffer = io.BytesIO()
                    df.to_csv(buffer, index=False, encoding='utf-8-sig')
                    buffer.seek(0)
                    st.download_button("📥 CSV", buffer, f"{selected_pl.split(' - ')[0]}_prices.csv", use_container_width=True)
    
    with tab3:
        st.subheader("Bulk Update Customer Product Modifier")
        
        # Expected columns for auto-match
        expected_cust = ['customer_code', 'customer_name', 'sku', 'modifier', 'notes']
        
        uploaded = st.file_uploader("Select Modifier File", type=['xlsx', 'csv'])
        if uploaded:
            try:
                if uploaded.name.endswith('.csv'):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)
                
                st.success(f"Read {len(df)} rows")
                st.dataframe(df.head())
                
                # Auto-match columns
                col_mapping = auto_match_columns(df, expected_cust)
                
                st.info("Auto-detected column mapping:")
                mapped_lines = []
                for k, v in col_mapping.items():
                    if v:
                        mapped_lines.append(f"**{k}** ← {v}")
                    else:
                        mapped_lines.append(f"**{k}** ← (not found)")
                st.write(" | ".join(mapped_lines))
                
                # Manual override
                with st.expander("Manual column mapping override"):
                    for key in ['customer_code', 'sku', 'modifier', 'notes']:
                        options = ['(not mapped)'] + list(df.columns)
                        current = col_mapping.get(key, '')
                        idx = options.index(current) if current in options else 0
                        selected = st.selectbox(f"Map '{key}' to:", options, index=idx, key=f"cust_map_{key}")
                        col_mapping[key] = None if selected == '(not mapped)' else selected
                
                if st.button("Confirm Import Modifier", type="primary"):
                    conn = get_connection()
                    cur = conn.cursor()
                    imported = 0
                    
                    for _, row in df.iterrows():
                        cc_col = col_mapping.get('customer_code')
                        sku_col = col_mapping.get('sku')
                        mod_col = col_mapping.get('modifier')
                        notes_col = col_mapping.get('notes')
                        
                        cust_val = str(row[cc_col]).strip() if cc_col and cc_col in row else ''
                        sku_val = str(row[sku_col]).strip() if sku_col and sku_col in row else ''
                        
                        if not cust_val or not sku_val:
                            continue
                        
                        cur.execute("SELECT id FROM ecoer_customers WHERE customer_code = ?", (cust_val,))
                        cust = cur.fetchone()
                        
                        # Try SKU or model number
                        prod = None
                        if sku_val:
                            cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (sku_val,))
                            prod = cur.fetchone()
                            if not prod:
                                cur.execute("SELECT id FROM ecoer_products WHERE model_number = ?", (sku_val,))
                                prod = cur.fetchone()
                                if not prod:
                                    sku_clean = sku_val.replace('ABA', '').strip()
                                    cur.execute("SELECT id FROM ecoer_products WHERE sku = ?", (sku_clean,))
                                    prod = cur.fetchone()
                        
                        if cust and prod:
                            mod_val = float(row[mod_col]) if mod_col and mod_col in row else 1.0
                            notes_val = str(row[notes_col]) if notes_col and notes_col in row else ''
                            cur.execute("""
                                INSERT OR REPLACE INTO ecoer_customer_product_modifiers
                                (customer_id, product_id, modifier, notes)
                                VALUES (?, ?, ?, ?)
                            """, (cust[0], prod[0], mod_val, notes_val))
                            imported += 1
                    
                    conn.commit()
                    conn.close()
                    st.success(f"Successfully imported {imported} modifiers!")
                    st.balloons()
            except Exception as e:
                st.error(f"Import failed: {e}")
