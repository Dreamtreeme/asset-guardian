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
    return {"id": analysis_id, "status": "completed", "symbol": "AAPL"}
