import os
import uuid
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from vision.worker import process_video_async
from core.config import cfg
from core.db import db

router = APIRouter()

# 업로드 디렉토리 설정
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_DIR = os.path.join(BASE, "storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 허용된 비디오 확장자
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    비디오 파일 업로드 및 분석 시작

    - **file**: 업로드할 비디오 파일 (MP4, MOV, AVI, MKV 등)
    """
    # 파일 확장자 검증
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 없습니다.")

    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 파일 크기 검증 (100MB 제한)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    file.file.seek(0, 2)  # 파일 끝으로 이동
    file_size = file.file.tell()
    file.file.seek(0)  # 파일 시작으로 복귀

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. 최대 크기: 100MB, 현재 크기: {file_size / (1024*1024):.1f}MB"
        )

    try:
        # 고유 ID 생성
        video_id = str(uuid.uuid4())

        # 파일 저장 경로
        safe_filename = f"{video_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 파일 정보
        file_info = {
            "video_id": video_id,
            "original_filename": file.filename,
            "stored_filename": safe_filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file_ext,
            "upload_time": str(os.path.getctime(file_path))
        }

        # 백그라운드에서 비디오 분석 시작
        if background_tasks:
            background_tasks.add_task(process_video_async, video_id, file_path)
        else:
            # 백그라운드 태스크가 없는 경우 asyncio로 실행
            import asyncio
            asyncio.create_task(process_video_async(video_id, file_path))

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "비디오 업로드 완료. 분석이 시작되었습니다.",
                "data": {
                    "video_id": video_id,
                    "filename": file.filename,
                    "file_size": file_size,
                    "status": "processing"
                }
            }
        )

    except Exception as e:
        # 에러 발생 시 업로드된 파일 정리
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

        raise HTTPException(
            status_code=500,
            detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}"
        )