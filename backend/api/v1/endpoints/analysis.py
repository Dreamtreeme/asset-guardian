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
                "investment_rating": "분석 불가",
                "current_price": 0,
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

    
    # 캐시 확인
    try:
        cached_report = db.query(ReportCache).filter(
            ReportCache.symbol == symbol,
            ReportCache.report_date >= datetime.combine(today, datetime.min.time()),
            ReportCache.report_date < datetime.combine(today, datetime.max.time())
        ).first()
        
        if cached_report:
            llm_output = cached_report.llm_output
    except Exception:
        pass

    # 리스크 지표 계산
    import numpy as np
    var_5_pct = 0
    volatility = 0
    if hasattr(td, 'px_10y') and not td.px_10y.empty:
        daily_returns = td.px_10y["Close"].pct_change().dropna()
        var_5_pct = float(daily_returns.quantile(0.05)) if len(daily_returns) > 0 else 0
        volatility = float(daily_returns.std() * np.sqrt(252)) if len(daily_returns) > 0 else 0

    # LLM 호출 및 캐시 저장
    if llm_output is None:
        long_term_data = preprocess_financial_data(long_res)
        # 리스크 지표 추가 (LLM 참고용)
        long_term_data["risk_metrics_raw"] = {
            "var_5_pct": var_5_pct,
            "volatility": volatility,
            "max_drawdown_5y": long_res.get("evidence", {}).get("장기추세", {}).get("최근5년_MDD", 0)
        }

        analysis_data_preprocessed = {
            "symbol": symbol,
            "company_name": company_name,
            "long_term": long_term_data,
            "mid_term": preprocess_technical_data(mid_res),
            "short_term": preprocess_short_term_data(short_res)
        }
        
        llm_output = await llm_service.generate_report(analysis_data_preprocessed)

        # 캐시 저장
        try:
            db.add(ReportCache(
                symbol=symbol,
                report_date=datetime.now(),
                llm_output=llm_output
            ))
            db.commit()
        except Exception as save_err:
            db.rollback()
    

    
    # 응답 데이터 구조화 (가독성 개선)
    long_evidence = long_res.get("evidence", {})
    long_trends = long_evidence.get("재무추세", {})
    long_valuation = long_evidence.get("밸류에이션", {})
    
    mid_evidence = mid_res.get("evidence", {})
    
    short_evidence = short_res.get("evidence", {})
    short_pivot = short_evidence.get("금일피봇", {})
    short_yesterday = short_evidence.get("전일", {})
    
    # 상단에서 이미 리스크 지표 계산됨
    
    return {
        "id": analysis_id,
        "status": "completed",
        "symbol": symbol,
        "company_name": company_name,
        "long_term": {
            # 차트용 재무 추세 데이터
            "financial_trends": long_trends,
            
            # 차트용 가격 데이터 (최근 1년)
            "price_history": {
                "dates": [str(d) for d in td.px_10y.index[-252:].tolist()],
                "close": td.px_10y["Close"].iloc[-252:].tolist(),
                "ma200": td.px_10y["Close"].rolling(window=200).mean().iloc[-252:].tolist(),
                "ma300": td.px_10y["Close"].rolling(window=300).mean().iloc[-252:].tolist()
            } if hasattr(td, 'px_10y') and not td.px_10y.empty else {},
            
            # 리스크 지표
            "risk_metrics": {
                "max_drawdown_5y": long_evidence.get("장기추세", {}).get("최근5년_MDD", 0),
                "var_5_pct": var_5_pct,
                "volatility": volatility
            },
            
            # 밸류에이션 지표
            "peg_ratio": long_valuation.get("trailingPEG", 0),
            "roe": long_valuation.get("ROE", 0),
            "current_ratio": long_valuation.get("currentRatio", 0)
        },
        "mid_term": {
            "rsi_value": mid_evidence.get("RSI", 0)
        },
        "short_term": {
            "current_price": short_pivot.get("Pivot", 0) # 현재가 백업용
        },
        "llm_output": llm_output
    }

