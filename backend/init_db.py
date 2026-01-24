"""
데이터베이스 테이블 초기화 스크립트
애플리케이션 시작 시 필요한 테이블을 자동 생성
"""
from db.session import engine, Base
from db.base import *  # 모든 모델을 import하여 Base에 등록

def init_db():
    """데이터베이스 테이블 초기화"""
    try:
        # Base에 등록된 모든 모델의 테이블을 자동 생성
        Base.metadata.create_all(bind=engine)
        pass  # 테이블 생성 완료
    except Exception as e:
        print(f"[DB INIT ERROR] Failed to create tables: {e}")
        raise

if __name__ == "__main__":
    init_db()
