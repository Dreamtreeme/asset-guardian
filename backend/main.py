import logging
import sys

# 로깅 설정 (Docker 로그 출력을 위해 로컬뿐만 아니라 전체 설정)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from api.v1.api import api_router
from core.config import settings
from init_db import init_db

# 서버 시작 로그
logger.info("========================================")
logger.info(f"🚀 {settings.PROJECT_NAME} 시작 중...")
logger.info("========================================")

# 데이터베이스 초기화
try:
    init_db()
    logger.info("✅ 데이터베이스 초기화 완료")
except Exception as e:
    logger.error(f"❌ DB initialization failed: {e}")

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
