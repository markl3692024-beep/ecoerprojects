"""
Ecoer 价格情报系统 - 竞品分析模块
"""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from parse_excel import PriceExtractor
from parse_pdf import PDFExtractor

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'ecoer_prices.db'

def get_connection():
    return sqlite3.connect(str(DB_PATH))

st.set_page_config(
    page_title="价格情报系统",
    page_icon="📊",
    layout="wide"
)

# 返回主页按钮
if st.sidebar.button("← 返回主页"):
    st.switch_page("home.py")

st.title("📊 Ecoer 价格情报系统")
st.markdown("**竞品价格分析与对比**")
st.markdown("---")

# 侧边栏导航
page = st.sidebar.radio("功能菜单", ["📤 数据上传", "🔍 数据查询", "📊 价格分析", "⚙️ 系统设置"])

# ==================== 数据上传页面 ====================
if page == "📤 数据上传":
    st.header("📤 上传价格数据")
    
    uploaded_file = st.file_uploader("选择文件", type=['xlsx', 'xls', 'pdf'])
    
    if uploaded_file:
        st.success(f"已选择: {uploaded_file.name}")
        
        col1, col2 = st.columns(2)
        with col1:
            brand = st.text_input("品牌名称", placeholder="如: Bryant, Goodman")
            region = st.text_input("地区", placeholder="如: TX, NY")
        with col2:
            source = st.text_input("数据来源", placeholder="如: Johnstone Supply")
            date = st.date_input("报价日期")
        
        if st.button("开始解析并导入", type="primary"):
            with st.spinner("解析中..."):
                if uploaded_file.name.endswith('.pdf'):
                    extractor = PDFExtractor()
                    data = extractor.extract(uploaded_file)
                else:
                    extractor = PriceExtractor()
                    data = extractor.extract(uploaded_file)
                
                st.success(f"解析完成！找到 {len(data)} 条记录")
                st.dataframe(data.head(10))

# ==================== 数据查询页面 ====================
elif page == "🔍 数据查询":
    st.header("🔍 查询价格数据")
    
    try:
        conn = get_connection()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            brands = pd.read_sql("SELECT DISTINCT brand FROM products ORDER BY brand", conn)
            brand = st.selectbox("品牌", ['全部'] + brands['brand'].tolist())
        with col2:
            cats = pd.read_sql("SELECT DISTINCT category FROM products ORDER BY category", conn)
            category = st.selectbox("品类", ['全部'] + cats['category'].tolist())
        with col3:
            search = st.text_input("搜索型号")
        
        query = """
            SELECT p.brand, p.model, p.category, p.capacity_btu, p.seer, 
                   pq.price, pq.price_type, r.state, pq.quote_date
            FROM products p
            JOIN price_quotes pq ON p.id = pq.product_id
            LEFT JOIN regions r ON pq.region_id = r.id
            WHERE 1=1
        """
        params = []
        if brand != '全部':
            query += " AND p.brand = ?"
            params.append(brand)
        if category != '全部':
            query += " AND p.category = ?"
            params.append(category)
        if search:
            query += " AND p.model LIKE ?"
            params.append(f'%{search}%')
        
        df = pd.read_sql(query, conn, params=params)
        st.dataframe(df, use_container_width=True)
        st.caption(f"共 {len(df)} 条记录")
        
        conn.close()
    except Exception as e:
        st.error(f"数据库错误: {e}")
        st.info("请先上传数据")

# ==================== 价格分析页面 ====================
elif page == "📊 价格分析":
    st.header("📊 价格分析")
    
    try:
        conn = get_connection()
        
        # 品牌对比
        st.subheader("品牌价格对比")
        brand_prices = pd.read_sql("""
            SELECT p.brand, AVG(pq.price) as avg_price, COUNT(*) as count
            FROM products p
            JOIN price_quotes pq ON p.id = pq.product_id
            GROUP BY p.brand
            ORDER BY avg_price DESC
        """, conn)
        
        st.bar_chart(brand_prices.set_index('brand')['avg_price'])
        
        # Ecoer 对比
        st.subheader("Ecoer vs 竞品")
        ecoer = pd.read_sql("""
            SELECT p.category, p.model, pq.price
            FROM products p
            JOIN price_quotes pq ON p.id = pq.product_id
            WHERE p.brand = 'Ecoer'
        """, conn)
        
        if not ecoer.empty:
            st.dataframe(ecoer)
        else:
            st.info("暂无 Ecoer 数据")
        
        conn.close()
    except Exception as e:
        st.error(f"分析错误: {e}")

# ==================== 设置页面 ====================
elif page == "⚙️ 系统设置":
    st.header("⚙️ 系统设置")
    
    st.subheader("数据库状态")
    try:
        conn = get_connection()
        stats = pd.read_sql("""
            SELECT 'products' as table_name, COUNT(*) as count FROM products
            UNION ALL
            SELECT 'price_quotes', COUNT(*) FROM price_quotes
            UNION ALL
            SELECT 'regions', COUNT(*) FROM regions
        """, conn)
        st.dataframe(stats, use_container_width=True)
        conn.close()
    except Exception as e:
        st.error(f"数据库错误: {e}")
