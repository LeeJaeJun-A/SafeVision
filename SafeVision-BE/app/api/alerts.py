import json
import asyncio
import os
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from core.db import db
from core.broker import broker
from rules.schemas import AlertResponse, AlertStatusUpdate, AlertStatus

router = APIRouter()

@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    limit: int = Query(50, ge=1, le=100, description="조회할 최대 개수"),
    offset: int = Query(0, ge=0, description="건너뛸 개수"),
    rule_type: Optional[str] = Query(None, description="규칙 타입으로 필터링"),
    video_id: Optional[str] = Query(None, description="비디오 ID로 필터링"),
    severity: Optional[str] = Query(None, description="심각도로 필터링"),
    status: Optional[str] = Query(None, description="상태로 필터링 (unprocessed/processing/completed)")
):
    """
    알림 목록 조회

    - **limit**: 조회할 최대 개수 (1-100, 기본값: 50)
    - **offset**: 건너뛸 개수 (기본값: 0)
    - **rule_type**: 규칙 타입으로 필터링
    - **video_id**: 비디오 ID로 필터링
    - **severity**: 심각도로 필터링 (low, medium, high, critical)
    - **status**: 상태로 필터링 (unprocessed, processing, completed)
    """
    try:
        # 데이터베이스에서 알림 조회
        alerts = await db.get_alerts(limit=limit, offset=offset, rule_type=rule_type,
                                   video_id=video_id, severity=severity, status=status)

        return alerts

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"알림 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """
    특정 알림 조회

    - **alert_id**: 조회할 알림 ID
    """
    try:
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

        return alert

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"알림 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/alerts/{alert_id}/video")
async def get_alert_video(alert_id: str):
    """
    알림에 대한 비디오 클립 다운로드

    - **alert_id**: 알림 ID (accident ID)
    """
    try:
        # 알림 정보 조회
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

        video_clip_path = alert.get('video_clip_path')
        if not video_clip_path or not os.path.exists(video_clip_path):
            raise HTTPException(status_code=404, detail="비디오 클립을 찾을 수 없습니다.")

        # 파일 다운로드
        from fastapi.responses import FileResponse
        return FileResponse(
            video_clip_path,
            media_type="video/mp4",
            filename=f"accident_{alert_id}.mp4"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"비디오 클립 다운로드 중 오류가 발생했습니다: {str(e)}"
        )

@router.patch("/alerts/{alert_id}/status")
async def update_alert_status(alert_id: str, status_update: AlertStatusUpdate):
    """
    알림 상태 변경

    - **alert_id**: 알림 ID
    - **status_update**: 변경할 상태 정보 (unprocessed/processing/completed)
    """
    try:
        # 알림 존재 여부 확인
        alert = await db.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

        # 상태 업데이트
        success = await db.update_alert_status(
            alert_id,
            status_update.status.value
        )

        if not success:
            raise HTTPException(status_code=400, detail="상태 업데이트에 실패했습니다.")

        return {
            "success": True,
            "message": f"알림 상태가 '{status_update.status.value}'로 변경되었습니다.",
            "data": {
                "alert_id": alert_id,
                "new_status": status_update.status.value,
                "processed_at": datetime.now().isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상태 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/alerts/stats/unprocessed")
async def get_unprocessed_alerts_count():
    """
    미처리 알림 수 조회

    처리 상태가 'unprocessed'인 알림의 개수를 반환합니다.
    """
    try:
        count = await db.get_unprocessed_alerts_count()
        return {
            "success": True,
            "data": {
                "unprocessed_count": count
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"미처리 알림 수 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.options("/sse/alerts")
async def sse_alerts_options():
    """
    iOS SSE 연결을 위한 CORS preflight 요청 처리
    """
    return {
        "status": "ok",
        "message": "SSE 연결 준비 완료"
    }

@router.get("/sse/alerts")
async def sse_alerts(request: Request):
    """
    Server-Sent Events를 통한 실시간 알림 스트리밍

    클라이언트가 이 엔드포인트에 연결하면 새로운 알림이 발생할 때마다 실시간으로 전송됩니다.
    """

    async def event_generator():
        # SSE 연결 설정
        yield "retry: 10000\n\n"  # 재연결 간격 10초

        # 브로커에 연결
        queue = await broker.connect()

        try:
            while True:
                # 연결 상태 확인
                if await request.is_disconnected():
                    break

                try:
                    # 메시지 대기 (타임아웃 30초)
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # SSE 형식으로 메시지 전송
                    if message.get('event_type') == 'alert':
                        yield f"event: alert\n"
                        yield f"data: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
                    elif message.get('event_type') == 'rule_update':
                        yield f"event: rule_update\n"
                        yield f"data: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
                    elif message.get('event_type') == 'config_update':
                        yield f"event: config_update\n"
                        yield f"data: {json.dumps(message['data'], ensure_ascii=False)}\n\n"
                    else:
                        # 일반 메시지
                        yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

                except asyncio.TimeoutError:
                    # 타임아웃 시 연결 유지를 위한 하트비트
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"

        except Exception as e:
            print(f"SSE 스트림 오류: {e}")
        finally:
            # 연결 해제
            await broker.disconnect(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control, Content-Type, Authorization",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Credentials": "true",
            "X-Accel-Buffering": "no",  # Nginx 프록시에서 버퍼링 방지
            "Content-Encoding": "identity",  # 압축 방지
            "Transfer-Encoding": "chunked"  # 청크 전송 인코딩
        }
    )

@router.get("/sse/status")
async def get_sse_status():
    """
    SSE 연결 상태 확인
    """
    try:
        connection_count = broker.get_connection_count()
        return {
            "success": True,
            "data": {
                "active_connections": connection_count,
                "status": "active" if connection_count > 0 else "idle"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SSE 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )
