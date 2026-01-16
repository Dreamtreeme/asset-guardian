import streamlit as st
import pandas as pd
import numpy as np
import time
import requests

# --- [설정] ---
st.set_page_config(page_title="Asset Guardian | 4-Stage Analysis", layout="wide", initial_sidebar_state="expanded")

# --- [스타일링] ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- [Session State 초기화] ---
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# --- [Header] ---
st.title("🛡️ Asset Guardian")
st.markdown("### 4단계 시계열 분석 프레임워크")
st.caption("장기(가치) → 중기(추세) → 단기(수급) → 대응(전략)")

# --- [Sidebar: Input Section] ---
with st.sidebar:
    st.header("🔍 종목 분석")
    ticker = st.selectbox("분석할 종목을 선택하세요", 
                          ["삼성전자 (005930)", "SK하이닉스 (000660)", "현대차 (005380)", "LG에너지솔루션 (373220)", "Apple (AAPL)"])
    
    st.divider()
    
    # 분석 시작 버튼
    if st.button("🚀 분석하기", type="primary", use_container_width=True):
        with st.status("분석 데이터를 수집하고 있습니다...", expanded=True) as status:
            st.write("1단계: 장기 펀더멘컬 데이터 로드 중...")
            time.sleep(1)
            st.write("2단계: 중기 이동평균선 및 모멘텀 계산 중...")
            time.sleep(1)
            st.write("3단계: 전일 캔들 및 거래량 패턴 매칭 중...")
            time.sleep(1)
            st.write("4단계: LLM 종합 투자 의견 생성 중...")
            time.sleep(1)
            
            # 실제로는 API 호출 (여기서는 Mockup 데이터를 backend에서 가져오는 시늉)
            # res = requests.post("http://backend:8000/api/v1/analysis/", json={"symbol": ticker})
            # analysis_id = res.json()["id"]
            # result = requests.get(f"http://backend:8000/api/v1/analysis/{analysis_id}")
            
            # Mockup result inspired by '투자전략.md'
            st.session_state.analysis_result = {
                "symbol": ticker.split(" ")[0],
                "long_term": {
                    "fundamental_trend": "상승 (Growth)",
                    "slope": 0.82,
                    "peg": 0.45,
                    "status": "강력 매수 (저평가)",
                    "description": "최근 8분기 매출 및 FCF 선형회귀 기울기가 양수이며, PEG가 0.5 미만으로 극저평가 구간입니다."
                },
                "mid_term": {
                    "trend": "강력 상승 (정배열)",
                    "ma_align": "Price > MA20 > MA60 > MA200",
                    "rsi": 58,
                    "status": "상승 추세 유지",
                    "description": "모든 주요 이평선이 정배열을 유지하고 있으며, RSI가 50선을 상향 돌파 후 안정적인 매수세를 유지 중입니다."
                },
                "short_term": {
                    "candle": "장대양봉 (Long Body)",
                    "volume_ratio": 185,
                    "pivot": 185000,
                    "r1": 188500, "r2": 192000,
                    "s1": 182000, "s2": 178000,
                    "description": "전일 거래량이 20일 평균 대비 185% 급증하며 돌파 신호가 발생했습니다. Pivot 지지 여부가 핵심입니다."
                },
                "conclusion": "Strong Buy",
                "summary": "장기적 가치 매력도가 매우 높고 중기 추세가 살아있는 가운데, 단기 수급 폭발이 확인됨. 적극 매수 전략 유효."
            }
            status.update(label="분석이 완료되었습니다!", state="complete", expanded=False)

# --- [Main Content: Results Section] ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    
    # 종합 의견 카드
    st.markdown(f"""
        <div class="status-card">
            <h4>종합 투자의견: <span style="color: #ff4b4b;">{res['conclusion']}</span></h4>
            <p>{res['summary']}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 3개 탭 구성
    tab_long, tab_mid, tab_short = st.tabs(["📊 장기 (가치/성장)", "📈 중기 (추세/파동)", "📅 단기 (수급/대응)"])
    
    with tab_long:
        st.subheader("1단계: 숲을 보고 (Long-term)")
        c1, c2, c3 = st.columns(3)
        c1.metric("펀더멘탈 추세", res['long_term']['fundamental_trend'])
        c2.metric("PEG Ratio", res['long_term']['peg'], delta="Good", delta_color="normal")
        c3.metric("가치 평가", res['long_term']['status'])
        
        st.info(f"**분석 결과:** {res['long_term']['description']}")
        
        # 가상의 성장 차트
        st.caption("최근 8분기 수익성 추이 (Linear Regression Analysis)")
        chart_data = pd.DataFrame({
            'Quarter': ['22.3Q', '22.4Q', '23.1Q', '23.2Q', '23.3Q', '23.4Q', '24.1Q', '24.2Q'],
            'Revenue': [100, 105, 115, 120, 140, 160, 185, 210]
        })
        st.line_chart(chart_data.set_index('Quarter'))

    with tab_mid:
        st.subheader("2단계: 나무를 살피며 (Mid-term)")
        m1, m2, m3 = st.columns(3)
        m1.metric("이평선 배열", res['mid_term']['trend'])
        m2.metric("RSI (14)", res['mid_term']['rsi'])
        m3.metric("현재 상태", res['mid_term']['status'])
        
        st.success(f"**분석 결과:** {res['mid_term']['description']}\n\n**배열 상태:** `{res['mid_term']['ma_align']}`")
        
        # 가상의 RSI 게이지 대체 (수평 바)
        st.write("RSI Momentum Gauge")
        rsi_val = res['mid_term']['rsi']
        st.progress(rsi_val / 100)
        st.caption(f"30(침체) ----- 50(보통) ----- 70(과열) | 현재: {rsi_val}")

    with tab_short:
        st.subheader("3&4단계: 날씨 확인 및 대응 (Short-term)")
        s1, s2 = st.columns([1, 2])
        with s1:
            st.write("#### 전일 수급 신호")
            st.metric("추천 패턴", res['short_term']['candle'])
            st.metric("거래량 비율", f"{res['short_term']['volume_ratio']}%", delta="150% 초과", delta_color="normal")
        
        with s2:
            st.write("#### 오늘 대응 가이드 (Pivot Point)")
            pivot_df = pd.DataFrame({
                "레벨": ["2차 저항 (R2)", "1차 저항 (R1)", "기준점 (P)", "1차 지지 (S1)", "2차 지지 (S2)"],
                "가격": [res['short_term']['r2'], res['short_term']['r1'], res['short_term']['pivot'], res['short_term']['s1'], res['short_term']['s2']]
            })
            st.table(pivot_df)
            
        st.warning(f"**전략 제언:** {res['short_term']['description']}")

else:
    st.info("왼쪽 사이드바에서 종목을 선택하고 '분석하기' 버튼을 클릭해 주세요.")
    
    # 가이드 섹션
    with st.expander("분석 프레임워크 안내"):
        st.markdown("""
        자산 가디언(Asset Guardian)은 레이 달리오의 펀더멘탈 분석과 기술적 분석을 결합한 4단계 시스템을 사용합니다.
        1. **장기**: 8~12분기 실적 추세 및 PEG를 이용한 적정 가치 평가
        2. **중기**: 이동평균선 정배열 상태 및 RSI를 통한 추세 확인
        3. **단기**: 전일 캔들과 거래량을 통한 시장 심리 및 수급 분석
        4. **금일**: 피봇 포인트를 활용한 실시간 진입/청산 전략 제시
        """)
