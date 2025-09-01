import uuid
import asyncio
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from rules.builtins import create_rule
from core.db import db
from core.broker import broker
from core.config import cfg
from logging_config import get_logger

class RuleEngine:
    """규칙 엔진 - 비디오 분석 결과에 대해 규칙을 평가하고 알림을 생성"""

    def __init__(self):
        self.rules = {}
        self.logger = get_logger('rule_engine')
        self.load_rules()

    def load_rules(self):
        """활성화된 규칙들을 로드"""
        self.rules.clear()
        enabled_rules = cfg.get_enabled_rules()

        self.logger.info(f"활성화된 규칙 {len(enabled_rules)}개 로드:")
        for rule_data in enabled_rules:
            try:
                rule = create_rule(rule_data, cfg._config)
                self.rules[rule_data['id']] = rule
                self.logger.info(f"  - {rule_data.get('name')} ({rule_data.get('type')}) 로드 완료")
            except Exception as e:
                self.logger.error(f"규칙 로드 실패 {rule_data['id']}: {e}")

        self.logger.info(f"최종 로드된 규칙 수: {len(self.rules)}")

    def reload_rules(self):
        """규칙 재로드"""
        self.logger.info("규칙 재로드 시작")
        self.load_rules()

    async def evaluate_frame(self, detections: List[Dict], frame_data: Dict, video_id: str) -> List[Dict]:
        """프레임에 대해 모든 활성 규칙을 평가"""
        frame_num = frame_data.get('frame_number', 'N/A')
        self.logger.info(f"[규칙 엔진] 프레임 {frame_num} 평가 시작")
        self.logger.info(f"  - 탐지된 객체: {len(detections)}개")
        self.logger.info(f"  - 활성 규칙: {len(self.rules)}개")

        alerts = []

        for rule_id, rule in self.rules.items():
            rule_name = rule.rule_data.get('name', 'Unknown')
            rule_type = rule.rule_data.get('type', 'Unknown')
            self.logger.info(f"  - 규칙 '{rule_name}' ({rule_type}) 평가 중...")

            try:
                result = rule.evaluate(detections, frame_data)
                if result:
                    self.logger.info(f"    - 위반 감지: {result['summary']}")

                    # 쿨다운 체크 (같은 동영상에 대해 3초 내 중복 알림 방지)
                    if await db.is_alert_cooldown_active(video_id, result['rule_type']):
                        self.logger.info(f"    - 쿨다운 활성화: {video_id} - {result['rule_type']} (3초 내 중복 알림 방지)")
                        continue

                    # 알림 생성
                    alert_data = self._create_alert(result, frame_data, video_id)

                    # 비디오 클립 생성
                    from core.video_utils import create_alert_video_clip
                    from app.api.uploads import UPLOAD_DIR
                    import os

                    # 원본 비디오 파일 경로 찾기
                    video_files = [f for f in os.listdir(UPLOAD_DIR) if f.startswith(video_id)]
                    if video_files:
                        video_path = os.path.join(UPLOAD_DIR, video_files[0])

                        # 규칙 결과에서 영상 녹화 설정 가져오기
                        violations = result.get('violations', [])
                        if violations:
                            first_violation = violations[0]
                            pre_duration = first_violation.get('pre_duration', 1.5)
                            post_duration = first_violation.get('post_duration', 1.5)
                            total_duration = pre_duration + post_duration

                            # 디버깅: violations 데이터 출력
                            self.logger.info(f"    - [디버깅] violations 데이터: {first_violation}")
                            self.logger.info(f"    - [디버깅] pre_duration: {pre_duration}, post_duration: {post_duration}")
                            self.logger.info(f"    - [디버깅] total_duration: {total_duration}")
                        else:
                            self.logger.info("    - [디버깅] violations가 비어있음")
                            total_duration = 3  # 기본값

                        # 낙상 감지 규칙일 때는 무조건 5초 영상 생성
                        if result.get('rule_type') == 'fall_detection':
                            total_duration = 5.0
                            self.logger.info(f"    - [낙상 감지] 강제로 5초 영상 생성 설정")

                        video_clip_path = create_alert_video_clip(
                            video_path,
                            frame_data.get('frame_number', 0),
                            alert_data['alertId'],
                            total_duration  # 동적으로 계산된 클립 길이
                        )
                        alert_data['video_clip_path'] = video_clip_path

                    alerts.append(alert_data)

                    # 데이터베이스에 저장
                    alert_id = await db.create_alert(alert_data)

                    # SSE로 브로드캐스트
                    asyncio.create_task(broker.send_alert(alert_data))

                    # 규칙 실행 결과 저장
                    await db.save_rule_execution(
                        rule_id=rule_id,
                        video_id=video_id,
                        frame_number=frame_data.get('frame_number', 0),
                        timestamp_ms=frame_data.get('timestamp_ms', 0),
                        result=True,
                        details=result
                    )
                else:
                    self.logger.info(f"    - 위반 없음")

                    # 규칙 실행 결과 저장 (위반 없음)
                    await db.save_rule_execution(
                        rule_id=rule_id,
                        video_id=video_id,
                        frame_number=frame_data.get('frame_number', 0),
                        timestamp_ms=frame_data.get('timestamp_ms', 0),
                        result=False,
                        details=None
                    )
            except Exception as e:
                self.logger.error(f"    ✗ 규칙 평가 오류: {e}")

                # 에러 발생 시에도 실행 결과 저장
                await db.save_rule_execution(
                    rule_id=rule_id,
                    video_id=video_id,
                    frame_number=frame_data.get('frame_number', 0),
                    timestamp_ms=frame_data.get('timestamp_ms', 0),
                    result=False,
                    details={'error': str(e)}
                )

        if alerts:
            self.logger.info(f"  - 총 {len(alerts)}개 알림 생성")
        else:
            self.logger.info(f"  - 알림 없음")

        return alerts

    def _create_alert(self, rule_result: Dict, frame_data: Dict, video_id: str) -> Dict:
        """규칙 평가 결과로부터 알림 데이터 생성"""
        alert_id = str(uuid.uuid4())

        return {
            'alertId': alert_id,
            'rule_id': rule_result['rule_id'],
            'rule_type': rule_result['rule_type'],
            'ts_ms': frame_data.get('timestamp_ms', int(datetime.now().timestamp() * 1000)),
            'summary': rule_result['summary'],
            'detail': rule_result,
            'video_id': video_id,
            'frame_number': frame_data.get('frame_number', 0),
            'severity': self._get_rule_severity(rule_result['rule_id']),
            'status': 'unprocessed'
        }

    def _get_rule_severity(self, rule_id: str) -> str:
        """규칙의 심각도 반환"""
        for rule_data in cfg.get_rules():
            if rule_data['id'] == rule_id:
                return rule_data.get('severity', 'medium')
        return 'medium'

    def get_rule_info(self) -> List[Dict]:
        """현재 로드된 규칙 정보 반환"""
        rule_info = []
        for rule_id, rule in self.rules.items():
            rule_info.append({
                'id': rule_id,
                'type': rule.rule_data['type'],
                'name': rule.rule_data['name'],
                'enabled': rule.rule_data['enabled'],
                'severity': rule.rule_data.get('severity', 'medium'),
                'description': rule.rule_data.get('description', ''),
                'params': rule.rule_data['params']
            })
        return rule_info

    def test_rule(self, rule_data: Dict, test_detections: List[Dict], test_frame_data: Dict) -> Dict:
        """규칙 테스트 (실제 비디오 없이)"""
        try:
            # 테스트용 규칙 생성
            test_rule = create_rule(rule_data, cfg._config)

            # 규칙 평가
            result = test_rule.evaluate(test_detections, test_frame_data)

            return {
                'success': True,
                'result': result,
                'message': '규칙 테스트 완료'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '규칙 테스트 실패'
            }

# 전역 규칙 엔진 인스턴스
rule_engine = RuleEngine()
