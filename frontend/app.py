import streamlit as st
import pandas as pd
import numpy as np
import time

# --- [설정] ---
st.set_page_config(page_title="Stock Evidence Board", layout="wide")

# --- [Session State 초기화] ---
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

# --- [내비게이션 기능] ---
def go_to_page(page_name):
    st.session_state.page = page_name

# --- [Sidebar] ---
with st.sidebar:
    st.title("Menu")
    if st.button("분석 실행", use_container_width=True):
        go_to_page("Home")
    if st.button("분석 이력", use_container_width=True):
        go_to_page("History")
    
    st.divider()

# --- [Page 1: 분석 실행 및 결과] ---
if st.session_state.page == "Home":
    st.title("종목 분석")
    
    # 1. 입력 섹션
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            ticker = st.selectbox("종목 선택", ["삼성전자", "SK하이닉스", "현대차", "LG에너지솔루션"])
        with col2:
            mode = st.segmented_control("분석 모드", ["장기", "중단기", "전일", "금일 예상"], default="중단기")
        with col3:
            st.write("") # 간격 맞춤
            run_btn = st.button("분석 시작", type="primary", use_container_width=True)

    # 2. 분석 로직 (Mockup)
    if run_btn:
        with st.status("분석 프로세스 가동 중...", expanded=True) as status:
            st.write("데이터 수집 단계: 재무제표 및 공시 로드...")
            time.sleep(1)
            st.write("산식 적용 단계: ROE/PER 가중치 계산...")
            time.sleep(1)
            st.write("리포트 인용 단계: LLM 핵심 문장 추출...")
            time.sleep(2)
            status.update(label="분석 완료", state="complete", expanded=False)
        
        # 결과 데이터 저장 (실제로는 API 결과값)
        st.session_state.analysis_data = {
            "ticker": ticker,
            "score": 78,
            "status": "강세 근거 우세",
            "date": "2026-01-15",
            "run_id": f"RID-{int(time.time())}"
        }

    # 3. 결과 출력 섹션
    if st.session_state.analysis_data:
        res = st.session_state.analysis_data
        
        # 상단 요약 카드
        st.subheader(f"{res['ticker']} 분석 결과")
        c1, c2, c3 = st.columns(3)
        c1.metric("종합 점수", f"{res['score']} / 100", delta="5")
        c2.metric("상태", res['status'])
        c3.info(f"Run ID: {res['run_id']}\n\n기준일: {res['date']}")

        # 상세 탭 (근거 중심)
        t1, t2, t3 = st.tabs(["재무 근거", "차트 신호", "리포트 인용"])
        
        with t1:
            st.write("#### 핵심 재무 메트릭")
            m1, m2, m3 = st.columns(3)
            m1.metric("PER", "12.5", "-1.2")
            m2.metric("PBR", "1.4", "+0.1")
            m3.metric("ROE", "15.2%", "+2.1%")
            with st.expander("재무 점수 산정 공식 보기"):
                st.latex(r"Score_{Finance} = \frac{\sum (Metric \times Weight)}{Target_{Avg}}")
        
        with t2:
            st.write("#### 기술적 지표 신호")
            chart_data = pd.DataFrame(np.random.randn(20, 3), columns=['Price', 'MA20', 'MA60'])
            st.line_chart(chart_data)
            st.success("이동평균선 60일 지지선 확인됨 (신뢰도: 85%)")

        with t3:
            st.write("#### 리포트 핵심 인용")
            st.markdown("""
            > "HBM3E 양산 가시화로 인한 2분기 실적 턴어라운드 전망"  
            > **-- K증권 리포트 (2026-01-10)**
            
            > "공급 과잉 우려 해소 및 가전 부문 프리미엄 전략 유효"  
            > **-- H투자연구소 (2026-01-12)**
            """)

# --- [Page 2: 히스토리] ---
elif st.session_state.page == "History":
    st.title("분석 실행 이력")
    
    # 더미 데이터 표
    history_df = pd.DataFrame({
        "Run ID": ["RID-12345", "RID-12346", "RID-12347"],
        "종목": ["삼성전자", "현대차", "SK하이닉스"],
        "점수": [78, 82, 65],
        "모드": ["중단기", "장기", "금일 예상"],
        "시각": ["2026-01-15 10:00", "2026-01-14 15:30", "2026-01-14 09:10"]
    })
    st.table(history_df)
    
    if st.button("이력 초기화"):
        st.toast("이력이 삭제되었습니다.")
