import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import requests

# ==============================================================================
# Page Config & Style
# ==============================================================================
st.set_page_config(layout="wide", page_title="주식 분석기")

st.markdown("""
<style>
    /* 전역 글꼴 설정 및 비율 최적화 */
    html, body, [class*="st-"] {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 16px;
        color: #374151;
        line-height: 1.6;
    }
    
    /* 헤더 계층 구조화 */
    h1 { font-size: 2.2rem !important; font-weight: 700 !important; color: #111827 !important; margin-bottom: 1.5rem !important; }
    h2 { font-size: 1.8rem !important; font-weight: 700 !important; color: #1F2937 !important; margin-top: 2rem !important; margin-bottom: 1rem !important; border-bottom: 1px solid #E5E7EB; padding-bottom: 0.5rem; }
    h3 { font-size: 1.4rem !important; font-weight: 600 !important; color: #374151 !important; margin-top: 1.5rem !important; margin-bottom: 0.75rem !important; }
    h4 { font-size: 1.1rem !important; font-weight: 600 !important; color: #4B5563 !important; }

    /* 리포트 본문 텍스트 */
    p {
        font-size: 1rem !important;
        margin-bottom: 1rem !important;
        text-align: justify;
    }

    /* 투자의견 배지 */
    .rating-badge {
        display: inline-block;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1rem;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .rating-badge.buy { background: linear-gradient(135deg, #059669, #10B981); color: white; }
    .rating-badge.hold { background: linear-gradient(135deg, #F59E0B, #FBBF24); color: white; }
    .rating-badge.reduce { background: linear-gradient(135deg, #DC2626, #EF4444); color: white; }
    
    /* Executive Summary 박스 */
    .executive-summary {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        color: #1E293B;
        padding: 24px;
        border-radius: 12px;
        font-size: 1.1rem;
        font-weight: 500;
        line-height: 1.8;
        margin: 20px 0;
        box-shadow: inset 4px 0 0 #3B82F6;
    }
    
    /* Insight Box */
    .insight-box {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 5px solid #3B82F6;
        padding: 20px;
        border-radius: 8px;
        margin: 15px 0;
        font-size: 0.95rem;
    }
    .insight-box.risk { border-left-color: #DC2626; }
    .insight-box h4 { margin-top: 0 !important; color: #1F2937; margin-bottom: 10px !important; }

    /* 헤더 섹션 스타일 */
    .header-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #111827;
        margin-bottom: 0.2rem;
        letter-spacing: -0.025em;
    }
    .header-meta {
        font-size: 1.1rem;
        color: #64748B;
        font-weight: 500;
    }
    
    .section-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #111827;
        margin: 40px 0 25px 0;
        padding-bottom: 12px;
        border-bottom: 4px solid #3B82F6;
        display: flex;
        align-items: center;
    }
    
    /* 리포트 컨테이너 전용 스타일 */
    .report-container {
        padding: 40px;
        background-color: white;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-top: 30px;
    }
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
        
        # POST 응답에서 analysis_id 추출
        analysis_id = res_post.json().get("id", 1)
        
        res_get = requests.get(f"{API_URL}/{analysis_id}?symbol={symbol}", timeout=120)
        if res_get.status_code == 200:
            return res_get.json()
        else:
            st.warning(f"GET 요청 실패: {res_get.status_code}")
    except Exception as e:
        st.error(f"API 연결 실패: {e}")
    return None

# ==============================================================================
# Helper Functions
# ==============================================================================

def format_korean_unit(n):
    """숫자를 한국식 단위(조, 억, 만)로 변환"""
    if n >= 1e12:
        return f"{n/1e12:.1f}조"
    if n >= 1e8:
        return f"{n/1e8:.1f}억"
    if n >= 1e4:
        return f"{n/1e4:.1f}만"
    return f"{n:,.0f}"

# ==============================================================================
# Chart Functions (라인 차트 + 막대 차트만 사용)
# ==============================================================================

def plot_financial_trends(fund_data):
    """펀더멘털 성장 추세 (매출액 라인 + 영업이익률 막대 개별 표시)"""
    if not fund_data or not isinstance(fund_data, dict):
        return plot_placeholder("재무 추세 데이터 없음")
    
    from plotly.subplots import make_subplots
    
    revenue = fund_data.get("매출", {})
    op_margin = fund_data.get("영업이익률", {})
    
    if not revenue.get("사용가능") or not op_margin.get("사용가능"):
        return plot_placeholder("데이터 부족")
    
    # 분기 데이터 준비 (백엔드에서 오는 데이터 사용)
    rev_history = revenue.get("history", [])
    labels = revenue.get("labels", [])
    
    # 매출 단위를 조원으로 변환 (10^12로 나눔)
    revenues_scaled = [v / 1e12 for v in rev_history]
    
    margin_history = op_margin.get("history", [])
    margins = [v * 100 for v in margin_history] 
    
    if not labels or not revenues_scaled:
        return plot_placeholder("최근 분기 데이터 부족")

    # 서브플롯 생성: 2행 1열 (매출액 라인 / 영업이익률 막대)
    fig = make_subplots(rows=2, cols=1, 
                        shared_xaxes=True, 
                        vertical_spacing=0.15,
                        subplot_titles=("매출액 추세 (조원)", "영업이익률 추세 (%)"))
    
    # 1. 매출액 (라인 그래프)
    fig.add_trace(
        go.Scatter(x=labels, y=revenues_scaled, name="매출액", 
                   line=dict(color='#3B82F6', width=4), mode='lines+markers+text',
                   text=[f"{v:.1f}" for v in revenues_scaled], textposition="top center"),
        row=1, col=1
    )
    
    # 2. 영업이익률 (막대 그래프)
    fig.add_trace(
        go.Bar(x=labels, y=margins, name="영업이익률", 
               marker_color='#DC2626', opacity=0.8,
               width=0.4, # 막대 너비 줄임
               text=[f"{v:.1f}%" for v in margins], textposition="outside"),
        row=2, col=1
    )
    
    fig.update_layout(
        height=550, # 높이 약간 증가시켜 여유 확보
        margin=dict(l=40, r=40, t=80, b=40), # 여백 증가
        showlegend=False,
        plot_bgcolor='white',
        bargap=0.5 # 막대 사이 간격 증가
    )
    
    # 디자인 디테일
    fig.update_xaxes(type='category', showgrid=True, gridwidth=1, gridcolor='#F1F5F9')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F1F5F9', tickformat=',.1f') # T, G 접미사 제거
    
    return fig

def plot_placeholder(message):
    """차트 플레이스홀더"""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='white'
    )
    return fig

def plot_valuation_indicators(peg, roe, current_ratio):
    """밸류에이션 지표 개별 인디케이터 (게이지 스타일)"""
    from plotly.subplots import make_subplots
    
    # 3개의 인디케이터를 위한 가로형 서브플롯
    fig = make_subplots(
        rows=1, cols=3,
        specs=[[{'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}]]
    )
    
    # 1. PEG Ratio
    fig.add_trace(go.Indicator(
        mode = "gauge+number",
        value = peg,
        title = {'text': "PEG 배수", 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, 3]},
            'bar': {'color': "#3B82F6"},
            'steps': [
                {'range': [0, 1], 'color': "rgba(5, 150, 105, 0.2)"},
                {'range': [1, 2], 'color': "rgba(245, 158, 11, 0.2)"},
                {'range': [2, 3], 'color': "rgba(220, 38, 38, 0.2)"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 1.0
            }
        }
    ), row=1, col=1)
    
    # 2. ROE
    fig.add_trace(go.Indicator(
        mode = "gauge+number",
        value = roe * 100,
        number = {'suffix': "%"},
        title = {'text': "ROE (자본효율성)", 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, 30]},
            'bar': {'color': "#10B981"},
            'steps': [
                {'range': [0, 8], 'color': "rgba(220, 38, 38, 0.2)"},
                {'range': [8, 15], 'color': "rgba(245, 158, 11, 0.2)"},
                {'range': [15, 30], 'color': "rgba(5, 150, 105, 0.2)"}
            ]
        }
    ), row=1, col=2)
    
    # 3. 유동비율
    fig.add_trace(go.Indicator(
        mode = "gauge+number",
        value = current_ratio,
        title = {'text': "유동비율", 'font': {'size': 14}},
        gauge = {
            'axis': {'range': [0, 400]},
            'bar': {'color': "#6366F1"},
            'steps': [
                {'range': [0, 100], 'color': "rgba(220, 38, 38, 0.2)"},
                {'range': [100, 200], 'color': "rgba(245, 158, 11, 0.2)"},
                {'range': [200, 400], 'color': "rgba(5, 150, 105, 0.2)"}
            ]
        }
    ), row=1, col=3)
    
    fig.update_layout(
        height=220,
        margin=dict(l=30, r=30, t=60, b=30), # 여백 증가
        paper_bgcolor='white',
    )
    
    return fig

def plot_price_chart():
    """가격 라인 차트 - 백엔드 데이터 연동 필요"""
    # TODO: 백엔드에서 실제 가격 데이터를 받아와야 함
    fig = go.Figure()
    fig.add_annotation(
        text="가격 데이터 연동 필요",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="gray")
    )
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor='white'
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
        width=0.2 # 더 얇게 조정
    ))
    
    # 과매수/과매도 기준선
    fig.add_hline(y=70, line_dash="dash", line_color="#DC2626", annotation_text="과매수(70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#059669", annotation_text="과매도(30)")
    
    fig.update_layout(
        height=240, # 높이 약간 증가
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='white',
        yaxis=dict(
            range=[0, 100], 
            title="RSI 지수",
            tickmode='linear',
            tick0=0,
            dtick=20,
            gridcolor='#F1F5F9'
        ),
        showlegend=False
    )
    return fig

def plot_drawdown_chart(price_history):
    """수중 차트 (Drawdown Analysis)"""
    if not price_history or not isinstance(price_history, dict):
        return plot_placeholder("데이터 없음")
    
    import pandas as pd
    dates = price_history.get("dates", [])
    close = price_history.get("close", [])
    
    if not dates or not close:
        return plot_placeholder("가격 데이터 부족")
    
    df = pd.DataFrame({"close": close}, index=pd.to_datetime(dates))
    cummax = df['close'].cummax()
    drawdown = (df['close'] / cummax - 1) * 100
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=drawdown.values,
        fill='tozeroy',
        fillcolor='rgba(220, 38, 38, 0.3)',
        line=dict(color='#DC2626', width=2),
        name='Drawdown'
    ))
    
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
    fig.update_layout(
        yaxis_title="전고점 대비 낙폭 (%)",
        height=300,
        margin=dict(l=40, r=40, t=30, b=40), # 여백 증가
        plot_bgcolor='white',
        showlegend=False
    )
    
    return fig

def plot_return_distribution(price_history):
    """수익률 분포 + VaR"""
    if not price_history or not isinstance(price_history, dict):
        return plot_placeholder("데이터 없음")
    
    import pandas as pd
    close = price_history.get("close", [])
    
    if not close or len(close) < 10:
        return plot_placeholder("가격 데이터 부족")
    
    series = pd.Series(close)
    daily_returns = series.pct_change().dropna() * 100
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=daily_returns,
        nbinsx=50,
        name='일간 수익률',
        marker_color='#3B82F6'
    ))
    
    var_5 = daily_returns.quantile(0.05)
    fig.add_vline(x=var_5, line_dash="dash", line_color="red", line_width=2,
                  annotation_text=f"VaR 5%: {var_5:.2f}%")
    
    fig.update_layout(
        xaxis_title="일간 수익률 (%)",
        yaxis_title="빈도",
        height=300,
        margin=dict(l=40, r=40, t=30, b=40), # 여백 증가
        plot_bgcolor='white',
        showlegend=False
    )
    
    return fig

def plot_moving_averages(price_history):
    """장기 이동평균선 추세 (라인 차트 + 이평선 오버레이)"""
    if not price_history or not isinstance(price_history, dict):
        return plot_placeholder("데이터 없음")
    
    import pandas as pd
    dates = price_history.get("dates", [])
    close = price_history.get("close", [])
    ma200 = price_history.get("ma200", [])
    ma300 = price_history.get("ma300", [])
    
    if not dates or not close:
        return plot_placeholder("가격 데이터 부족")
    
    fig = go.Figure()
    
    # 1. 주가 (Area Chart 느낌의 라인)
    fig.add_trace(go.Scatter(
        x=dates, y=close, name="현재가",
        line=dict(color='#059669', width=2),
        opacity=0.8
    ))
    
    # 2. 200일 이동평균선
    if ma200 and any(v is not None for v in ma200):
        fig.add_trace(go.Scatter(
            x=dates, y=ma200, name="200일선",
            line=dict(color='#64748B', width=2, dash='solid'),
        ))
        
    # 3. 300일 이동평균선
    if ma300 and any(v is not None for v in ma300):
        fig.add_trace(go.Scatter(
            x=dates, y=ma300, name="300일선",
            line=dict(color='#94A3B8', width=2, dash='dot'),
        ))
    
    fig.update_layout(
        yaxis_title="가격 (원)",
        height=350,
        margin=dict(l=40, r=40, t=30, b=40),
        plot_bgcolor='white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(tickformat=',d')
    )
    
    # 그리드 스타일
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F1F5F9')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F1F5F9')
    
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
    st.markdown('<div class="section-title">투자 의견 요약</div>', unsafe_allow_html=True)
    
    rating = llm_data.get("investment_rating", "HOLD").upper()
    current = llm_data.get("current_price", 0)
    
    # 투자의견 한글 매핑
    rating_map = {
        "BUY": "매수 (BUY)",
        "HOLD": "보유 (HOLD)",
        "REDUCE": "비중축소 (REDUCE)"
    }
    rating_kor = rating_map.get(rating, rating)
    
    # 투자의견 배지 및 핵심 레이아웃
    rating_class = rating.lower() if rating.lower() in ['buy', 'hold', 'reduce'] else 'hold'
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 20px;">
        <div class="rating-badge {rating_class}">
            투자의견: {rating_kor}
        </div>
        <div style="font-size: 1.2rem; font-weight: 500; color: #64748B;">
            기준가: {current:,.0f} 원
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Executive Summary
    executive_summary = llm_data.get('executive_summary', '')
    if executive_summary:
        st.markdown(f"""
        <div class="executive-summary">
            <strong>📊 투자 개요</strong><br>
            {executive_summary}
        </div>
        """, unsafe_allow_html=True)
    
    # Key Thesis & Risk
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="insight-box">
            <h4 style="margin-top:0;">핵심 논거</h4>
            <p style="margin-bottom:0;">{llm_data.get('key_thesis', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="insight-box risk">
            <h4 style="margin-top:0;">주요 리스크</h4>
            <p style="margin-bottom:0;">{llm_data.get('primary_risk', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

def render_fundamental(long_data, llm_data):
    st.markdown('<div class="section-title">펀더멘털 성장 추세</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.5, 1], gap="large")
    
    with col1:
        financial_trends = long_data.get('financial_trends', {})
        st.plotly_chart(plot_financial_trends(financial_trends), use_container_width=True)
    
    with col2:
        st.markdown(f"""
        <div class="insight-box">
            <h4>분석</h4>
            <p>{llm_data.get('fundamental_analysis', '재무 분석 중...')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

def render_valuation(long_data, llm_data):
    st.markdown('<div class="section-title">밸류에이션 분석</div>', unsafe_allow_html=True)
    
    peg = long_data.get('peg_ratio', 0)
    roe = long_data.get('roe', 0)
    current_ratio = long_data.get('current_ratio', 0)
    
    # 지표 차트를 상단에 전체 너비로 표시
    st.plotly_chart(plot_valuation_indicators(peg, roe, current_ratio), use_container_width=True)
    
    # 분석 의견을 하단에 표시
    # 자동 밸류에이션 해석 고도화
    if peg < 0.8:
        peg_desc = f"🟢 PEG {peg:.2f}로 이익 성장성 대비 주가가 매우 저평가된 매력적인 구간입니다."
    elif peg < 1.2:
        peg_desc = f"🟢 PEG {peg:.2f}는 성장성과 주가 수준이 이상적인 균형을 이루는 적정 가치 구간입니다."
    elif peg < 2.0:
        peg_desc = f"🟡 PEG {peg:.2f}는 성장에 따른 프리미엄이 반영된 구간이나, 과도한 수준은 아닙니다."
    else:
        peg_desc = f"🔴 PEG {peg:.2f}는 이익 성장 대비 주가가 과열되어 있어 밸류에이션 부담이 존재합니다."
    
    roe_status = "우수" if roe > 0.15 else "양호" if roe > 0.10 else "보통"
    current_ratio_status = "건전" if current_ratio > 1.5 else "주의"
    
    st.markdown(f"""
    <div class="insight-box">
        <h4>밸류에이션 요약</h4>
        <p style="font-size: 1.1rem; color: #1E293B; font-weight: 600; margin-bottom: 12px;">{peg_desc}</p>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
            <div style="background: white; padding: 10px; border: 1px solid #F1F5F9; border-radius: 6px;">
                <small style="color: #64748B;">자본 효율성 (ROE)</small><br>
                <strong>{roe*100:.1f}%</strong> <span style="font-size: 0.8em; color: {'#059669' if roe > 0.1 else '#64748B'};">({roe_status})</span>
            </div>
            <div style="background: white; padding: 10px; border: 1px solid #F1F5F9; border-radius: 6px;">
                <small style="color: #64748B;">지급 능력 (유동비율)</small><br>
                <strong>{current_ratio:.2f}배</strong> <span style="font-size: 0.8em; color: {'#059669' if current_ratio > 1.5 else '#DC2626'};">({current_ratio_status})</span>
            </div>
        </div>
        <p style="padding: 15px; background: #F8FAFC; border-radius: 8px; font-size: 0.95rem; line-height: 1.7; color: #334155; border: 1px solid #E2E8F0;">
            {llm_data.get('valuation_analysis', '밸류에이션 상세 분석을 생성하고 있습니다...')}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

def render_technical(mid_data, llm_data):
    st.markdown('<div class="section-title">RSI 분석</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        rsi_value = mid_data.get('rsi_value', 50)
        st.plotly_chart(plot_rsi_bar(rsi_value), use_container_width=True)
    
    with col2:
        # RSI 자동 해석
        if rsi_value > 70:
            rsi_signal = "과매수"
            rsi_desc = f"RSI {rsi_value:.0f}은 과매수 구간입니다. 단기 조정 가능성에 유의하시기 바랍니다."
        elif rsi_value < 30:
            rsi_signal = "과매도"
            rsi_desc = f"RSI {rsi_value:.0f}은 과매도 구간입니다. 기술적 반등 가능성이 높아지고 있습니다."
        else:
            rsi_signal = "중립"
            rsi_desc = f"RSI {rsi_value:.0f}은 중립 구간입니다. 추가 상승 여력이 남아있는 것으로 판단됩니다."
        
        st.markdown(f"""
        <div class="insight-box">
            <h4>{rsi_signal}</h4>
            <p>{rsi_desc}</p>
            <p style="margin-top:15px;">
            <strong>기술적 관점:</strong><br>
            {llm_data.get('technical_analysis', '기술적 분석 중...')}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")


def render_risk_analysis(long_data):
    """리스크 분석 섹션"""
    st.markdown('<div class="section-title">3. 리스크 분석</div>', unsafe_allow_html=True)
    
    # 차트 2개 좌우 배치
    c1, c2 = st.columns([1, 1], gap="large")
    
    with c1:
        st.markdown("**낙폭 분석 (Drawdown)**")
        price_history = long_data.get('price_history', {})
        st.plotly_chart(plot_drawdown_chart(price_history), use_container_width=True)
    
    with c2:
        st.markdown("**수익률 분포**")
        st.plotly_chart(plot_return_distribution(price_history), use_container_width=True)
    
    # 리스크 지표
    risk_metrics = long_data.get('risk_metrics', {})
    if risk_metrics:
        col1, col2, col3 = st.columns(3)
        col1.metric("최대 낙폭 (5년)", f"{risk_metrics.get('max_drawdown_5y', 0)*100:.1f}%")
        col2.metric("VaR 5%", f"{risk_metrics.get('var_5_pct', 0)*100:.2f}%")
        col3.metric("변동성 (연간)", f"{risk_metrics.get('volatility', 0)*100:.1f}%")
    
    # 장기 이평선
    st.markdown("**이동평균선 (장기 추세)**")
    st.plotly_chart(plot_moving_averages(price_history), use_container_width=True)

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
        
        
        # LLM 데이터 파싱
        llm_data = res.get("llm_output")
        if llm_data is None:
            llm_data = res.get("report", {})
        if not isinstance(llm_data, dict):
            llm_data = {}
        
        company_name = res.get("company_name", res.get("symbol", "Unknown"))
        current_price = llm_data.get("current_price", res.get("short_term", {}).get("current_price", 0))
     
        
        render_header(res["symbol"], company_name, current_price)
        
        # 탭 제거, 모든 콘텐츠를 한 페이지에 표시
        render_summary(llm_data)
        render_fundamental(res["long_term"], llm_data)
        render_valuation(res["long_term"], llm_data)
        render_technical(res["mid_term"], llm_data)
        render_risk_analysis(res["long_term"])
        
        # 전문 리서치 보고서 섹션
        st.markdown("---")
        st.markdown('<div class="section-title">전문 리서치 보고서</div>', unsafe_allow_html=True)
        report_text = llm_data.get("report_markdown", "보고서가 생성되지 않았습니다.")
        st.markdown(f'<div class="report-container">{report_text}</div>', unsafe_allow_html=True)
    else:
        st.info("왼쪽 사이드바에서 종목 코드를 입력하고 [분석 실행] 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()