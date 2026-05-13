# -*- coding: utf-8 -*-
"""
Ecoer Price Intelligence - Streamlit Web界面
"""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import sys

# 添加scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from parse_excel import PriceExtractor
from parse_pdf import PDFExtractor

DB_PATH = Path(__file__).parent.parent / "data" / "ecoer_prices.db"

st.set_page_config(
    page_title="Ecoer价格情报系统",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Ecoer价格情报系统")
st.markdown("**Ecoer Pricing Intelligence System**")

# 侧边栏导航
page = st.sidebar.radio("导航", ["📤 数据上传", "🔍 数据查询", "📊 价格分析", "💰 价格查询", "⚙️ 设置"])

# 导入分析模块
from analysis import (
    render_price_analysis_page,
    load_price_data,
    get_brand_stats,
    get_state_price_summary
)

# 数据库连接
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def load_data(query: str, params: list = None) -> pd.DataFrame:
    """Load data from database using cached connection"""
    conn = get_connection()
    if params:
        df = pd.read_sql(query, conn, params=params)
    else:
        df = pd.read_sql(query, conn)
    # Don't close - connection is cached
    return df

# ==================== 数据上传页面 ====================
if page == "📤 数据上传":
    st.header("📤 上传价格数据文件")
    
    # 元数据输入
    st.subheader("📝 数据来源信息")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 价格时间
        import datetime
        price_date = st.date_input(
            "价格日期",
            value=datetime.date.today(),
            help="这份报价的日期"
        )
    
    with col2:
        # 美国州份
        us_states = [
            "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
            "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
            "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
            "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
            "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
            "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
            "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
            "Wisconsin", "Wyoming", "District of Columbia"
        ]
        selected_state = st.selectbox("美国州份", ["请选择..."] + us_states)
    
    with col3:
        # 渠道来源
        source_options = ["请选择...", "Johnstone Supply", "Green Earth HVAC", "Goodman/Daikin", "其他经销商"]
        selected_source = st.selectbox("渠道来源", source_options)
        if selected_source == "其他经销商":
            custom_source = st.text_input("请输入渠道名称", placeholder="例如: ABC HVAC Supply")
        else:
            custom_source = None
    
    st.markdown("---")
    
    uploaded_file = st.file_uploader(
        "选择Excel或PDF文件",
        type=['xlsx', 'xls', 'pdf'],
        help="支持Excel(.xlsx, .xls)和PDF文件"
    )
    
    if uploaded_file:
        # 保存文件
        save_path = Path(__file__).parent.parent / "data" / uploaded_file.name
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ 文件已保存: {save_path}")
        
        # 根据文件类型处理
        if uploaded_file.name.endswith('.pdf'):
            st.info("📄 正在处理PDF文件...")
            extractor = PDFExtractor()
            result = extractor.process_pdf(str(save_path))
        else:
            st.info("📊 正在处理Excel文件...")
            extractor = PriceExtractor()
            result = extractor.process_excel(str(save_path))
        
        # 显示结果
        st.subheader("📊 处理结果")
        col1, col2, col3 = st.columns(3)
        col1.metric("总行数", result.get('total_rows', result.get('total_pages', 0)))
        col2.metric("提取记录", result.get('extracted_records', 0))
        
        errors_count = len(result.get('errors', []))
        if errors_count > 0:
            col3.metric("警告数", errors_count, delta="⚠️")
        else:
            col3.metric("警告数", 0)
        
        # 显示预览
        if result.get('records'):
            st.subheader("📋 数据预览")
            df_preview = pd.DataFrame(result['records'][:10])
            st.dataframe(df_preview, use_container_width=True)
            
            # 保存到数据库
            if st.button("💾 保存到数据库"):
                # 验证元数据
                if selected_state == "请选择...":
                    st.error("❌ 请选择美国州份")
                elif selected_source == "请选择...":
                    st.error("❌ 请选择渠道来源")
                elif selected_source == "其他经销商" and not custom_source:
                    st.error("❌ 请输入渠道名称")
                else:
                    # 获取地区ID
                    conn = get_connection()
                    region_result = conn.execute(
                        "SELECT id FROM regions WHERE state = ?", 
                        (selected_state,)
                    ).fetchone()
                    
                    if not region_result:
                        # 自动创建地区
                        cursor = conn.execute(
                            "INSERT INTO regions (name, state) VALUES (?, ?)",
                            (selected_state, selected_state)
                        )
                        region_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    else:
                        region_id = region_result[0]
                    
                    # 构建metadata
                    source_name = custom_source if selected_source == "其他经销商" else selected_source
                    metadata = {
                        'region_id': region_id,
                        'quote_date': str(price_date),
                        'source_name': source_name
                    }
                    
                    # 保存数据
                    if uploaded_file.name.endswith('.pdf'):
                        saved = extractor.save_to_database(result['records'], metadata)
                    else:
                        saved = extractor.save_to_database(result['records'], metadata)
                    
                    st.success(f"✅ 已保存 {saved} 条记录到数据库！")
                    st.success(f"📍 {selected_state} | 📅 {price_date} | 📤 {source_name}")
                    st.cache_resource.clear()
        
        # 显示错误
        if result.get('errors'):
            with st.expander("⚠️ 查看处理警告"):
                for err in result['errors']:
                    st.write(f"- {err}")

# ==================== 数据查询页面 ====================
elif page == "🔍 数据查询":
    st.header("🔍 查询价格数据")
    
    # 筛选条件
    col1, col2, col3 = st.columns(3)
    
    with col1:
        brands = load_data("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL ORDER BY brand")
        selected_brand = st.selectbox("品牌", ["全部"] + brands['brand'].tolist())
    
    with col2:
        categories = load_data("SELECT * FROM categories")
        selected_category = st.selectbox("品类", ["全部"] + categories['name'].tolist())
    
    with col3:
        regions = load_data("SELECT * FROM regions")
        selected_region = st.selectbox("地区", ["全部"] + regions['name'].tolist())
    
    # 构建查询
    query = """
        SELECT 
            p.brand,
            p.model_number,
            c.name as category,
            p.capacity_tons,
            p.efficiency_seer,
            pq.price,
            r.name as region,
            r.state,
            pq.quote_date,
            pq.source_type
        FROM price_quotes pq
        JOIN products p ON pq.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN regions r ON pq.region_id = r.id
        WHERE 1=1
    """
    
    params = []
    if selected_brand != "全部":
        query += " AND p.brand = ?"
        params.append(selected_brand)
    if selected_category != "全部":
        query += " AND c.name = ?"
        params.append(selected_category)
    if selected_region != "全部":
        query += " AND r.name = ?"
        params.append(selected_region)
    
    query += " ORDER BY pq.quote_date DESC, p.brand"
    
    # 执行查询
    if params:
        df = load_data(query, params)
    else:
        df = load_data(query)
    
    # 显示统计
    st.subheader(f"📊 查询结果 ({len(df)} 条记录)")
    
    if not df.empty:
        # 价格统计
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("记录数", len(df))
        col2.metric("平均价格", f"${df['price'].mean():,.0f}")
        col3.metric("最低价格", f"${df['price'].min():,.0f}")
        col4.metric("最高价格", f"${df['price'].max():,.0f}")
        
        # 数据表格
        st.dataframe(
            df.sort_values('price', ascending=False),
            use_container_width=True,
            height=500
        )
        
        # 导出CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 导出CSV",
            csv,
            "price_quotes.csv",
            "text/csv"
        )
    else:
        st.info("暂无数据，请先上传价格文件")

# ==================== 价格分析页面 ====================
elif page == "📊 价格分析":
    render_price_analysis_page()

# ==================== 价格查询页面 ====================
elif page == "💰 价格查询":
    from ecoer_pricing_tool import render_pricing_tool
    render_pricing_tool()

# ==================== 设置页面 ====================
elif page == "⚙️ 设置":
    st.header("⚙️ 系统设置")
    
    # 初始化数据库
    st.subheader("数据库管理")
    
    if st.button("🔄 初始化数据库"):
        from init_db import init_database
        init_database()
        st.success("✅ 数据库初始化完成！")
        st.cache_resource.clear()
    
    # 查看数据库状态
    st.subheader("📊 数据库状态")
    
    try:
        conn = get_connection()
        
        tables = pd.read_sql("""
            SELECT 
                'products' as table_name, COUNT(*) as count FROM products
            UNION ALL
            SELECT 'price_quotes', COUNT(*) FROM price_quotes
            UNION ALL
            SELECT 'regions', COUNT(*) FROM regions
        """, conn)
        
        st.dataframe(tables, use_container_width=True)
        
        conn.close()
    except Exception as e:
        st.error(f"数据库错误: {e}")
        st.info("请先初始化数据库")

# ==================== 侧边栏信息 ====================
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ 系统信息")
st.sidebar.markdown(f"""
- **数据库**: `{DB_PATH.name}`
- **版本**: v1.0.0
""")

st.sidebar.markdown("### 📝 使用说明")
st.sidebar.markdown("""
1. **上传数据**: 支持Excel/PDF文件
2. **查询数据**: 按品牌/品类/地区筛选
3. **分析报表**: 查看价格对比分析
4. **设置**: 管理数据库
""")
