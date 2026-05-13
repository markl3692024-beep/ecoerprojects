"""
Ecoer 统一入口 - 主页
"""
import streamlit as st

st.set_page_config(
    page_title="Ecoer Systems",
    page_icon="🏠",
    layout="centered"
)

st.title("🏠 Ecoer 系统入口")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📊 价格情报系统")
    st.markdown("""
    **功能**:
    - 上传竞品价格文件
    - 分析 Bryant/Goodman 等竞品
    - Apple-to-Apple 对比
    - 区域价格差异分析
    
    **数据**: 导入的外部价格数据
    """)
    if st.button("进入价格情报系统 →", use_container_width=True, type="primary"):
        st.switch_page("pages/intelligence.py")

with col2:
    st.markdown("### 💰 价格查询系统")
    st.markdown("""
    **功能**:
    - 查询 Ecoer 产品价格
    - 按客户/区域筛选
    - List Price × Multiplier
    - 散件价格查询
    
    **数据**: 管理员录入的 Ecoer 数据
    """)
    if st.button("进入价格查询系统 →", use_container_width=True, type="primary"):
        st.switch_page("pages/pricing.py")

st.markdown("---")
st.caption("Ecoer Price Intelligence & Pricing System v1.0")
