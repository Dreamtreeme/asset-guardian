from services.collector import collector
from services.engine.finance import analyze_long_term
from services.engine.technical import analyze_mid_term, analyze_short_term
from services.llm import llm_service
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api import deps
from schemas.analysis import AnalysisCreate, AnalysisOut

router = APIRouter()

@router.post("/", response_model=AnalysisOut)
async def create_analysis(
    *,
    db: Session = Depends(deps.get_db),
    analysis_in: AnalysisCreate
):
    """
    분석 실행 API
    """
    # 실제로는 여기서 DB에 기록하고 비동기 작업을 생성하지만,
    # 지금은 간단하게 ID만 넘기는 스텁 유지
    return {"id": 1, "status": "pending", "symbol": analysis_in.symbol}

@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    *,
    db: Session = Depends(deps.get_db),
    analysis_id: int,
    symbol: str = "AAPL" # 임시로 symbol을 쿼리로 받거나 DB에서 조회해야 함
):
    """
    분석 상태 조회 API
    """
    # 1. 데이터 수집
    td = await collector.fetch_ticker_data(symbol)
    
    # 2. 엔진 실행
    long_res = analyze_long_term(td)
    mid_res = analyze_mid_term(td)
    short_res = analyze_short_term(td)
    
    # 3. LLM 보고서 생성
    analysis_data = {
        "symbol": symbol,
        "long_term": long_res,
        "mid_term": mid_res,
        "short_term": short_res
    }
    report = await llm_service.generate_report(analysis_data)
    
    return {
        "id": analysis_id,
        "status": "completed",
        "symbol": symbol,
        "long_term": {
            "fundamental_trend": long_res["evidence"]["판정"],
            "revenue_slope": long_res["evidence"]["재무추세"]["매출"].get("기울기"),
            "peg_ratio": long_res["evidence"]["밸류에이션"].get("trailingPEG", 0),
            "valuation_status": long_res["outlook"],
            "message": f"재무 판정: {long_res['evidence']['판정']}, {long_res['outlook']}"
        },
        "mid_term": {
            "ma_trend": mid_res["outlook"],
            "ma_state": f"Support: {mid_res['evidence']['지지선']}, Resistance: {mid_res['evidence']['저항선']}",
            "rsi_value": mid_res["evidence"]["RSI"],
            "rsi_signal": "Neutral",
            "message": f"국면: {mid_res['evidence']['국면']}, {mid_res['outlook']}"
        },
        "short_term": {
            "candle_pattern": short_res["outlook"],
            "volume_ratio": int(short_res["evidence"]["전일"]["거래량배수"] * 100),
            "pivot_point": short_res["evidence"]["금일피봇"]["Pivot"],
            "r1": short_res["evidence"]["금일피봇"]["R1"],
            "r2": short_res["evidence"]["금일피봇"]["R1"] * 1.02,
            "s1": short_res["evidence"]["금일피봇"]["S1"],
            "s2": short_res["evidence"]["금일피봇"]["S1"] * 0.98,
            "message": f"단기 전망: {short_res['outlook']}"
        },
        "report": report
    }
