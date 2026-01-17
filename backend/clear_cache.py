import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.session import SessionLocal
from models.report_cache import ReportCache

def clear_cache():
    db = SessionLocal()
    try:
        num_deleted = db.query(ReportCache).delete()
        db.commit()
        print(f"✅ 캐시 삭제 완료: {num_deleted}개의 항목이 제거되었습니다.")
    except Exception as e:
        db.rollback()
        print(f"❌ 캐시 삭제 실패: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_cache()
