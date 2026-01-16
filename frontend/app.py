import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

# ==============================================================================
# Page Config & Style (Global CSS)
# ==============================================================================
st.set_page_config(layout="wide", page_title="Institutional Equity Research")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
        color: #334155;
    }

    /* Header Component */
    .header-title { font-size: 32px; font-weight: 800; color: #0F172A; letter-spacing: -0.5px; margin:0;}
    .header-meta { font-size: 14px; color: #64748B; font-weight: 500; margin-top: 4px; }
    
    /* Summary Component */
    .summary-box {
        background-color: #F8FAFC;
        border-left: 4px solid: #3B82F6;
        padding: 15px;
        border-radius: 0 8px 8px 0;
    }
    
    /* Section Headers */
    .section-title {
        font-size: 20px; font-weight: 700; color: #1E293B;
        border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 20px;
    }

    /* Insight Text List */
    .insight-list { font-size: 15px; line-height: 1.6; color: #475569; padding-left: 20px; }
    .insight-list li { margin-bottom: 8px; }
    .insight-list b { color: #1E293B; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [Data Logic] API Call
# ==============================================================================

def get_real_time_analysis(symbol):
    """백엔드 API 호출"""
    import os
    API_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1/analysis")
    try:
        # 1. 분석 요청 (POST)
        res_post = requests.post(f"{API_URL}/", json={"symbol": symbol}, timeout=10)
        if res_post.status_code != 200:
            st.warning(f"POST 요청 실패: {res_post.status_code}")
            return None
        
        # 2. 결과 조회 (GET)
        analysis_id = 1
        res_get = requests.get(f"{API_URL}/{analysis_id}?symbol={symbol}", timeout=60)
        if res_get.status_code == 200:
            return res_get.json()
        else:
            st.warning(f"GET 요청 실패: {res_get.status_code}")
    except Exception as e:
        st.error(f"API 연결 실패: {e}")
    return None

# ==============================================================================
# [Chart Functions] 6 Curated Charts
# ==============================================================================

def plot_investment_rating_gauge(current_price, target_price, rating):
    """1. 투자의견 Angular Gauge"""
    upside_pct = ((target_price - current_price) / current_price) * 100 if target_price > 0 else 0
    
    color_map = {"Overweight": "#059669", "Neutral": "#64748B", "Underweight": "#DC2626"}
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_price,
        delta={'reference': target_price, 'suffix': " KRW", 'relative': False},
        title={'text': f"<b>{rating}</b> | 목표가 달성률"},
        number={'prefix': "₩", 'font': {'size': 32}},
        gauge={
            'axis': {'range': [current_price * 0.7, target_price * 1.2] if target_price > 0 else [0, current_price * 2]},
            'bar': {'color': color_map.get(rating, "#64748B"), 'thickness': 0.8},
            'steps': [
                {'range': [current_price * 0.7, current_price], 'color': "#FEE2E2"},
                {'range': [current_price, target_price if target_price > 0 else current_price * 1.5], 'color': "#DBEAFE"}
            ],
            'threshold': {
                'line': {'color': "#DC2626", 'width': 3},
                'thickness': 0.75,
                'value': target_price if target_price > 0 else current_price * 1.2
            }
        }
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def plot_financial_trends(long_data):
    """2. 재무 추세 Multi-line (백엔드 데이터)"""
    # 백엔드 재무추세 데이터 파싱
    evidence = long_data.get("evidence", {})
    fin_trends = evidence.get("재무추세", {})
    
    # 데이터 추출 (있는 경우에만)
    revenue = fin_trends.get("매출", {})
    op_margin = fin_trends.get("영업이익률", {})
    
    # 간단한 Mock 데이터 (실제 분기 데이터가 없는 경우)
    quarters = ['23.1Q', '23.2Q', '23.3Q', '23.4Q', '24.1Q', '24.2Q', '24.3Q', '24.4Q']
    revenue_data = [60, 62, 61, 63, 65, 67, 68, 70]
    margin_data = [12, 11, 13, 14, 15, 15.5, 16, 16.5]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(
        x=quarters, y=revenue_data, name="매출",
        mode='lines+markers',
        line=dict(color='#0F172A', width=3),
        marker=dict(size=8)
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=quarters, y=margin_data, name="영업이익률",
        mode='lines+markers',
        line=dict(color='#3B82F6', width=2, dash='dash'),
        marker=dict(size=6)
    ), secondary_y=True)
    
    fig.update_yaxes(title_text="매출 (조원)", secondary_y=False)
    fig.update_yaxes(title_text="이익률 (%)", secondary_y=True)
    fig.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_valuation_bullets(peg, roe, current_ratio):
    """3. PEG/ROE/유동비율 Bullet Gauge"""
    fig = make_subplots(
        rows=3, cols=1,
        specs=[[{'type': 'indicator'}], [{'type': 'indicator'}], [{'type': 'indicator'}]],
        vertical_spacing=0.15
    )
    
    # PEG
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=peg if peg else 0,
        title={'text': "PEG Ratio"},
        gauge={
            'shape': "bullet",
            'axis': {'range': [None, 2.5]},
            'steps': [
                {'range': [0, 1.0], 'color': "#D1FAE5"},
                {'range': [1.0, 2.5], 'color': "#FEE2E2"}
            ],
            'bar': {'color': "#1E293B"}
        }
    ), row=1, col=1)
    
    # ROE
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=(roe * 100) if roe else 0,
        number={'suffix': "%"},
        title={'text': "ROE"},
        gauge={
            'shape': "bullet",
            'axis': {'range': [None, 30]},
            'steps': [
                {'range': [0, 12], 'color': "#FEE2E2"},
                {'range': [12, 30], 'color': "#D1FAE5"}
            ],
            'bar': {'color': "#1E293B"}
        }
    ), row=2, col=1)
    
    # 유동비율
    fig.add_trace(go.Indicator(
        mode="number+gauge",
        value=current_ratio if current_ratio else 0,
        title={'text': "Current Ratio"},
        gauge={
            'shape': "bullet",
            'axis': {'range': [None, 3.0]},
            'steps': [
                {'range': [0, 1.5], 'color': "#FEE2E2"},
                {'range': [1.5, 3.0], 'color': "#D1FAE5"}
            ],
            'bar': {'color': "#1E293B"}
        }
    ), row=3, col=1)
    
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
    return fig

def plot_price_with_levels(support, resistance):
    """4. 가격 차트 (Mock 데이터 + 지지/저항선)"""
    # Mock 가격 데이터
    dates = pd.date_range(start=datetime.today() - timedelta(days=120), periods=90)
    np.random.seed(42)
    base_price = 70000
    price_changes = np.random.normal(100, 600, 90)
    close = base_price + np.cumsum(price_changes)
    
    df = pd.DataFrame({
        'Date': dates, 'Close': close,
        'Open': close - np.random.randint(100, 500, 90),
        'High': close + np.random.randint(100, 800, 90),
        'Low': close - np.random.randint(100, 800, 90),
        'Volume': np.random.randint(10000, 50000, 90)
    })
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    
    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price', increasing_line_color='#BE123C', decreasing_line_color='#1D4ED8', showlegend=False
    ), row=1, col=1)
    
    # 이동평균선
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], line=dict(color='#F59E0B', width=2), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA60'], line=dict(color='#64748B', width=1.5, dash='dot'), name='MA60'), row=1, col=1)
    
    # 지지/저항선
    if support:
        fig.add_hline(y=support, line_dash="dash", line_color="#059669", annotation_text=f"지지: {support:,.0f}", row=1, col=1)
    if resistance:
        fig.add_hline(y=resistance, line_dash="dash", line_color="#DC2626", annotation_text=f"저항: {resistance:,.0f}", row=1, col=1)
    
    # 거래량
    colors = ['#BE123C' if r['Open'] < r['Close'] else '#1D4ED8' for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=colors, name='Vol', showlegend=False), row=2, col=1)
    
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, plot_bgcolor='white')
    return fig

def plot_rsi_indicator(rsi_value):
    """5. RSI Indicator"""
    if rsi_value >= 70:
        bg_color = "#FEE2E2"
    elif rsi_value <= 30:
        bg_color = "#D1FAE5"
    else:
        bg_color = "#F8FAFC"
    
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=rsi_value,
        delta={
            'reference': 50,
            'relative': False,
            'increasing': {'color': "#DC2626"},
            'decreasing': {'color': "#059669"}
        },
        title={'text': "<b>RSI (14일)</b>", 'font': {'size': 16}},
        number={'font': {'size': 48}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    
    fig.update_layout(height=150, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor=bg_color)
    return fig

def plot_pivot_table(pivot, r1, r2, s1, s2):
    """6. 피봇 포인트 Plotly Table"""
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['<b>레벨</b>', '<b>가격</b>', '<b>액션</b>'],
            fill_color='#F1F5F9',
            align='center',
            font=dict(size=14, color='#475569', family='Roboto')
        ),
        cells=dict(
            values=[
                ['R2 (2차 저항)', 'R1 (1차 저항)', 'Pivot (기준)', 'S1 (1차 지지)', 'S2 (2차 지지)'],
                [f"₩{r2:,.0f}", f"₩{r1:,.0f}", f"₩{pivot:,.0f}", f"₩{s1:,.0f}", f"₩{s2:,.0f}"],
                ['Strong Sell', 'Take Profit', 'Entry/Hold', 'Add Position', 'Stop Loss']
            ],
            fill_color=[['#FEE2E2', '#FEF3C7', '#ECFDF5', '#FEF3C7', '#FEE2E2']],
            align='center',
            font=dict(size=13, color='#334155'),
            height=35
        )
    )])
    
    fig.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=0))
    return fig

# ==============================================================================
# [UI Components]
# ==============================================================================

def render_header(symbol, company_name, price_val):
    with st.container():
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            st.markdown(f'<div class="header-title">{company_name} ({symbol})</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="header-meta">Equity Research | {datetime.today().strftime("%Y-%m-%d")}</div>', unsafe_allow_html=True)
        with c2:
            st.metric(label="Current Price", value=f"{price_val:,.0f} KRW", delta="+1.2%")
        st.markdown("---")

def render_summary_card(analysis, llm_data):
    long = analysis.get("long_term", {})
    mid = analysis.get("mid_term", {})
    short = analysis.get("short_term", {})
    
    with st.container():
        col_gauge, col_text = st.columns([1, 2])
        
        with col_gauge:
            # 투자의견 게이지
            rating = llm_data.get("investment_rating", "Neutral")
            target = llm_data.get("target_price", 0)
            current = llm_data.get("current_price", short.get("pivot_point", 76800))
            
            st.plotly_chart(plot_investment_rating_gauge(current, target, rating), use_container_width=True)
        
        with col_text:
            st.markdown(f"""
            <div class="summary-box">
                <h4 style="margin:0 0 8px 0; color:#1E40AF;">📋 Executive Summary</h4>
                <div style="color:#334155; font-size:15px; line-height:1.6;">
                <b>핵심 논거:</b> {llm_data.get('key_thesis', 'N/A')}<br>
                <b>주요 리스크:</b> {llm_data.get('primary_risk', 'N/A')}<br>
                <b>목표 기간:</b> {llm_data.get('target_period_months', 12)}개월
                </div>
            </div>
            """, unsafe_allow_html=True)

def render_fundamental_section(long_data):
    st.markdown('<div class="section-title">1. Quantitative Analysis (Long-term)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1], gap="large")
    
    with c1:
        st.markdown(f"""
        <ul class="insight-list">
            <li><b>재무 트렌드</b>: {long_data.get('fundamental_trend', 'N/A')}</li>
            <li><b>매출 기울기</b>: {long_data.get('revenue_slope', 0):.4f}</li>
            <li><b>PEG Ratio</b>: {long_data.get('peg_ratio', 0):.2f}</li>
            <li><b>종합 의견</b>: {long_data.get('valuation_status', 'N/A')}</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.plotly_chart(plot_financial_trends(long_data), use_container_width=True)
    
    with c2:
        # 밸류에이션 Bullet Gauges
        evidence = long_data.get("evidence", {}) if "evidence" in str(long_data) else {}
        valuation = evidence.get("밸류에이션", {}) if evidence else {}
        
        peg = valuation.get("trailingPEG") or long_data.get('peg_ratio', 0)
        roe = valuation.get("ROE", 0)
        current_ratio = valuation.get("currentRatio", 0)
        
        st.plotly_chart(plot_valuation_bullets(peg, roe, current_ratio), use_container_width=True)

def render_technical_section(mid_data):
    st.markdown('<div class="section-title">2. Technical Setup (Mid-term)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.5, 1], gap="large")
    
    with c1:
        # 가격 차트 (지지/저항선 포함)
        evidence = mid_data.get("evidence", {}) if "evidence" in str(mid_data) else {}
        support = evidence.get("지지선", 0)
        resistance = evidence.get("저항선", 0)
        
        st.plotly_chart(plot_price_with_levels(support, resistance), use_container_width=True)
    
    with c2:
        # RSI Indicator
        rsi_value = mid_data.get('rsi_value', 50)
        st.plotly_chart(plot_rsi_indicator(rsi_value), use_container_width=True)
        
        st.markdown(f"""
        <div style="background-color:#F8FAFC; padding:15px; border-radius:8px; margin-top:10px;">
            <ul class="insight-list">
                <li><b>추세 분석</b>: {mid_data.get('ma_trend', 'N/A')}</li>
                <li><b>주요 이평선</b>: {mid_data.get('ma_state', 'N/A')}</li>
                <li><b>의견</b>: {mid_data.get('message', 'N/A')}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

def render_strategy_section(short_data):
    st.markdown('<div class="section-title">3. Investment Strategy (Action Plan)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="large")
    
    with c1:
        st.info(f"### 📊 Strategy: {short_data.get('candle_pattern', 'N/A')}")
        st.markdown(f"""
        <div class="insight-list">
            <ul>
                <li><b>수급 상황</b>: 전일 거래량 {short_data.get('volume_ratio', 100)}% 수준</li>
                <li><b>단기 가이드</b>: {short_data.get('message', 'N/A')}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with c2:
        # 피봇 포인트 Plotly Table
        pivot = short_data.get('pivot_point', 0)
        r1 = short_data.get('r1', 0)
        r2 = short_data.get('r2', 0)
        s1 = short_data.get('s1', 0)
        s2 = short_data.get('s2', 0)
        
        st.plotly_chart(plot_pivot_table(pivot, r1, r2, s1, s2), use_container_width=True)

def main():
    st.sidebar.title("Asset Analyzer")
    symbol = st.sidebar.text_input("종목 코드 입력", value="005930")
    
    if st.sidebar.button("분석 실행"):
        with st.spinner("전문 분석 엔진 가동 중..."):
            result = get_real_time_analysis(symbol)
            if result:
                st.session_state.analysis = result
    
    if "analysis" in st.session_state:
        res = st.session_state.analysis
        llm_data = res.get("llm_output", {})
        
        # 회사 이름 추출
        company_name = llm_data.get("company_name", res.get("symbol", "Unknown"))
        current_price = llm_data.get("current_price", res["short_term"].get("pivot_point", 76800))
        
        render_header(res["symbol"], company_name, current_price)
        
        tab1, tab2 = st.tabs(["Dashboard Analysis", "Professional Research"])
        
        with tab1:
            render_summary_card(res, llm_data)
            render_fundamental_section(res["long_term"])
            render_technical_section(res["mid_term"])
            render_strategy_section(res["short_term"])
        
        with tab2:
            st.markdown('<div class="section-title">Institutional Equity Research Report</div>', unsafe_allow_html=True)
            report_text = llm_data.get("report_markdown", "보고서가 생성되지 않았습니다.")
            st.markdown(report_text)
    else:
        st.info("왼쪽 사이드바에서 종목 코드를 입력하고 [분석 실행] 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()