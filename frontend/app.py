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
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
    
    * {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    /* 투자의견 배지 */
    .rating-badge {
        display: inline-block;
        padding: 8px 20px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 18px;
        margin: 10px 0;
    }
    .rating-badge.buy {
        background: linear-gradient(135deg, #059669, #10B981);
        color: white;
    }
    .rating-badge.hold {
        background: linear-gradient(135deg, #F59E0B, #FBBF24);
        color: white;
    }
    .rating-badge.reduce {
        background: linear-gradient(135deg, #DC2626, #EF4444);
        color: white;
    }
    
    /* Executive Summary */
    .executive-summary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        font-size: 16px;
        line-height: 1.8;
        margin: 20px 0;
    }
    
    /* Insight Box */
    .insight-box {
        background: #F9FAFB;
        border-left: 4px solid #3B82F6;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .insight-box.risk {
        border-left-color: #DC2626;
    }
    
    .section-title {
        font-size: 24px;
        font-weight: 700;
        color: #1F2937;
        margin: 30px 0 20px 0;
        padding-bottom: 10px;
        border-bottom: 3px solid #3B82F6;
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
# Chart Functions (라인 차트 + 막대 차트만 사용)
# ==============================================================================

def plot_financial_trends(fund_data):
    """펀더멘털 성장 추세 (매출 + 영업이익률)"""
    if not fund_data or not isinstance(fund_data, dict):
        return plot_placeholder("재무 추세 데이터 없음")
    
    from plotly.subplots import make_subplots
    
    revenue = fund_data.get("매출", {})
    op_margin = fund_data.get("영업이익률", {})
    
    if not revenue.get("사용가능") or not op_margin.get("사용가능"):
        return plot_placeholder("데이터 부족")
    
    # 분기 수
    quarters = list(range(revenue.get("분기수", 20)))
    
    # 기울기로 과거 값 역산
    rev_current = revenue.get("최신값", 0)
    rev_slope = revenue.get("기울기", 0)
    revenues = [rev_current - rev_slope * (len(quarters)-1-i) for i in quarters]
    
    margin_current = op_margin.get("최신값", 0)
    margin_slope = op_margin.get("기울기", 0)
    margins = [(margin_current - margin_slope * (len(quarters)-1-i)) * 100 for i in quarters]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 매출 막대
    fig.add_trace(
        go.Bar(x=quarters, y=revenues, name="매출액 (조원)", marker_color='#3B82F6'),
        secondary_y=False
    )
    
    # 영업이익률 라인
    fig.add_trace(
        go.Scatter(x=quarters, y=margins, name="영업이익률 (%)", 
                   line=dict(color='#DC2626', width=3), mode='lines+markers'),
        secondary_y=True
    )
    
    fig.update_xaxes(title_text="분기")
    fig.update_yaxes(title_text="매출 (조원)", secondary_y=False)
    fig.update_yaxes(title_text="영업이익률 (%)", secondary_y=True)
    
    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white'
    )
    
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

def plot_drawdown_chart(price_history):
    """수중 차트 (Drawdown Analysis)"""
    if not price_history or len(price_history) < 2:
        return plot_placeholder("가격 데이터 없음")
    
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
        height=280,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
        showlegend=False
    )
    
    return fig

def plot_return_distribution(price_history):
    """수익률 분포 + VaR"""
    if not price_history or len(price_history) < 10:
        return plot_placeholder("데이터 부족")
    
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
        height=280,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
        showlegend=False
    )
    
    return fig

def plot_moving_averages(price_block):
    """장기 이동평균선 추세"""
    if not price_block:
        return plot_placeholder("가격 데이터 없음")
    
    current = price_block.get("현재가", 0)
    ma200 = price_block.get("200일선", 0)
    ma300 = price_block.get("300일선", 0)
    
    if not current or not ma200:
        return plot_placeholder("이동평균 데이터 부족")
    
    categories = ['300일선', '200일선', '현재가']
    values = [ma300 if ma300 else 0, ma200, current]
    colors = ['#94A3B8', '#64748B', '#059669']
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=[f"{v:,.0f}원" for v in values],
        textposition='outside'
    ))
    
    fig.update_layout(
        yaxis_title="가격 (원)",
        height=280,
        margin=dict(l=0, r=0, t=20, b=0),
        plot_bgcolor='white',
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
    st.markdown('<div class="section-title">투자 의견 요약</div>', unsafe_allow_html=True)
    
    rating = llm_data.get("investment_rating", "HOLD")
    target = llm_data.get("target_price", 0)
    current = llm_data.get("current_price", 0)
    upside = llm_data.get("upside_pct", 0)
    
    # 투자의견 배지
    rating_class = rating.lower() if rating.lower() in ['buy', 'hold', 'reduce'] else 'hold'
    st.markdown(f"""
    <div class="rating-badge {rating_class}">
        투자의견: {rating}
    </div>
    """, unsafe_allow_html=True)
    
    # 목표가 및 상승여력
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{current:,.0f} 원")
    col2.metric("목표주가", f"{target:,.0f} 원")
    col3.metric("상승여력", f"{upside:+.1f}%")
    
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
            <h4 style="margin-top:0;">💡 핵심 논거</h4>
            <p style="margin-bottom:0;">{llm_data.get('key_thesis', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="insight-box risk">
            <h4 style="margin-top:0;">⚠️ 주요 리스크</h4>
            <p style="margin-bottom:0;">{llm_data.get('primary_risk', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

def render_fundamental(long_data, llm_data):
    st.markdown('<div class="section-title">📈 펀더멘털 성장 추세</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.5, 1], gap="large")
    
    with col1:
        financial_trends = long_data.get('financial_trends', {})
        st.plotly_chart(plot_financial_trends(financial_trends), use_container_width=True)
    
    with col2:
        st.markdown(f"""
        <div class="insight-box">
            <h4>📊 분석</h4>
            <p>{llm_data.get('fundamental_analysis', '재무 분석 중...')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

def render_valuation(long_data, llm_data):
    st.markdown('<div class="section-title">💰 밸류에이션 분석</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        peg = long_data.get('peg_ratio', 0)
        roe = long_data.get('roe', 0)
        current_ratio = long_data.get('current_ratio', 0)
        
        st.plotly_chart(plot_valuation_bars(peg, roe, current_ratio), use_container_width=True)
    
    with col2:
        # 자동 밸류에이션 해석
        if peg < 1:
            val_opinion = f"🟢 PEG {peg:.2f}는 적정 수준 대비 저평가 구간입니다."
        elif peg < 2:
            val_opinion = f"🟡 PEG {peg:.2f}는 적정 밸류에이션 구간입니다."
        else:
            val_opinion = f"🔴 PEG {peg:.2f}는 과열 구간입니다."
        
        st.markdown(f"""
        <div class="insight-box">
            <h4>💡 밸류에이션 의견</h4>
            <p><strong>{val_opinion}</strong></p>
            <p style="margin-top:10px;">
            • PEG Ratio: {peg:.2f}<br>
            • ROE: {roe*100:.1f}% {"(우수)" if roe > 0.15 else "(보통)" if roe > 0.08 else "(개선필요)"}<br>
            • 유동비율: {current_ratio:.2f}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

def render_technical(mid_data, llm_data):
    st.markdown('<div class="section-title">📉 RSI 분석</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1.5], gap="large")
    
    with col1:
        rsi_value = mid_data.get('rsi_value', 50)
        st.plotly_chart(plot_rsi_bar(rsi_value), use_container_width=True)
    
    with col2:
        # RSI 자동 해석
        if rsi_value > 70:
            rsi_signal = "🔴 과매수"
            rsi_desc = f"RSI {rsi_value:.0f}은 과매수 구간입니다. 단기 조정 가능성에 유의하시기 바랍니다."
        elif rsi_value < 30:
            rsi_signal = "🟢 과매도"
            rsi_desc = f"RSI {rsi_value:.0f}은 과매도 구간입니다. 기술적 반등 가능성이 높아지고 있습니다."
        else:
            rsi_signal = "🟡 중립"
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

def render_strategy(short_data):
    st.markdown('<div class="section-title">3. 투자 전략 (단기)</div>', unsafe_allow_html=True)
    
    st.info(f"**전략:** {short_data.get('candle_pattern', 'N/A')}")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("피봇 포인트", f"{short_data.get('pivot_point', 0):,.0f} 원")
    col2.metric("1차 저항", f"{short_data.get('r1', 0):,.0f} 원")
    col3.metric("1차 지지", f"{short_data.get('s1', 0):,.0f} 원")

def render_risk_analysis(long_data):
    """리스크 분석 섹션"""
    st.markdown('<div class="section-title">4. 리스크 분석</div>', unsafe_allow_html=True)
    
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
        col2.metric("VaR 5%", f"{risk_metrics.get('var_5_pct', 0):.2f}%")
        col3.metric("변동성 (연간)", f"{risk_metrics.get('volatility', 0)*100:.1f}%")
    
    # 장기 이평선
    st.markdown("**이동평균선 (장기 추세)**")
    price_block = long_data.get('price_block', {})
    st.plotly_chart(plot_moving_averages(price_block), use_container_width=True)

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
        current_price = llm_data.get("current_price", res.get("short_term", {}).get("pivot_point", 0))
     
        
        render_header(res["symbol"], company_name, current_price)
        
        # 탭 제거, 모든 콘텐츠를 한 페이지에 표시
        render_summary(llm_data)
        render_fundamental(res["long_term"], llm_data)
        render_valuation(res["long_term"], llm_data)
        render_technical(res["mid_term"], llm_data)
        render_strategy(res["short_term"])
        render_risk_analysis(res["long_term"])
        
        # 전문 리서치 보고서 섹션
        st.markdown("---")
        st.markdown('<div class="section-title">📄 전문 리서치 보고서</div>', unsafe_allow_html=True)
        report_text = llm_data.get("report_markdown", "보고서가 생성되지 않았습니다.")
        st.markdown(report_text)
    else:
        st.info("왼쪽 사이드바에서 종목 코드를 입력하고 [분석 실행] 버튼을 눌러주세요.")

if __name__ == "__main__":
    main()