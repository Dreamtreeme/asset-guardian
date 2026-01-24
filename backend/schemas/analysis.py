from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class AnalysisBase(BaseModel):
    symbol: str

class AnalysisCreate(AnalysisBase):
    pass

class AnalysisOut(AnalysisBase):
    id: int
    status: str
    created_at: Optional[datetime] = None
    company_name: Optional[str] = None
    long_term: Optional[Dict] = None
    mid_term: Optional[Dict] = None
    short_term: Optional[Dict] = None
    llm_output: Optional[Dict] = None  # LLM 생성 데이터

    class Config:
        from_attributes = True
