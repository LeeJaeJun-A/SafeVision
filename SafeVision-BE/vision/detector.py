import cv2
import numpy as np
from ultralytics import YOLO
from typing import Any, List, Dict, Tuple, Optional
import logging
from logging_config import get_logger

class YOLODetector:
    """YOLO 모델을 사용한 객체 감지 클래스"""

    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.5):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.logger = get_logger('yolo_detector')
        self.logger.info(f"YOLO 모델 로드 완료: {model_path}")
        self.logger.info(f"신뢰도 임계값: {confidence_threshold}")

    def update_confidence_threshold(self, threshold: float):
        """신뢰도 임계값 업데이트"""
        old_threshold = self.confidence_threshold
        self.confidence_threshold = threshold
        self.logger.info(f"신뢰도 임계값 변경: {old_threshold} -> {threshold}")

    def detect_frame(self, frame: np.ndarray) -> List[Dict]:
        """단일 프레임에서 객체 감지"""
        try:
            # YOLO 모델로 객체 감지
            results = self.model(frame, verbose=False)

            detections = []

            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes
                    for i, box in enumerate(boxes):
                        # 바운딩 박스 좌표
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                        # 신뢰도
                        confidence = float(box.conf[0].cpu().numpy())

                        # 신뢰도가 너무 낮으면 건너뛰기
                        if confidence < self.confidence_threshold:
                            continue

                        # 클래스 ID 및 라벨
                        class_id = int(box.cls[0].cpu().numpy())
                        label = self.model.names[class_id]

                        # 중심점 계산
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2

                        # 너비와 높이
                        width = x2 - x1
                        height = y2 - y1

                        # 너무 큰 객체는 제외 (화면 전체를 덮는 경우)
                        frame_height, frame_width = frame.shape[:2]
                        if width > frame_width * 0.8 or height > frame_height * 0.8:
                            continue

                        # 너무 작은 객체도 제외 (노이즈 방지)
                        if width < 20 or height < 20:
                            continue

                        # 트래킹 ID (기본값)
                        track_id = f"{label}_{i}"

                        detection = {
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'center_x': float(center_x),
                            'center_y': float(center_y),
                            'width': float(width),
                            'height': float(height),
                            'confidence': confidence,
                            'class_id': class_id,
                            'label': label,
                            'track_id': track_id
                        }

                        detections.append(detection)

            # 프레임별 상세 로깅
            frame_info = f"프레임 {frame.shape[1]}x{frame.shape[0]}"
            if detections:
                self.logger.info(f"[{frame_info}] YOLO 감지 완료: {len(detections)}개 객체")
                for det in detections:
                    self.logger.info(
                        f"[{frame_info}] 객체: {det['label']} "
                        f"(ID: {det['track_id']}, conf: {det['confidence']:.3f}, "
                        f"size: {det['width']:.0f}x{det['height']:.0f}, "
                        f"pos: ({det['center_x']:.0f}, {det['center_y']:.0f}))"
                    )
            else:
                self.logger.info(f"[{frame_info}] YOLO 감지 결과: 객체 없음")

            # 신뢰도 필터링 전 원본 결과도 로깅
            if hasattr(result, 'boxes') and result.boxes is not None:
                self.logger.info(f"[{frame_info}] 신뢰도 필터링 전 원본 감지:")
                for i, box in enumerate(result.boxes):
                    class_id = int(box.cls[0].cpu().numpy())
                    confidence = float(box.conf[0].cpu().numpy())
                    label = self.model.names[class_id]
                    filter_status = "통과" if confidence >= self.confidence_threshold else "제외"
                    self.logger.info(
                        f"[{frame_info}] 원본 {label}: conf={confidence:.3f} "
                        f"(필터링: {filter_status})"
                    )

            return detections

        except Exception as e:
            self.logger.error(f"객체 감지 실패: {e}")
            return []

    def detect_video_frames(self, video_path: str, sample_fps: int = 5) -> List[Tuple[int, np.ndarray, List[Dict]]]:
        """비디오에서 프레임을 샘플링하여 객체 감지"""
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"비디오 파일을 열 수 없습니다: {video_path}")
            return []

        # 비디오 정보
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps

        print(f"비디오 정보: {total_frames} 프레임, {fps:.2f} FPS, {duration:.2f}초")
        print(f"샘플링: {sample_fps} FPS로 {int(duration * sample_fps)} 프레임 분석")

        frame_interval = max(1, int(fps / sample_fps))
        results = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 지정된 간격으로 프레임 샘플링
            if frame_count % frame_interval == 0:
                # 객체 감지
                detections = self.detect_frame(frame)

                # 결과 저장
                timestamp_ms = int((frame_count / fps) * 1000)
                results.append((frame_count, frame, detections, timestamp_ms))
            frame_count += 1

        cap.release()
        return results

    def draw_detections(self, frame: np.ndarray, detections: List[Dict],
                       draw_labels: bool = True, draw_confidence: bool = True) -> np.ndarray:
        """감지된 객체들을 프레임에 그리기"""
        result_frame = frame.copy()

        for detection in detections:
            bbox = detection['bbox']
            x1, y1, x2, y2 = bbox

            # 바운딩 박스 그리기
            color = self._get_color_by_label(detection['label'])
            cv2.rectangle(result_frame, (x1, y1), (x2, y2), color, 2)

            # 라벨과 신뢰도 그리기
            if draw_labels or draw_confidence:
                label_text = detection['label']
                if draw_confidence:
                    label_text += f" {detection['confidence']:.2f}"

                # 텍스트 배경
                (text_width, text_height), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(result_frame, (x1, y1 - text_height - 10), (x1 + text_width, y1), color, -1)

                # 텍스트
                cv2.putText(result_frame, label_text, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return result_frame

    def _get_color_by_label(self, label: str) -> Tuple[int, int, int]:
        """라벨에 따른 색상 반환"""
        color_map = {
            # 사람 관련
            'person': (0, 255, 0),      # 녹색

            # 차량 관련
            'car': (255, 0, 0),         # 파란색
            'truck': (255, 0, 0),       # 파란색
            'bus': (255, 0, 0),         # 파란색
            'motorcycle': (0, 0, 255),  # 빨간색
            'bicycle': (0, 0, 255),     # 빨간색
            'train': (255, 0, 0),       # 파란색

            # 건설장비
            'forklift': (255, 165, 0),  # 주황색
            'crane': (128, 0, 128),     # 보라색
            'excavator': (128, 0, 128), # 보라색
            'bulldozer': (128, 0, 128), # 보라색
            'loader': (128, 0, 128),    # 보라색
            'dumper': (128, 0, 128),    # 보라색

            # 동물
            'dog': (0, 255, 255),       # 노란색
            'cat': (0, 255, 255),       # 노란색
            'horse': (0, 255, 255),     # 노란색

            # 물체
            'chair': (255, 255, 0),     # 청록색
            'couch': (255, 255, 0),     # 청록색
            'bed': (255, 255, 0),       # 청록색
            'dining table': (255, 255, 0), # 청록색
            'tv': (255, 255, 0),        # 청록색
            'laptop': (255, 255, 0),    # 청록색
            'cell phone': (255, 255, 0), # 청록색

            # 음식
            'pizza': (0, 255, 255),     # 노란색
            'sandwich': (0, 255, 255),  # 노란색
            'orange': (0, 255, 255),    # 노란색
            'broccoli': (0, 255, 255),  # 노란색
            'carrot': (0, 255, 255),    # 노란색

            # 스포츠
            'sports ball': (255, 0, 255), # 마젠타
            'baseball bat': (255, 0, 255), # 마젠타
            'baseball glove': (255, 0, 255), # 마젠타
            'tennis racket': (255, 0, 255), # 마젠타

            # 주방용품
            'knife': (255, 255, 255),   # 흰색
            'fork': (255, 255, 255),    # 흰색
            'spoon': (255, 255, 255),   # 흰색
            'bowl': (255, 255, 255),    # 흰색
            'cup': (255, 255, 255),     # 흰색
            'wine glass': (255, 255, 255), # 흰색
            'bottle': (255, 255, 255),  # 흰색

            # 옷
            'backpack': (128, 128, 128), # 회색
            'umbrella': (128, 128, 128), # 회색
            'handbag': (128, 128, 128),  # 회색
            'suitcase': (128, 128, 128), # 회색

            # 신호등/표지판
            'traffic light': (0, 128, 255), # 주황색
            'fire hydrant': (0, 128, 255), # 주황색
            'stop sign': (0, 128, 255),    # 주황색
            'parking meter': (0, 128, 255), # 주황색
            'bench': (0, 128, 255),        # 주황색
        }

        return color_map.get(label, (128, 128, 128))  # 기본값: 회색

    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        if self.model is None:
            return {'error': '모델이 로드되지 않음'}

        return {
            'model_name': self.model.ckpt_path if hasattr(self.model, 'ckpt_path') else 'Unknown',
            'confidence_threshold': self.confidence_threshold,
            'available_classes': list(self.model.names.values()) if hasattr(self.model, 'names') else []
        }

# 전역 감지기 인스턴스
detector = YOLODetector()
