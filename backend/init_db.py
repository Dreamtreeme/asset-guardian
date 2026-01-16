"""
데이터베이스 테이블 초기화 스크립트
애플리케이션 시작 시 필요한 테이블을 자동 생성
"""
from sqlalchemy import create_engine, text
from core.config import settings

def init_db():
    """데이터베이스 테이블 초기화"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # report_cache 테이블 생성
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS report_cache (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                report_date TIMESTAMP NOT NULL,
                llm_output JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # 인덱스 생성
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_symbol_date 
            ON report_cache(symbol, report_date);
        """))
        
        conn.commit()
        print("[DB INIT] report_cache table created successfully")

if __name__ == "__main__":
    init_db()
