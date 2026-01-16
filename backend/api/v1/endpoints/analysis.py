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
            "report": f"데이터 수집 실패로 보고서를 생성할 수 없습니다. (원인: {error_msg})"
        }

    # 4. LLM 보고서 생성
    # 종목 코드를 실제 회사 이름으로 치환 (정보가 있는 경우)
    company_name = td.info.get("longName") or td.info.get("shortName") or symbol
    
    analysis_data = {
        "symbol": symbol,
        "company_name": company_name,
        "long_term": long_res,
        "mid_term": mid_res,
        "short_term": short_res
    }
    
    # 캐시 확인: 오늘 날짜로 이미 생성된 보고서가 있는지 확인
    from datetime import datetime, date
    from models.report_cache import ReportCache
    
    today = date.today()
    cached_report = db.query(ReportCache).filter(
        ReportCache.symbol == symbol,
        ReportCache.report_date >= datetime.combine(today, datetime.min.time()),
        ReportCache.report_date < datetime.combine(today, datetime.max.time())
    ).first()
    
    if cached_report:
        print(f"[CACHE HIT] Using cached report for {symbol} from {cached_report.created_at}")
        llm_output = cached_report.llm_output
    else:
        print(f"[CACHE MISS] Generating new report for {symbol}")
        # 데이터 전처리: LLM에게 인간 친화적 형식으로 변환
        from services.preprocessing import (
            preprocess_financial_data,
            preprocess_technical_data,
            preprocess_short_term_data
        )
        
        analysis_data_preprocessed = {
            "symbol": symbol,
            "company_name": company_name,
            "long_term": preprocess_financial_data(long_res),
            "mid_term": preprocess_technical_data(mid_res),
            "short_term": preprocess_short_term_data(short_res)
        }
        
        llm_output = await llm_service.generate_report(analysis_data_preprocessed)
        
        # 캐시 저장
        try:
            cache_entry = ReportCache(
                symbol=symbol,
                report_date=datetime.now(),
                llm_output=llm_output
            )
            db.add(cache_entry)
            db.commit()
            print(f"[CACHE SAVED] Report cached for {symbol}")
        except Exception as e:
            print(f"[CACHE ERROR] Failed to save cache: {e}")
            db.rollback()
    
    return {
        "id": analysis_id,
        "status": "completed",
        "symbol": symbol,
        "company_name": company_name,
        "long_term": {
            "fundamental_trend": long_res.get("evidence", {}).get("판정", "N/A"),
            "revenue_slope": long_res.get("evidence", {}).get("재무추세", {}).get("매출", {}).get("기울기"),
            "peg_ratio": long_res.get("evidence", {}).get("밸류에이션", {}).get("trailingPEG", 0),
            "valuation_status": long_res.get("outlook", "N/A"),
            "message": f"재무 판정: {long_res.get('evidence', {}).get('판정', 'N/A')}, {long_res.get('outlook', 'N/A')}"
        },
        "mid_term": {
            "ma_trend": mid_res.get("outlook", "N/A"),
            "ma_state": f"Support: {mid_res.get('evidence', {}).get('지지선')}, Resistance: {mid_res.get('evidence', {}).get('저항선')}",
            "rsi_value": mid_res.get("evidence", {}).get("RSI", 0),
            "rsi_signal": "Neutral",
            "message": f"국면: {mid_res.get('evidence', {}).get('국면', 'N/A')}, {mid_res.get('outlook', 'N/A')}"
        },
        "short_term": {
            "candle_pattern": short_res.get("outlook", "N/A"),
            "volume_ratio": int(short_res.get("evidence", {}).get("전일", {}).get("거래량배수", 1.0) * 100),
            "pivot_point": short_res.get("evidence", {}).get("금일피봇", {}).get("Pivot", 0),
            "r1": short_res.get("evidence", {}).get("금일피봇", {}).get("R1", 0),
            "r2": short_res.get("evidence", {}).get("금일피봇", {}).get("R1", 0) * 1.02,
            "s1": short_res.get("evidence", {}).get("금일피봇", {}).get("S1", 0),
            "s2": short_res.get("evidence", {}).get("금일피봇", {}).get("S1", 0) * 0.98,
            "message": f"단기 전망: {short_res.get('outlook', 'N/A')}"
        },
        "llm_output": llm_output
    }

