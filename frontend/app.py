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
        border-left: 4px solid #3B82F6;
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

    /* Tables */
    .pivot-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .pivot-table th { background-color: #F1F5F9; padding: 12px; text-align: left; font-weight: 600; color: #475569; border-bottom: 2px solid #E2E8F0; }
    .pivot-table td { padding: 10px 12px; border-bottom: 1px solid #E2E8F0; color: #334155; }
    .highlight-row { background-color: #ECFDF5; font-weight: 700; color: #047857; }

    /* Badges */
    .rating-badge-container { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; }
    .rating-badge { background-color: #DC2626; color: white; padding: 8px 24px; border-radius: 6px; font-weight: 800; font-size: 20px; letter-spacing: 1px; box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.3); }
    .tp-text { font-size: 14px; font-weight: 700; color: #DC2626; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [Data Logic] Chart & Data Generators
# ==============================================================================

def get_real_time_analysis(symbol):
    """백엔드 API 호출"""
    # Docker 환경에서는 http://backend:8000, 로컬에서는 http://localhost:8000
    # Nginx를 통한다면 http://localhost/api/v1/analysis
    API_URL = "http://localhost:8000/v1/analysis" 
    try:
        # 1. 분석 요청 (POST)
        res_post = requests.post(f"{API_URL}/", json={"symbol": symbol}, timeout=10)
        if res_post.status_code != 200:
            st.warning(f"POST 요청 실패: {res_post.status_code}")
            return None
        
        # 2. 결과 조회 (GET) - 현재 백엔드 스텁은 symbol을 쿼리로 받게 수정함
        analysis_id = 1
        res_get = requests.get(f"{API_URL}/{analysis_id}?symbol={symbol}", timeout=30)
        if res_get.status_code == 200:
            return res_get.json()
        else:
            st.warning(f"GET 요청 실패: {res_get.status_code}")
    except Exception as e:
        st.error(f"API 연결 실패: {e}")
    return None

def get_mock_data():
    """가상 데이터 생성기 (차트 시각화용)"""
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
    
    last_idx = df.index[-1]
    df.at[last_idx, 'Close'] = df.at[last_idx, 'Close'] * 1.03
    df.at[last_idx, 'Volume'] = df['Volume'].mean() * 1.8
    
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    return df

DATA = get_mock_data()

def plot_price_chart(df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
    fig.add_trace(go.Candlestick(
        x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price', increasing_line_color='#BE123C', decreasing_line_color='#1D4ED8', showlegend=False
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA20'], line=dict(color='#F59E0B', width=1.5), name='MA20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['Date'], y=df['MA60'], line=dict(color='#64748B', width=1.5, dash='dot'), name='MA60'), row=1, col=1)
    colors = ['#BE123C' if r['Open'] < r['Close'] else '#1D4ED8' for _, r in df.iterrows()]
    fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=colors, name='Vol', showlegend=False), row=2, col=1)
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, plot_bgcolor='white')
    return fig

def plot_financial_combo():
    quarters = ['23.1Q', '23.2Q', '23.3Q', '23.4Q', '24.1Q', '24.2Q', '24.3Q', '24.4Q']
    revenue = [60, 62, 61, 63, 65, 67, 68, 70]
    margin = [12, 11, 13, 14, 15, 15.5, 16, 16.5]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=quarters, y=revenue, name="Rev", marker_color='#CBD5E1', opacity=0.6), secondary_y=False)
    fig.add_trace(go.Scatter(x=quarters, y=margin, name="Margin", line=dict(color='#0F172A', width=3), mode='lines+markers'), secondary_y=True)
    fig.update_layout(height=200, margin=dict(l=0, r=0, t=20, b=0), plot_bgcolor='white', showlegend=False)
    return fig

def plot_peg_bullet(peg_value):
    fig = go.Figure(go.Indicator(
        mode = "number+gauge", value = peg_value,
        domain = {'x': [0.1, 1], 'y': [0.2, 0.9]},
        title = {'text': "<b>PEG</b>", 'font': {'size': 14}},
        gauge = {
            'shape': "bullet", 'axis': {'range': [None, 2.5]},
            'steps': [{'range': [0, 1.0], 'color': "#dcfce7"}, {'range': [1.0, 2.5], 'color': "#fee2e2"}],
            'bar': {'color': "#1e293b"}
        }
    ))
    fig.update_layout(height=100, margin=dict(l=10, r=10, t=10, b=10))
    return fig

# ==============================================================================
# [UI Components] Modular Functional Components
# ==============================================================================

def render_header(symbol, price_val):
    with st.container():
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            st.markdown(f'<div class="header-title">{symbol} Analysis</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="header-meta">Equity Research | {datetime.today().strftime("%Y-%m-%d")}</div>', unsafe_allow_html=True)
        with c2:
            st.metric(label="Current Price", value=f"{price_val:,.0f} KRW", delta="+1.2%")
        st.markdown("---")

def render_summary_card(analysis):
    long = analysis.get("long_term", {})
    mid = analysis.get("mid_term", {})
    short = analysis.get("short_term", {})
    with st.container():
        col_badge, col_text = st.columns([1, 4])
        with col_badge:
            st.markdown(f"""
            <div class="rating-badge-container">
                <div class="rating-badge" style="background-color: #DC2626">
                    OVERWEIGHT
                </div>
                <div class="tp-text">Target: 92,000</div>
            </div>
            """, unsafe_allow_html=True)
        with col_text:
            st.markdown(f"""
            <div class="summary-box">
                <h4 style="margin:0 0 8px 0; color:#1E40AF;">📋 Executive Summary</h4>
                <div style="color:#334155; font-size:15px; line-height:1.6;">
                <b>장기:</b> {long.get('message', 'N/A')}<br>
                <b>중기:</b> {mid.get('message', 'N/A')}<br>
                <b>단기:</b> {short.get('message', 'N/A')}
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
            <li><b>PEG Ratio</b>: {long_data.get('peg_ratio', 0):.2f} (저평가 매력)</li>
            <li><b>종합 의견</b>: {long_data.get('valuation_status', 'N/A')}</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rev Slope", f"{long_data.get('revenue_slope', 0):.2f}")
        m2.metric("PEG", f"{long_data.get('peg_ratio', 0):.2f}")
        m3.metric("FCF Yield", "4.8%")
    with c2:
        st.plotly_chart(plot_financial_combo(), use_container_width=True)
        st.plotly_chart(plot_peg_bullet(long_data.get('peg_ratio', 0.6)), use_container_width=True)

def render_technical_section(mid_data):
    st.markdown('<div class="section-title">2. Technical Setup (Mid-term)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.5, 1], gap="large")
    with c1:
        st.plotly_chart(plot_price_chart(DATA), use_container_width=True)
    with c2:
        st.markdown(f"""
        <div style="background-color:#F8FAFC; padding:15px; border-radius:8px;">
            <ul class="insight-list">
                <li><b>추세 분석</b>: {mid_data.get('ma_trend', 'N/A')}</li>
                <li><b>주요 이평선</b>: {mid_data.get('ma_state', 'N/A')}</li>
                <li><b>RSI 지표</b>: {mid_data.get('rsi_value', 0)} ({mid_data.get('rsi_signal', 'N/A')})</li>
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
        st.markdown("""
        <table class="pivot-table">
            <thead><tr><th>Level</th><th>Price</th><th>Action</th></tr></thead>
            <tbody>
                <tr><td>R1 (1차 저항)</td><td>{r1:,.0f}</td><td>Target</td></tr>
                <tr class="highlight-row"><td>Pivot (기준)</td><td>{pv:,.0f}</td><td>Entry/Hold</td></tr>
                <tr><td>S1 (1차 지지)</td><td>{s1:,.0f}</td><td>Stop Loss</td></tr>
            </tbody>
        </table>
        """.format(r1=short_data.get('r1', 0), pv=short_data.get('pivot_point', 0), s1=short_data.get('s1', 0)), unsafe_allow_html=True)

def main():
    st.sidebar.title("🛡️ Asset Guardian")
    symbol = st.sidebar.text_input("종목 코드 입력", value="005930")
    
    if st.sidebar.button("🔍 분석 실행"):
        with st.spinner("전문 분석 엔진 가동 중..."):
            result = get_real_time_analysis(symbol)
            if result:
                st.session_state.analysis = result
    
    if "analysis" in st.session_state:
        res = st.session_state.analysis
        render_header(res["symbol"], res["short_term"].get("pivot_point", 76800))
        render_summary_card(res)
        render_fundamental_section(res["long_term"])
        render_technical_section(res["mid_term"])
        render_strategy_section(res["short_term"])
    else:
        st.info("왼쪽 사이드바에서 종목 코드를 입력하고 [분석 실행] 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()