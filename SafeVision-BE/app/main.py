from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import cfg, save_config
from core.broker import broker
from core.db import init_db
from app.api.uploads import router as upload_router
from app.api.alerts import router as alerts_router
from app.api.rules import router as rules_router
from logging_config import setup_logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로깅 시스템 초기화
logger, log_file = setup_logging()
logger.info(f"Smart Safety 시스템 시작 - 로그 파일: {log_file}")

app = FastAPI(
    title="Smart Safety (Local)",
    description="동영상 분석 기반 안전 모니터링 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_start():
    logger.info("데이터베이스 초기화 시작")
    await init_db()
    logger.info("데이터베이스 초기화 완료")

    logger.info("라우터 등록 시작")
    app.include_router(upload_router, prefix="/api/v1", tags=["uploads"])
    app.include_router(alerts_router, prefix="/api/v1", tags=["alerts"])
    app.include_router(rules_router, prefix="/api/v1", tags=["rules"])
    logger.info("라우터 등록 완료")

    logger.info("Smart Safety 시스템 시작 완료")

@app.get("/")
async def root():
    return {"message": "Smart Safety API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
