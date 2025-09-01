import os
import cv2
from pathlib import Path
from typing import Optional

def create_alert_video_clip(video_path: str, frame_number: int, alert_id: str, duration_seconds: int = 3) -> Optional[str]:
    """
    알림 발생 시점을 중심으로 3초 비디오 클립 생성 (전 1.5초 + 후 1.5초)

    Args:
        video_path: 원본 비디오 파일 경로
        frame_number: 알림이 발생한 프레임 번호
        alert_id: 알림 ID
        duration_seconds: 클립 길이 (초, 기본값 3)

    Returns:
        생성된 클립 파일 경로 또는 None (실패 시)
    """
    try:
        # 비디오 파일 열기
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"비디오 파일을 열 수 없습니다: {video_path}")
            return None

        # 비디오 정보 가져오기
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 클립 범위 계산 (전 1.5초 + 후 1.5초, 안전하게)
        frames_before = int(fps * 1.5)  # 1.5초 전
        frames_after = int(fps * 1.5)   # 1.5초 후

        print(f"[클립 생성] 원본 요청: 전 {frames_before}프레임({frames_before/fps:.1f}초) + 후 {frames_after}프레임({frames_after/fps:.1f}초)")

        # 시작 프레임: 0보다 작아지지 않도록
        start_frame = max(0, frame_number - frames_before)

        # 끝 프레임: 비디오 끝을 넘어가지 않도록
        end_frame = min(total_frames - 1, frame_number + frames_after)

        print(f"[클립 생성] 초기 계산: 시작={start_frame}, 끝={end_frame}")

        # 만약 시작 프레임이 0이면, 끝 프레임을 조정하여 3초 클립 유지
        if start_frame == 0:
            # 시작이 0이면, 끝 프레임을 3초에 맞춤
            end_frame = min(total_frames - 1, int(fps * 3))
            print(f"[클립 생성] 시작이 0이므로 끝 프레임을 3초({end_frame}프레임)로 조정")
        elif end_frame == total_frames - 1:
            # 끝이 비디오 끝이면, 시작 프레임을 조정하여 3초 클립 유지
            start_frame = max(0, end_frame - int(fps * 3))
            print(f"[클립 생성] 끝이 비디오 끝이므로 시작 프레임을 {start_frame}으로 조정")

        # 실제 클립 길이 계산 (디버깅용)
        actual_frames_before = frame_number - start_frame
        actual_frames_after = end_frame - frame_number

        print(f"[클립 생성] 최종 범위: {start_frame}-{end_frame} (총 {end_frame-start_frame+1}프레임)")
        print(f"[클립 생성] 실제 분할: 전 {actual_frames_before}프레임({actual_frames_before/fps:.1f}초) + 후 {actual_frames_after}프레임({actual_frames_after/fps:.1f}초)")

        # 클립 저장 디렉토리 생성
        storage_dir = Path(__file__).parent.parent / "storage" / "alert_clips"
        storage_dir.mkdir(exist_ok=True)

        # 클립 파일명 및 경로
        clip_filename = f"alert_{alert_id}.mp4"
        clip_path = storage_dir / clip_filename

        # 비디오 작성기 설정
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(clip_path),
            fourcc,
            fps,
            (width, height)
        )

        # 지정된 프레임 범위 복사
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frames_written = 0
        for i in range(start_frame, end_frame + 1):
            ret, frame = cap.read()
            if not ret:
                print(f"  - 경고: 프레임 {i} 읽기 실패, 클립 생성 중단")
                break

            # 알림 발생 프레임에 표시 추가
            if i == frame_number:
                # 빨간색 테두리와 알림 텍스트 추가
                cv2.rectangle(frame, (10, 10), (width-10, height-10), (0, 0, 255), 3)
                cv2.putText(
                    frame,
                    f"ALERT: {alert_id}",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

            out.write(frame)
            frames_written += 1

        # 리소스 해제
        cap.release()
        out.release()

        clip_duration = (end_frame - start_frame + 1) / fps
        print(f"비디오 클립 생성 완료: {clip_path}")
        print(f"  - 총 길이: {clip_duration:.1f}초")
        print(f"  - 프레임 범위: {start_frame}-{end_frame}")
        print(f"  - 전: {actual_frames_before/fps:.1f}초, 후: {actual_frames_after/fps:.1f}초")
        print(f"  - 원본 비디오: {total_frames} 프레임, {total_frames/fps:.1f}초")
        print(f"  - 실제 작성: {frames_written} 프레임")
        return str(clip_path)

    except Exception as e:
        print(f"비디오 클립 생성 실패: {e}")
        return None
