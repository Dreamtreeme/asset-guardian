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
    # TODO: DB에 기록하고 비동기 작업 생성
    # 임시로 고정 ID 반환 (실제로는 DB에서 생성된 ID 사용)
    return {"id": 1, "status": "pending", "symbol": analysis_in.symbol}

@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    *,
    db: Session = Depends(deps.get_db),
    analysis_id: int,
    symbol: str  # 쿠리 파라미터로 symbol 필수 입력
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
    
    # 3. 에러 처리: 데이터가 없는 경우
    if "error" in long_res or "error" in mid_res or "error" in short_res:
        error_msg = long_res.get("error") or mid_res.get("error") or short_res.get("error")
        return {
            "id": analysis_id,
            "status": "failed",
            "symbol": symbol,
            "long_term": {"message": f"에러: {error_msg}"},
            "mid_term": {"message": "데이터 수집 실패"},
            "short_term": {"message": "데이터 수집 실패"},
            "llm_output": {
                "investment_rating": "Neutral",
                "target_price": 0,
                "current_price": 0,
                "upside_pct": 0,
                "target_period_months": 12,
                "key_thesis": "데이터 수집 실패",
                "primary_risk": "시스템 오류",
                "report_markdown": f"데이터 수집 실패로 보고서를 생성할 수 없습니다. (원인: {error_msg})"
            }
        }

    # 4. LLM 보고서 생성
    company_name = td.info.get("longName") or td.info.get("shortName") or symbol
    
    # 캐시 또는 LLM 호출
    from datetime import datetime, date
    from models.report_cache import ReportCache
    from services.preprocessing import (
        preprocess_financial_data,
        preprocess_technical_data,
        preprocess_short_term_data
    )
    
    llm_output = None
    today = date.today()
    print(f"[DEBUG] Starting LLM/Cache flow for {symbol}")
    
    # 캐시 확인
    try:
        cached_report = db.query(ReportCache).filter(
            ReportCache.symbol == symbol,
            ReportCache.report_date >= datetime.combine(today, datetime.min.time()),
            ReportCache.report_date < datetime.combine(today, datetime.max.time())
        ).first()
        
        if cached_report:
            llm_output = cached_report.llm_output
            print(f"[DEBUG] Cache HIT - llm_output type: {type(llm_output)}, keys: {list(llm_output.keys()) if isinstance(llm_output, dict) else 'N/A'}")
        else:
            print(f"[DEBUG] Cache MISS - will call LLM")
    except Exception as cache_err:
        print(f"[DEBUG] Cache error: {cache_err}")
    
    # LLM 호출 및 캐시 저장
    if llm_output is None:
        print(f"[DEBUG] Calling LLM for {symbol}")
        analysis_data_preprocessed = {
            "symbol": symbol,
            "company_name": company_name,
            "long_term": preprocess_financial_data(long_res),
            "mid_term": preprocess_technical_data(mid_res),
            "short_term": preprocess_short_term_data(short_res)
        }
        
        llm_output = await llm_service.generate_report(analysis_data_preprocessed)
        print(f"[DEBUG] LLM returned - type: {type(llm_output)}, keys: {list(llm_output.keys()) if isinstance(llm_output, dict) else 'N/A'}")
        
        # 캐시 저장
        try:
            db.add(ReportCache(
                symbol=symbol,
                report_date=datetime.now(),
                llm_output=llm_output
            ))
            db.commit()
            print(f"[DEBUG] Cache saved successfully")
        except Exception as save_err:
            print(f"[DEBUG] Cache save failed: {save_err}")
            db.rollback()
    
    print(f"[DEBUG] Before return - llm_output type: {type(llm_output)}, keys: {list(llm_output.keys()) if isinstance(llm_output, dict) else 'N/A'}")
    
    # 응답 데이터 구조화 (가독성 개선)
    long_evidence = long_res.get("evidence", {})
    long_trends = long_evidence.get("재무추세", {})
    long_valuation = long_evidence.get("밸류에이션", {})
    
    mid_evidence = mid_res.get("evidence", {})
    
    short_evidence = short_res.get("evidence", {})
    short_pivot = short_evidence.get("금일피봇", {})
    short_yesterday = short_evidence.get("전일", {})
    
    return {
        "id": analysis_id,
        "status": "completed",
        "symbol": symbol,
        "company_name": company_name,
        "long_term": {
            "fundamental_trend": long_evidence.get("판정", "N/A"),
            "revenue_slope": long_trends.get("매출", {}).get("기울기"),
            "peg_ratio": long_valuation.get("trailingPEG", 0),
            "valuation_status": long_res.get("outlook", "N/A"),
            "message": f"재무 판정: {long_evidence.get('판정', 'N/A')}, {long_res.get('outlook', 'N/A')}"
        },
        "mid_term": {
            "ma_trend": mid_res.get("outlook", "N/A"),
            "ma_state": f"Support: {mid_evidence.get('지지선')}, Resistance: {mid_evidence.get('저항선')}",
            "rsi_value": mid_evidence.get("RSI", 0),
            "rsi_signal": "Neutral",
            "message": f"국면: {mid_evidence.get('국면', 'N/A')}, {mid_res.get('outlook', 'N/A')}"
        },
        "short_term": {
            "candle_pattern": short_res.get("outlook", "N/A"),
            "volume_ratio": int(short_yesterday.get("거래량배수", 1.0) * 100),
            "pivot_point": short_pivot.get("Pivot", 0),
            "r1": short_pivot.get("R1", 0),
            "s1": short_pivot.get("S1", 0),
            "message": f"단기 전망: {short_res.get('outlook', 'N/A')}"
        },
        "llm_output": llm_output
    }

