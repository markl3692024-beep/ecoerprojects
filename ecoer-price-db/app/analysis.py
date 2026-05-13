"""
价格分析模块 - Ecoer Price Intelligence System
提供多维度价格分析和定价建议
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

# 图表库
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json


def get_connection():
    """获取数据库连接"""
    db_path = Path(__file__).parent.parent / 'data' / 'ecoer_prices.db'
    return sqlite3.connect(str(db_path))


def load_price_data(filters=None):
    """加载价格数据"""
    conn = get_connection()
    
    query = """
        SELECT 
            p.id as product_id,
            p.brand,
            p.model_number,
            p.capacity_btuh,
            p.capacity_tons,
            p.efficiency_seer,
            p.efficiency_eer,
            c.name as category,
            pq.price,
            pq.quote_date,
            pq.source_name,
            r.name as region_name,
            r.state
        FROM price_quotes pq
        JOIN products p ON pq.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN regions r ON pq.region_id = r.id
        WHERE pq.price IS NOT NULL AND pq.price > 0
    """
    
    if filters:
        if filters.get('brand'):
            query += f" AND p.brand = '{filters['brand']}'"
        if filters.get('state'):
            query += f" AND r.state = '{filters['state']}'"
        if filters.get('category'):
            query += f" AND c.name = '{filters['category']}'"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df


def get_brand_stats():
    """获取品牌统计数据"""
    conn = get_connection()
    
    query = """
        SELECT 
            p.brand,
            COUNT(DISTINCT p.id) as product_count,
            COUNT(pq.id) as price_count,
            MIN(pq.price) as min_price,
            MAX(pq.price) as max_price,
            AVG(pq.price) as avg_price,
            MEDIAN(pq.price) as median_price,
            STDDEV(pq.price) as std_price
        FROM products p
        LEFT JOIN price_quotes pq ON p.id = pq.product_id AND pq.price > 0
        GROUP BY p.brand
        ORDER BY avg_price
    """
    
    try:
        df = pd.read_sql_query(query, conn)
    except:
        # MEDIAN might not be available in older SQLite
        query = query.replace('MEDIAN(pq.price)', 'AVG(pq.price) as median_price')
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df


def get_state_price_summary():
    """获取各州价格汇总"""
    conn = get_connection()
    
    query = """
        SELECT 
            r.state,
            r.name as region_name,
            COUNT(DISTINCT p.id) as product_count,
            COUNT(pq.id) as price_count,
            MIN(pq.price) as min_price,
            MAX(pq.price) as max_price,
            AVG(pq.price) as avg_price
        FROM price_quotes pq
        JOIN products p ON pq.product_id = p.id
        LEFT JOIN regions r ON pq.region_id = r.id
        WHERE pq.price > 0 AND r.state IS NOT NULL
        GROUP BY r.state
        ORDER BY avg_price DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_category_price_analysis():
    """获取品类价格分析"""
    conn = get_connection()
    
    query = """
        SELECT 
            c.name as category,
            p.brand,
            COUNT(pq.id) as price_count,
            MIN(pq.price) as min_price,
            MAX(pq.price) as max_price,
            AVG(pq.price) as avg_price
        FROM price_quotes pq
        JOIN products p ON pq.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE pq.price > 0
        GROUP BY c.name, p.brand
        ORDER BY c.name, avg_price
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_ecoer_competitive_analysis():
    """Ecoer竞争分析 - 对比同类产品的价格"""
    conn = get_connection()
    
    # 找出Ecoer产品的品类，然后找同类竞品
    query = """
        SELECT 
            p_ecoer.model_number as ecoer_model,
            p_ecoer.capacity_tons as ecoer_tons,
            p_ecoer.efficiency_seer as ecoer_seer,
            pq_ecoer.price as ecoer_price,
            p_competitor.brand as competitor_brand,
            p_competitor.model_number as competitor_model,
            p_competitor.capacity_tons as competitor_tons,
            pq_competitor.price as competitor_price,
            ROUND((pq_competitor.price - pq_ecoer.price) / pq_ecoer.price * 100, 1) as price_diff_pct
        FROM price_quotes pq_ecoer
        JOIN products p_ecoer ON pq_ecoer.product_id = p_ecoer.id
        LEFT JOIN categories c ON p_ecoer.category_id = c.id
        LEFT JOIN price_quotes pq_competitor ON c.id = (
            SELECT p2.category_id FROM products p2 WHERE p2.id = pq_competitor.product_id
            AND p2.brand != 'Ecoer'
            LIMIT 1
        )
        LEFT JOIN products p_competitor ON pq_competitor.product_id = p_competitor.id
        WHERE p_ecoer.brand = 'Ecoer' 
        AND pq_ecoer.price > 0
        AND pq_competitor.price > 0
        AND p_competitor.brand IS NOT NULL
    """
    
    # 简化版：分别获取Ecoer和竞品数据
    ecoer_prices = pd.read_sql_query("""
        SELECT p.brand, p.model_number, p.capacity_tons, p.efficiency_seer, 
               p.capacity_btuh, pq.price, r.state
        FROM price_quotes pq
        JOIN products p ON pq.product_id = p.id
        LEFT JOIN regions r ON pq.region_id = r.id
        WHERE p.brand = 'Ecoer' AND pq.price > 0
    """, conn)
    
    competitor_prices = pd.read_sql_query("""
        SELECT p.brand, p.model_number, p.capacity_tons, p.efficiency_seer,
               p.capacity_btuh, pq.price, r.state
        FROM price_quotes pq
        JOIN products p ON pq.product_id = p.id
        LEFT JOIN regions r ON pq.region_id = r.id
        WHERE p.brand IN ('Bryant', 'Goodman', 'Payne', 'BOSCH') AND pq.price > 0
    """, conn)
    
    conn.close()
    
    return ecoer_prices, competitor_prices


def calculate_pricing_recommendations(df, target_brand='Ecoer'):
    """计算定价建议"""
    if df.empty:
        return None
    
    # 按品牌分组计算统计数据
    brand_stats = df.groupby('brand').agg({
        'price': ['count', 'min', 'max', 'mean', 'median', 'std']
    }).round(2)
    
    brand_stats.columns = ['count', 'min', 'max', 'mean', 'median', 'std']
    brand_stats = brand_stats.reset_index()
    
    # 计算Ecoer相对于市场的位置
    if target_brand in brand_stats['brand'].values:
        ecoer_data = brand_stats[brand_stats['brand'] == target_brand].iloc[0]
        
        # 市场平均价格（不含Ecoer）
        market_avg = brand_stats[brand_stats['brand'] != target_brand]['mean'].mean()
        market_median = brand_stats[brand_stats['brand'] != target_brand]['median'].median()
        
        # 竞品平均价格
        competitor_avg = brand_stats[brand_stats['brand'] != target_brand]['mean'].mean()
        
        return {
            'ecoer_avg': ecoer_data['mean'],
            'ecoer_median': ecoer_data['median'],
            'market_avg': market_avg,
            'market_median': market_median,
            'competitor_avg': competitor_avg,
            'premium_pct': ((ecoer_data['mean'] - market_avg) / market_avg * 100) if market_avg else 0,
            'brand_stats': brand_stats
        }
    
    return None


def render_price_analysis_page():
    """渲染价格分析页面"""
    st.header("📊 价格分析")
    
    # 加载数据
    df = load_price_data()
    brand_stats = get_brand_stats()
    state_stats = get_state_price_summary()
    category_stats = get_category_price_analysis()
    
    # 品牌筛选
    st.subheader("🔍 筛选条件")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_brand = st.selectbox(
            "选择品牌",
            ["全部"] + df['brand'].dropna().unique().tolist()
        )
    
    with col2:
        if 'state' in df.columns and df['state'].notna().any():
            states = df['state'].dropna().unique().tolist()
            selected_state = st.selectbox("选择州", ["全部"] + states)
        else:
            selected_state = "全部"
            st.info("暂无地区数据")
    
    with col3:
        if 'category' in df.columns and df['category'].notna().any():
            categories = df['category'].dropna().unique().tolist()
            selected_category = st.selectbox("选择品类", ["全部"] + categories)
        else:
            selected_category = "全部"
    
    # 应用筛选
    filters = {}
    if selected_brand != "全部":
        filters['brand'] = selected_brand
    if selected_state != "全部":
        filters['state'] = selected_state
    if selected_category != "全部":
        filters['category'] = selected_category
    
    filtered_df = load_price_data(filters) if filters else df
    
    # ==================== 标签页 ====================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 概览仪表盘",
        "🗺️ 区域分析", 
        "🎯 竞争定位",
        "🍎 Apple-to-Apple对比",
        "💡 定价建议"
    ])
    
    with tab1:
        render_dashboard_tab(df, filtered_df, brand_stats)
    
    with tab2:
        render_regional_tab(df, state_stats)
    
    with tab3:
        render_competitive_tab(df)
    
    with tab4:
        render_apple_to_apple_tab(df)
    
    with tab5:
        render_pricing_recommendation_tab(df, brand_stats)


def render_dashboard_tab(df, filtered_df, brand_stats):
    """概览仪表盘"""
    st.subheader("📈 价格概览")
    
    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    
    total_products = filtered_df['product_id'].nunique()
    total_quotes = len(filtered_df)
    avg_price = filtered_df['price'].mean()
    price_range = filtered_df['price'].max() - filtered_df['price'].min()
    
    col1.metric("产品数量", f"{total_products:,}")
    col2.metric("价格记录", f"{total_quotes:,}")
    col3.metric("平均价格", f"${avg_price:,.0f}")
    col4.metric("价格跨度", f"${price_range:,.0f}")
    
    st.markdown("---")
    
    # 图表区域
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 品牌价格分布")
        if not brand_stats.empty:
            fig = px.box(
                df[df['price'].notna()],
                x='brand',
                y='price',
                color='brand',
                title="各品牌价格分布",
                labels={'price': '价格 ($)', 'brand': '品牌'}
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 品牌平均价格对比")
        if not brand_stats.empty:
            fig = px.bar(
                brand_stats,
                x='brand',
                y='avg_price',
                color='brand',
                error_y='std_price' if 'std_price' in brand_stats.columns else None,
                title="品牌平均价格（含标准差）",
                labels={'avg_price': '平均价格 ($)', 'brand': '品牌'}
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 品类价格分析
    st.subheader("📦 品类价格分析")
    if not category_stats.empty and 'category' in filtered_df.columns:
        fig = px.box(
            filtered_df[filtered_df['category'].notna()],
            x='category',
            y='price',
            color='brand',
            title="各品类价格分布（按品牌）",
            labels={'price': '价格 ($)', 'category': '品类'}
        )
        fig.update_layout(
            height=400,
            xaxis_tickangle=-45,
            template='plotly_white'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 价格分布直方图
    st.subheader("📉 价格分布直方图")
    fig = px.histogram(
        df[df['price'].notna() & (df['price'] < df['price'].quantile(0.95))],
        x='price',
        nbins=50,
        color='brand',
        title="价格分布（排除顶部5%异常值）",
        labels={'price': '价格 ($)', 'count': '数量'}
    )
    fig.update_layout(
        height=350,
        template='plotly_white',
        barmode='overlay'
    )
    fig.update_traces(opacity=0.7)
    st.plotly_chart(fig, use_container_width=True)


def render_regional_tab(df, state_stats):
    """区域分析"""
    st.subheader("🗺️ 区域价格分析")
    
    # 区域汇总
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 各州价格汇总")
        if not state_stats.empty:
            # 格式化显示
            display_df = state_stats.copy()
            display_df['avg_price'] = display_df['avg_price'].apply(lambda x: f"${x:,.0f}")
            display_df['min_price'] = display_df['min_price'].apply(lambda x: f"${x:,.0f}")
            display_df['max_price'] = display_df['max_price'].apply(lambda x: f"${x:,.0f}")
            display_df.columns = ['州', '地区名', '产品数', '报价数', '最低价', '最高价', '平均价']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无区域数据")
    
    with col2:
        st.markdown("#### 各州平均价格对比")
        if not state_stats.empty:
            fig = px.bar(
                state_stats.sort_values('avg_price', ascending=True),
                x='state',
                y='avg_price',
                color='avg_price',
                title="各州平均价格",
                labels={'avg_price': '平均价格 ($)', 'state': '州'}
            )
            fig.update_layout(
                height=350,
                template='plotly_white',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # 区域 vs 品牌热力图
    if 'state' in df.columns:
        st.markdown("#### 🗺️ 品牌-区域价格热力图")
        
        # 创建透视表
        pivot_df = df.pivot_table(
            values='price',
            index='brand',
            columns='state',
            aggfunc='mean'
        ).round(0)
        
        if not pivot_df.empty:
            fig = px.imshow(
                pivot_df,
                labels=dict(x="州", y="品牌", color="平均价格 ($)"),
                title="品牌-区域平均价格热力图",
                text_auto=True,
                aspect='auto'
            )
            fig.update_layout(height=400, template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)


def render_competitive_tab(df):
    """竞争定位分析"""
    st.subheader("🎯 Ecoer竞争定位分析")
    
    # 获取Ecoer和竞品数据
    ecoer_df = df[df['brand'] == 'Ecoer']
    competitor_df = df[df['brand'].isin(['Bryant', 'Goodman', 'Payne', 'BOSCH'])]
    
    if ecoer_df.empty:
        st.warning("暂无Ecoer产品数据")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Ecoer vs 竞品价格范围")
        
        # 箱线图对比
        compare_df = df[df['brand'].isin(['Ecoer', 'Bryant', 'Goodman', 'BOSCH'])]
        if not compare_df.empty:
            fig = px.box(
                compare_df,
                x='brand',
                y='price',
                color='brand',
                title="价格区间对比",
                labels={'price': '价格 ($)', 'brand': '品牌'}
            )
            fig.update_layout(
                height=400,
                showlegend=False,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 价格区间分布")
        
        # 计算各品牌的价格区间
        price_ranges = df.groupby('brand').agg({
            'price': ['min', 'max', 'mean', 'median', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]
        }).round(2)
        price_ranges.columns = ['min', 'max', 'mean', 'median', 'q25', 'q75']
        price_ranges = price_ranges.reset_index()
        
        # 绘制价格区间图
        fig = go.Figure()
        
        for _, row in price_ranges.iterrows():
            # 中位数点
            fig.add_trace(go.Scatter(
                x=[row['brand']],
                y=[row['median']],
                mode='markers',
                marker=dict(size=15, color='red'),
                name=f"{row['brand']} 中位数"
            ))
            
            # 范围线
            fig.add_trace(go.Scatter(
                x=[row['brand'], row['brand']],
                y=[row['min'], row['max']],
                mode='lines',
                line=dict(color='blue', width=3),
                name=f"{row['brand']} 范围"
            ))
            
            # IQR框
            fig.add_trace(go.Scatter(
                x=[row['brand'], row['brand'], row['brand'], row['brand']],
                y=[row['q25'], row['q75'], row['q75'], row['q25']],
                mode='lines',
                fill='toself',
                fillcolor='rgba(0,100,255,0.2)',
                line=dict(color='rgba(0,100,255,0.5)'),
                name=f"{row['brand']} IQR"
            ))
        
        fig.update_layout(
            title="品牌价格区间对比",
            yaxis_title="价格 ($)",
            height=400,
            template='plotly_white',
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 散点图：容量 vs 价格
    st.markdown("#### 📊 容量-价格关系图")
    
    scatter_df = df[df['capacity_tons'].notna()].copy()
    if not scatter_df.empty:
        fig = px.scatter(
            scatter_df[scatter_df['price'] < scatter_df['price'].quantile(0.95)],
            x='capacity_tons',
            y='price',
            color='brand',
            size='efficiency_seer' if 'efficiency_seer' in scatter_df.columns else None,
            hover_data=['model_number', 'price'],
            title="产品容量 vs 价格（气泡大小=能效比）",
            labels={
                'capacity_tons': '容量（吨）',
                'price': '价格 ($)',
                'brand': '品牌',
                'efficiency_seer': 'SEER'
            }
        )
        fig.update_layout(
            height=450,
            template='plotly_white'
        )
        st.plotly_chart(fig, use_container_width=True)


def render_pricing_recommendation_tab(df, brand_stats):
    """定价建议"""
    st.subheader("💡 Ecoer定价建议")
    
    ecoer_df = df[df['brand'] == 'Ecoer']
    competitor_df = df[df['brand'].isin(['Bryant', 'Goodman', 'Payne', 'BOSCH'])]
    
    if ecoer_df.empty:
        st.warning("暂无Ecoer产品数据，无法提供定价建议")
        return
    
    # 计算市场基准
    market_avg = competitor_df['price'].mean()
    market_median = competitor_df['price'].median()
    ecoer_avg = ecoer_df['price'].mean()
    
    # 计算分位数
    p25 = competitor_df['price'].quantile(0.25)
    p75 = competitor_df['price'].quantile(0.75)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("竞品均价", f"${market_avg:,.0f}")
    col2.metric("竞品中位数", f"${market_median:,.0f}")
    col3.metric("Ecoer当前均价", f"${ecoer_avg:,.0f}")
    
    st.markdown("---")
    
    # 定价区间可视化
    st.markdown("#### 🎯 推荐定价区间")
    
    # 计算推荐价格
    premium_options = st.radio(
        "选择定价策略",
        options=['保守 (平价)', '适中 (+5%)', '进取 (+10%)', '高端 (+15%)'],
        horizontal=True
    )
    
    premium_map = {
        '保守 (平价)': 0,
        '适中 (+5%)': 0.05,
        '进取 (+10%)': 0.10,
        '高端 (+15%)': 0.15
    }
    
    premium = premium_map[premium_options]
    
    # 推荐价格区间
    budget_price = market_median * (1 - 0.10)  # 比市场低10%
    mid_price = market_median * (1 + premium)
    premium_price = p75 * (1 + premium)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💚 入门价格", f"${budget_price:,.0f}", 
                delta=f"比Ecoer当前低${ecoer_avg-budget_price:,.0f}")
    col2.metric("💙 标准价格", f"${mid_price:,.0f}",
                delta=f"比Ecoer当前{'高' if mid_price > ecoer_avg else '低'}${abs(mid_price-ecoer_avg):,.0f}")
    col3.metric("💜 高端价格", f"${premium_price:,.0f}",
                delta=f"比Ecoer当前{'高' if premium_price > ecoer_avg else '低'}${abs(premium_price-ecoer_avg):,.0f}")
    
    # 定价区间图
    fig = go.Figure()
    
    # 市场区间
    fig.add_shape(
        type="rect", x0=0, x1=1, y0=p25, y1=p75,
        fillcolor="lightblue", opacity=0.5,
        line=dict(width=0)
    )
    fig.add_annotation(x=0.5, y=(p25+p75)/2, text="市场IQR", showarrow=False)
    
    # 市场均价线
    fig.add_hline(y=market_avg, line_dash="dash", line_color="blue", 
                  annotation_text=f"市场均价 ${market_avg:,.0f}")
    
    # Ecoer当前价格
    fig.add_hline(y=ecoer_avg, line_dash="dash", line_color="red",
                  annotation_text=f"Ecoer当前 $${ecoer_avg:,.0f}")
    
    # 推荐区间
    fig.add_hrect(y0=budget_price, y1=premium_price, 
                  fillcolor="green", opacity=0.2,
                  annotation_text="推荐区间")
    
    fig.update_layout(
        title="Ecoer定价位置分析",
        yaxis_title="价格 ($)",
        height=400,
        template='plotly_white',
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 详细分析表格
    st.markdown("#### 📋 详细品类定价建议")
    
    if 'category' in df.columns and not df['category'].isna().all():
        category_analysis = []
        
        for category in df['category'].dropna().unique():
            cat_ecoer = df[(df['brand'] == 'Ecoer') & (df['category'] == category)]
            cat_competitor = df[(df['brand'] != 'Ecoer') & (df['category'] == category)]
            
            if not cat_ecoer.empty and not cat_competitor.empty:
                ecoer_avg_cat = cat_ecoer['price'].mean()
                comp_avg_cat = cat_competitor['price'].mean()
                
                category_analysis.append({
                    '品类': category,
                    'Ecoer均价': f"${ecoer_avg_cat:,.0f}",
                    '竞品均价': f"${comp_avg_cat:,.0f}",
                    '价差': f"{(ecoer_avg_cat/comp_avg_cat-1)*100:+.1f}%",
                    '建议价格': f"${comp_avg_cat*(1+premium):,.0f}",
                    '建议策略': '提价' if ecoer_avg_cat < comp_avg_cat else '保持'
                })
        
        if category_analysis:
            analysis_df = pd.DataFrame(category_analysis)
            st.dataframe(analysis_df, use_container_width=True, hide_index=True)
    
    # 总结建议
    st.markdown("---")
    st.markdown("#### 📝 综合建议")
    
    ecoer_premium = (ecoer_avg / market_avg - 1) * 100 if market_avg else 0
    
    if ecoer_premium < -10:
        suggestion = "💡 **建议**: Ecoer当前价格低于市场均价10%以上，建议适当提价以提升品牌形象。"
    elif ecoer_premium < 0:
        suggestion = "💡 **建议**: Ecoer价格略低于市场均价，可以考虑小幅提价（+5%）测试市场反应。"
    elif ecoer_premium < 10:
        suggestion = "💡 **建议**: Ecoer价格与市场基本持平，建议保持当前价格策略，侧重差异化竞争。"
    else:
        suggestion = "💡 **建议**: Ecoer价格高于市场均价，需要确保产品差异化价值支撑溢价。"
    
    st.info(suggestion)
    
    # 区域定价差异建议
    if 'state' in df.columns and not df['state'].isna().all():
        st.markdown("#### 🗺️ 区域差异化定价建议")
        
        state_analysis = []
        for state in df['state'].dropna().unique():
            state_comp = df[(df['brand'] != 'Ecoer') & (df['state'] == state)]
            if not state_comp.empty:
                state_avg = state_comp['price'].mean()
                state_analysis.append({
                    '州': state,
                    '市场均价': f"${state_avg:,.0f}",
                    '建议价': f"${state_avg*(1+premium):,.0f}",
                    '区域特点': '高价州' if state_avg > market_avg else '低价州'
                })
        
        if state_analysis:
            state_df = pd.DataFrame(state_analysis)
            st.dataframe(state_df, use_container_width=True, hide_index=True)


def get_capacity_tier(tons):
    """将容量转换为容量段"""
    if pd.isna(tons):
        return 'Unknown'
    if tons <= 2:
        return '≤2 Ton'
    elif tons <= 3:
        return '2-3 Ton'
    elif tons <= 4:
        return '3-4 Ton'
    elif tons <= 5:
        return '4-5 Ton'
    else:
        return '>5 Ton'


def get_seer_tier(seer):
    """将SEER转换为能效段"""
    if pd.isna(seer):
        return 'Unknown'
    if seer <= 14:
        return 'SEER ≤14'
    elif seer <= 16:
        return 'SEER 15-16'
    elif seer <= 18:
        return 'SEER 17-18'
    elif seer <= 20:
        return 'SEER 19-20'
    else:
        return 'SEER >20'


def render_apple_to_apple_tab(df):
    """Apple-to-Apple 同级别对比"""
    st.subheader("🍎 Apple-to-Apple 同级别对比")
    st.markdown("""
    按**品类 + 容量段 + 能效段**进行同级别对比，确保比较的是同类产品。
    """)
    
    # 添加容量段和能效段列
    df['capacity_tier'] = df['capacity_tons'].apply(get_capacity_tier)
    df['seer_tier'] = df['efficiency_seer'].apply(get_seer_tier)
    
    # 筛选有完整数据的记录
    df_valid = df[df['capacity_tons'].notna() & df['efficiency_seer'].notna() & df['price'].notna()]
    
    if df_valid.empty:
        st.warning("⚠️ 数据不足，无法进行 Apple-to-Apple 对比。需要产品具备容量(tons)和能效(SEER)数据。")
        return
    
    # 筛选条件
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = df_valid['category'].dropna().unique().tolist()
        selected_cat = st.selectbox("选择品类", ["全部"] + sorted(categories), key="a2a_cat")
    
    with col2:
        cap_tiers = df_valid['capacity_tier'].unique().tolist()
        selected_cap = st.selectbox("选择容量段", ["全部"] + sorted(cap_tiers), key="a2a_cap")
    
    with col3:
        seer_tiers = df_valid['seer_tier'].unique().tolist()
        selected_seer = st.selectbox("选择能效段", ["全部"] + sorted(seer_tiers), key="a2a_seer")
    
    # 应用筛选
    filtered = df_valid.copy()
    if selected_cat != "全部":
        filtered = filtered[filtered['category'] == selected_cat]
    if selected_cap != "全部":
        filtered = filtered[filtered['capacity_tier'] == selected_cap]
    if selected_seer != "全部":
        filtered = filtered[filtered['seer_tier'] == selected_seer]
    
    if filtered.empty:
        st.info("ℹ️ 当前筛选条件下无数据，请调整筛选条件。")
        return
    
    # 显示筛选结果统计
    st.markdown("---")
    st.markdown(f"**当前筛选**: 品类={selected_cat}, 容量={selected_cap}, 能效={selected_seer}")
    st.markdown(f"**匹配记录**: {len(filtered)} 条价格记录，{filtered['product_id'].nunique()} 个产品")
    
    # 品牌对比表格
    st.markdown("#### 📊 品牌价格对比")
    
    brand_comparison = filtered.groupby('brand').agg({
        'price': ['count', 'mean', 'median', 'min', 'max', 'std']
    }).round(2)
    brand_comparison.columns = ['记录数', '均价', '中位数', '最低价', '最高价', '标准差']
    brand_comparison = brand_comparison.reset_index()
    brand_comparison = brand_comparison.sort_values('均价', ascending=False)
    
    st.dataframe(brand_comparison, use_container_width=True, hide_index=True)
    
    # 可视化对比
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 品牌均价对比")
        fig = px.bar(
            brand_comparison,
            x='brand',
            y='均价',
            color='brand',
            text='均价',
            title=f"{selected_cat} - {selected_cap} - {selected_seer}",
            labels={'均价': '平均价格 ($)', 'brand': '品牌'}
        )
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig.update_layout(showlegend=False, height=400, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📦 价格分布箱线图")
        fig = px.box(
            filtered,
            x='brand',
            y='price',
            color='brand',
            title="价格分布对比",
            labels={'price': '价格 ($)', 'brand': '品牌'}
        )
        fig.update_layout(showlegend=False, height=400, template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)
    
    # Ecoer 定位分析
    if 'Ecoer' in filtered['brand'].values:
        st.markdown("---")
        st.markdown("#### 🎯 Ecoer 竞争定位")
        
        ecoer_data = filtered[filtered['brand'] == 'Ecoer']
        comp_data = filtered[filtered['brand'] != 'Ecoer']
        
        if not comp_data.empty:
            ecoer_avg = ecoer_data['price'].mean()
            comp_avg = comp_data['price'].mean()
            comp_min = comp_data['price'].min()
            comp_max = comp_data['price'].max()
            
            gap_pct = ((ecoer_avg - comp_avg) / comp_avg * 100) if comp_avg else 0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Ecoer均价", f"${ecoer_avg:,.0f}")
            col2.metric("竞品均价", f"${comp_avg:,.0f}")
            col3.metric("价差", f"{gap_pct:+.1f}%")
            col4.metric("竞品区间", f"${comp_min:,.0f} - ${comp_max:,.0f}")
            
            # 定位图
            fig = go.Figure()
            
            # 竞品价格散点
            for brand in comp_data['brand'].unique():
                brand_data = comp_data[comp_data['brand'] == brand]
                fig.add_trace(go.Scatter(
                    x=brand_data['capacity_tons'],
                    y=brand_data['price'],
                    mode='markers',
                    name=brand,
                    marker=dict(size=10, opacity=0.6)
                ))
            
            # Ecoer价格
            fig.add_trace(go.Scatter(
                x=ecoer_data['capacity_tons'],
                y=ecoer_data['price'],
                mode='markers',
                name='Ecoer',
                marker=dict(size=15, color='red', symbol='star')
            ))
            
            fig.update_layout(
                title="容量-价格散点图（同级别对比）",
                xaxis_title="容量 (tons)",
                yaxis_title="价格 ($)",
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 定价建议
            if gap_pct < -15:
                st.success(f"💡 **建议**: Ecoer在该细分市场定价低于竞品{abs(gap_pct):.1f}%，有较大提价空间。建议价格区间: ${comp_avg*0.9:,.0f} - ${comp_avg*1.05:,.0f}")
            elif gap_pct < -5:
                st.info(f"💡 **建议**: Ecoer定价略低于竞品{abs(gap_pct):.1f}%，可考虑小幅提价(+5%~10%)。")
            elif gap_pct < 5:
                st.info(f"💡 **建议**: Ecoer定价与竞品基本持平，建议保持当前策略。")
            else:
                st.warning(f"💡 **建议**: Ecoer定价高于竞品{gap_pct:.1f}%，需确保产品差异化价值支撑溢价。")
    
    # 详细产品列表
    st.markdown("---")
    st.markdown("#### 📋 详细产品列表")
    
    display_cols = ['brand', 'model_number', 'category', 'capacity_tons', 'efficiency_seer', 'price', 'state']
    display_df = filtered[display_cols].sort_values(['brand', 'price'])
    st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render_price_analysis_page()
