import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

# ==============================================================================
# Page Config & Style
# ==============================================================================
st.set_page_config(layout="wide", page_title="주식 분석기")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
        color: #334155;
    }

    .header-title { font-size: 32px; font-weight: 800; color: #0F172A; margin:0;}
    .header-meta { font-size: 14px; color: #64748B; font-weight: 500; margin-top: 4px; }
    .section-title { font-size: 20px; font-weight: 700; color: #1E293B; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 20px; }
    .insight-box { background-color: #F8FAFC; padding: 15px; border-radius: 8px; border-left: 4px solid #3B82F6; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# API Call
# ==============================================================================

def get_real_time_analysis(symbol):
    """백엔드 API 호출"""
    import os
    API_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1/analysis")
    try:
        res_post = requests.post(f"{API_URL}/", json={"symbol": symbol}, timeout=10)
        if res_post.status_code != 200:
            st.warning(f"POST 요청 실패: {res_post.status_code}")
            return None
        
        analysis_id = 1
        res_get = requests.get(f"{API_URL}/{analysis_id}?symbol={symbol}", timeout=120)
        if res_get.status_code == 200:
            return res_get.json()
        else:
            st.warning(f"GET 요청 실패: {res_get.status_code}")
    except Exception as e:
        st.error(f"API 연결 실패: {e}")
    return None

# ==============================================================================
# Chart Functions (라인 차트 + 막대 차트만 사용)
# ==============================================================================

def plot_financial_trends():
    """재무 추세 라인 차트"""
    quarters = ['23.1Q', '23.2Q', '23.3Q', '23.4Q', '24.1Q', '24.2Q', '24.3Q', '24.4Q']
    revenue = [60, 62, 61, 63, 65, 67, 68, 70]
    margin = [12, 11, 13, 14, 15, 15.5, 16, 16.5]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Scatter(
        x=quarters, y=revenue, name="매출 (조원)",
        mode='lines+markers',
        line=dict(color='#0F172A', width=3),
        marker=dict(size=8)
    ), secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=quarters, y=margin, name="영업이익률 (%)",
        mode='lines+markers',
        line=dict(color='#3B82F6', width=2, dash='dash'),
        marker=dict(size=6)
    ), secondary_y=True)
    
    fig.update_yaxes(title_text="매출 (조원)", secondary_y=False)
    fig.update_yaxes(title_text="이익률 (%)", secondary_y=True)
    fig.update_layout(
        height=280,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_valuation_bars(peg, roe, current_ratio):
    """밸류에이션 지표 막대 차트"""
    fig = go.Figure()
    
    categories = ['PEG Ratio', 'ROE (%)', '유동비율']
    values = [peg if peg else 0, (roe * 100) if roe else 0, current_ratio if current_ratio else 0]
    colors = ['#059669' if v > 0 else '#DC2626' for v in values]
    
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=[f"{v:.2f}" for v in values],
        textposition='outside'
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
        yaxis_title="값"
    )
    return fig

def plot_price_chart():
    """가격 라인 차트 (Mock 데이터)"""
    dates = pd.date_range(start=datetime.today() - timedelta(days=120), periods=90)
    np.random.seed(42)
    base_price = 70000
    price_changes = np.random.normal(100, 600, 90)
    close = base_price + np.cumsum(price_changes)
    
    df = pd.DataFrame({'Date': dates, 'Close': close})
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['Close'], name='종가',
        mode='lines',
        line=dict(color='#0F172A', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['MA20'], name='20일 이평선',
        line=dict(color='#F59E0B', width=1.5)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Date'], y=df['MA60'], name='60일 이평선',
        line=dict(color='#64748B', width=1.5, dash='dot')
    ))
    
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='white',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_rsi_bar(rsi_value):
    """RSI 막대 차트"""
    fig = go.Figure()
    
    color = '#DC2626' if rsi_value >= 70 else ('#059669' if rsi_value <= 30 else '#64748B')
    
    fig.add_trace(go.Bar(
        x=['RSI'],
        y=[rsi_value],
        marker_color=color,
        text=[f"{rsi_value:.1f}"],
        textposition='outside',
        width=0.5
    ))
    
    # 과매수/과매도 기준선
    fig.add_hline(y=70, line_dash="dash", line_color="#DC2626", annotation_text="과매수(70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#059669", annotation_text="과매도(30)")
    
    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
        yaxis=dict(range=[0, 100], title="RSI 값"),
        showlegend=False
    )
    return fig

# ==============================================================================
# UI Components
# ==============================================================================

def render_header(symbol, company_name, price_val):
    with st.container():
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            st.markdown(f'<div class="header-title">{company_name} ({symbol})</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="header-meta">주식 분석 리서치 | {datetime.today().strftime("%Y-%m-%d")}</div>', unsafe_allow_html=True)
        with c2:
            st.metric(label="현재가", value=f"{price_val:,.0f} 원")
        st.markdown("---")

def render_summary(llm_data):
    st.markdown('<div class="section-title">📋 투자 의견 요약</div>', unsafe_allow_html=True)
    
    rating = llm_data.get("investment_rating", "Neutral")
    target = llm_data.get("target_price", 0)
    current = llm_data.get("current_price", 0)
    upside = llm_data.get("upside_pct", 0)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("투자의견", rating)
    col2.metric("목표가", f"{target:,.0f} 원")
    col3.metric("상승여력", f"+{upside:.1f}%")
    
    st.markdown(f"""
    <div class="insight-box">
        <b>핵심 논거:</b> {llm_data.get('key_thesis', 'N/A')}<br>
        <b>주요 리스크:</b> {llm_data.get('primary_risk', 'N/A')}
    </div>
    """, unsafe_allow_html=True)

def render_fundamental(long_data, llm_data):
    st.markdown('<div class="section-title">1. 재무 분석 (장기)</div>', unsafe_allow_html=True)
    
    # 재무 추세 차트와 해석을 좌우로 배치
    c1, c2 = st.columns([1, 1], gap="large")
    
    with c1:
        st.plotly_chart(plot_financial_trends(), use_container_width=True)
    
    with c2:
        st.markdown(f"""
        <div class="insight-box">
            <p style="font-size: 15px; line-height: 1.6;">{llm_data.get('key_thesis', '재무 추세 분석 중...')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 밸류에이션 막대 차트와 지표를 좌우로 배치
    c3, c4 = st.columns([1, 1], gap="large")
    
    with c3:
        evidence = long_data.get("evidence", {}) if "evidence" in str(long_data) else {}
        valuation = evidence.get("밸류에이션", {}) if evidence else {}
        peg = valuation.get("trailingPEG") or long_data.get('peg_ratio', 0)
        roe = valuation.get("ROE", 0)
        current_ratio = valuation.get("currentRatio", 0)
        
        st.plotly_chart(plot_valuation_bars(peg, roe, current_ratio), use_container_width=True)
    
    with c4:
        st.markdown(f"""
        <div class="insight-box">
            <b>PEG Ratio:</b> {peg:.2f}<br>
            <b>ROE:</b> {roe*100:.1f}%<br>
            <b>유동비율:</b> {current_ratio:.2f}
        </div>
        """, unsafe_allow_html=True)

def render_technical(mid_data, llm_data):
    st.markdown('<div class="section-title">2. 기술적 분석 (중기)</div>', unsafe_allow_html=True)
    
    # 가격 차트와 해석을 좌우로 배치
    c1, c2 = st.columns([1, 1], gap="large")
    
    with c1:
        st.plotly_chart(plot_price_chart(), use_container_width=True)
    
    with c2:
        st.markdown(f"""
        <div class="insight-box">
            <p style="font-size: 15px; line-height: 1.6;">{llm_data.get('primary_risk', '기술적 분석 중...')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # RSI 차트와 지표를 좌우로 배치
    c3, c4 = st.columns([1, 1], gap="large")
    
    with c3:
        rsi_value = mid_data.get('rsi_value', 50)
        st.plotly_chart(plot_rsi_bar(rsi_value), use_container_width=True)
    
    with c4:
        st.markdown(f"""
        <div class="insight-box">
            <b>RSI:</b> {rsi_value:.1f}<br>
            <b>추세:</b> {mid_data.get('ma_trend', 'N/A')}<br>
            <b>의견:</b> {mid_data.get('message', 'N/A')}
        </div>
        """, unsafe_allow_html=True)

def render_strategy(short_data):
    st.markdown('<div class="section-title">3. 투자 전략 (단기)</div>', unsafe_allow_html=True)
    
    st.info(f"**전략:** {short_data.get('candle_pattern', 'N/A')}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("피봇 포인트", f"{short_data.get('pivot_point', 0):,.0f} 원")
    col2.metric("1차 저항", f"{short_data.get('r1', 0):,.0f} 원")
    col3.metric("1차 지지", f"{short_data.get('s1', 0):,.0f} 원")

def main():
    st.sidebar.title("주식 분석 시스템")
    symbol = st.sidebar.text_input("종목 코드", value="005930")
    
    if st.sidebar.button("분석 실행"):
        with st.spinner("분석 중..."):
            result = get_real_time_analysis(symbol)
            if result:
                st.session_state.analysis = result
    
    if "analysis" in st.session_state:
        res = st.session_state.analysis
        # llm_output 또는 report 필드 확인 (하위 호환성)
        llm_data = res.get("llm_output", res.get("report", {}))
        
        company_name = res.get("company_name", res.get("symbol", "Unknown"))
        current_price = llm_data.get("current_price", res["short_term"].get("pivot_point", 0))
        
        # 디버그: LLM 데이터 확인 (메인 페이지 상단에 표시)
        with st.expander("🔍 DEBUG - API 응답 구조 확인", expanded=True):
            st.write("**전체 응답 키:**", list(res.keys()))
            st.write("**llm_output 키:**", list(llm_data.keys()))
            st.json(llm_data)  # 전체 LLM 데이터 표시
        
        render_header(res["symbol"], company_name, current_price)
        
        # 탭 제거, 모든 콘텐츠를 한 페이지에 표시
        render_summary(llm_data)
        render_fundamental(res["long_term"], llm_data)
        render_technical(res["mid_term"], llm_data)
        render_strategy(res["short_term"])
        
        # 전문 리서치 보고서 섹션
        st.markdown("---")
        st.markdown('<div class="section-title">📄 전문 리서치 보고서</div>', unsafe_allow_html=True)
        report_text = llm_data.get("report_markdown", "보고서가 생성되지 않았습니다.")
        st.markdown(report_text)
    else:
        st.info("왼쪽 사이드바에서 종목 코드를 입력하고 [분석 실행] 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()