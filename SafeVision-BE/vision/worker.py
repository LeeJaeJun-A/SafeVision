import os
import threading
import time
import asyncio
from typing import Dict, List, Any
from vision.detector import detector
from rules.engine import rule_engine
from core.db import db
from core.config import cfg
from logging_config import get_logger

class VideoProcessor:
    """비디오 처리 워커 클래스"""

    def __init__(self):
        self.processing_queue = []
        self.is_processing = False
        self.logger = get_logger('video_processor')

    async def process_video(self, video_id: str, video_path: str):
        """비디오 처리 메인 함수"""
        self.logger.info(f"비디오 처리 시작: {video_id} ({video_path})")

        try:
            # 설정 가져오기
            sample_fps = cfg.get('sample_fps', 5)
            confidence_threshold = cfg.get('confidence_threshold', 0.5)

            self.logger.info(f"처리 설정: sample_fps={sample_fps}, confidence_threshold={confidence_threshold}")

            # 감지기 설정 업데이트
            detector.update_confidence_threshold(confidence_threshold)

            # 비디오 프레임 분석
            self.logger.info(f"비디오 프레임 분석 시작...")
            frame_results = detector.detect_video_frames(video_path, sample_fps)

            if not frame_results:
                self.logger.error(f"비디오 분석 실패: {video_id}")
                return

            self.logger.info(f"분석 완료: {len(frame_results)} 프레임")

            # 분석 시작 시 규칙 새로고침 (동적 규칙 변경 반영)
            cfg.refresh_rules()
            rule_engine.reload_rules()

            # 각 프레임에 대해 규칙 평가
            total_alerts = 0
            total_frames = len(frame_results)

            for i, (frame_number, frame, detections, timestamp_ms) in enumerate(frame_results):
                self.logger.info(f"=== 프레임 {frame_number} 처리 중 ({i+1}/{total_frames}) ===")
                self.logger.info(f"탐지된 객체: {len(detections)}개")

                # 탐지된 객체 상세 정보
                for det in detections:
                    self.logger.info(
                        f"  - {det['label']} (ID: {det['track_id']}): "
                        f"conf={det['confidence']:.2f}, "
                        f"pos=({det['center_x']:.0f},{det['center_y']:.0f})"
                    )

                # 분석 결과를 데이터베이스에 저장
                await db.save_video_analysis(
                    video_id=video_id,
                    frame_number=frame_number,
                    timestamp_ms=timestamp_ms,
                    detections=detections
                )

                # 프레임 데이터 준비
                frame_data = {
                    'frame_number': frame_number,
                    'timestamp_ms': timestamp_ms,
                    'video_id': video_id
                }

                # 규칙 엔진으로 프레임 평가
                alerts = await rule_engine.evaluate_frame(detections, frame_data, video_id)

                if alerts:
                    total_alerts += len(alerts)
                    self.logger.info(f"프레임 {frame_number}: {len(alerts)}개 알림 생성")
                    for alert in alerts:
                        self.logger.info(f"  - {alert.get('summary', '알림')}")

                # 처리 진행률 표시 (올바른 계산)
                progress = ((i + 1) / total_frames) * 100
                self.logger.info(f"처리 진행률: {progress:.1f}% ({i+1}/{total_frames})")

            self.logger.info(f"비디오 처리 완료: {video_id}")
            self.logger.info(f"총 {total_alerts}개 알림 생성")

        except Exception as e:
            self.logger.error(f"비디오 처리 중 오류 발생: {video_id} - {e}")
        finally:
            # 임시 파일 정리 (선택사항)
            # os.remove(video_path)
            pass

async def process_video(video_id: str, video_path: str):
    """비디오 처리를 위한 비동기 함수"""
    processor = VideoProcessor()
    await processor.process_video(video_id, video_path)

# 비동기 처리를 위한 함수
async def process_video_async(video_id: str, video_path: str):
    """비동기 비디오 처리"""
    # 비동기로 직접 실행
    asyncio.create_task(process_video(video_id, video_path))

    return {
        "video_id": video_id,
        "status": "processing",
        "message": "비디오 분석이 시작되었습니다."
    }
