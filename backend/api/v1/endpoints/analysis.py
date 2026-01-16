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
    return {"id": 1, "status": "pending", "symbol": analysis_in.symbol}

@router.get("/{analysis_id}", response_model=AnalysisOut)
async def get_analysis(
    *,
    db: Session = Depends(deps.get_db),
    analysis_id: int
):
    """
    분석 상태 조회 API
    """
    return {
        "id": analysis_id,
        "status": "completed",
        "symbol": "AAPL",
        "long_term": {
            "fundamental_trend": "Growth",
            "revenue_slope": 0.85,
            "peg_ratio": 0.45,
            "valuation_status": "강력 매수 (매우 저평가)",
            "message": "매출 및 이익 성장세가 뚜렷하며 PEG 기준 현저한 저평가 상태입니다."
        },
        "mid_term": {
            "ma_trend": "강력 상승 (정배열)",
            "ma_state": "Price > MA20 > MA60 > MA200",
            "rsi_value": 55,
            "rsi_signal": "매수세 유입",
            "message": "주요 이동평균선이 정배열 상태를 유지하며 완만한 상승 흐름을 보이고 있습니다."
        },
        "short_term": {
            "candle_pattern": "장대양봉 (Long Body Bullish)",
            "volume_ratio": 185,
            "pivot_point": 185.5,
            "r1": 188.2,
            "r2": 190.5,
            "s1": 183.0,
            "s2": 180.5,
            "message": "전일 강력한 수급과 함께 장대양봉이 발생했습니다. 시초가 Pivot 상단 유지 시 R1까지의 상승을 기대할 수 있습니다."
        }
    }
