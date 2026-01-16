"""
LLM 보고서 캐시 모델
같은 날 같은 종목에 대한 중복 LLM 호출 방지
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ReportCache(Base):
    __tablename__ = "report_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    report_date = Column(DateTime, nullable=False, index=True)
    llm_output = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 복합 인덱스: (symbol, report_date)로 빠른 조회
    __table_args__ = (
        Index('idx_symbol_date', 'symbol', 'report_date'),
    )
