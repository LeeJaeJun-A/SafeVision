import math
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from rules.schemas import RuleType, SeverityLevel
import logging

class RuleState:
    """규칙 상태 관리"""
    def __init__(self):
        self.violations = {}  # rule_id -> entity_id -> start_time
        self.entity_violation_times = {}  # rule_entity_key -> last_alert_time
        self.last_alert = {}  # rule_id -> last_alert_time
        self.video_alert_times = {}  # rule_video_key -> last_alert_time (새로 추가)
        self.tracking_data = {}  # track_id -> {position, timestamp}

    def start_violation(self, rule_id: str, entity_id: str):
        """위반 상태 시작"""
        key = f"{rule_id}_{entity_id}"
        if key not in self.violations:
            self.violations[key] = datetime.now()

    def is_violating(self, rule_id: str, entity_id: str, duration: int) -> bool:
        """지정된 시간 동안 위반 상태인지 확인"""
        key = f"{rule_id}_{entity_id}"
        if key not in self.violations:
            return False

        start_time = self.violations[key]
        elapsed = (datetime.now() - start_time).total_seconds()
        return elapsed >= duration

    def clear_violation(self, rule_id: str, entity_id: str):
        """위반 상태 초기화"""
        key = f"{rule_id}_{entity_id}"
        if key in self.violations:
            del self.violations[key]

    def mark_alert(self, rule_id: str, entity_id: str):
        """알림 생성 시간 기록"""
        self.last_alert[rule_id] = datetime.now()
        entity_key = f"{rule_id}_{entity_id}"
        self.entity_violation_times[entity_key] = datetime.now()

    def mark_video_alert(self, rule_id: str, video_id: str):
        """비디오별 알림 생성 시간 기록 (새로 추가)"""
        video_key = f"{rule_id}_{video_id}"
        self.video_alert_times[video_key] = datetime.now()

    def record_violation(self, rule_id: str, entity_id: str, violation_data: Dict):
        """위반 데이터 기록"""
        # 기존 로직 유지
        pass

class BaseRule:
    """기본 규칙 클래스"""
    def __init__(self, rule_data: Dict[str, Any], config: Dict[str, Any]):
        self.rule_data = rule_data
        self.config = config
        self.state = RuleState()  # 각 규칙마다 독립적인 상태

    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        """규칙 평가 - 하위 클래스에서 구현"""
        raise NotImplementedError

    def _should_generate_alert(self, rule_id: str, entity_id: str, violation_data: Dict, ignore_duration_check: bool = False) -> bool:
        """알림 생성 여부 결정 (중복 방지)"""
        cooldown = self.config.get('cooldown', 60)
        min_interval = self.config.get('min_violation_interval', 30)
        video_cooldown = self.config.get('video_cooldown', 5)  # 같은 영상에서 5초 간격

        # Duration 체크를 통과한 경우에만 중복 방지 로직 적용
        if ignore_duration_check:
            # Duration 요구사항을 만족한 첫 알림은 중복 체크를 더 관대하게
            min_interval = min_interval // 2  # 절반으로 줄임

        # 1. 쿨다운 확인 (전역)
        if rule_id in self.state.last_alert:
            last_time = self.state.last_alert[rule_id]
            if (datetime.now() - last_time).total_seconds() < cooldown:
                return False

        # 2. 개체별 최소 간격 확인
        if entity_id and min_interval:
            entity_key = f"{rule_id}_{entity_id}"
            if entity_key in self.state.entity_violation_times:
                last_entity_time = self.state.entity_violation_times[entity_key]
                if (datetime.now() - last_entity_time).total_seconds() < min_interval:
                    return False

        # 3. 같은 영상에서 5초 간격 확인 (새로 추가)
        video_id = violation_data.get('video_id', 'unknown')
        if video_id != 'unknown':
            video_key = f"{rule_id}_{video_id}"
            if video_key in self.state.video_alert_times:
                last_video_time = self.state.video_alert_times[video_key]
                if (datetime.now() - last_video_time).total_seconds() < video_cooldown:
                    # 로그 시스템 사용
                    import logging
                    logger = logging.getLogger('alert_generation')
                    logger.info(f"[알림 생성] 같은 영상에서 5초 간격 미달: {video_id}")
                    return False

        return True

    def _prepare_violation_data(self, entity_id: str, position: Tuple[float, float], **kwargs) -> Dict:
        """위반 데이터 준비"""
        violation_data = {
            'position': position,
            'entity_id': entity_id,
            'timestamp': datetime.now(),
            'video_id': kwargs.get('video_id', 'unknown'),  # 비디오 ID 추가
        }

        # 명시적으로 pre_duration과 post_duration 포함
        if 'pre_duration' in kwargs:
            violation_data['pre_duration'] = kwargs['pre_duration']
        if 'post_duration' in kwargs:
            violation_data['post_duration'] = kwargs['post_duration']

        # 나머지 kwargs 추가
        violation_data.update(kwargs)

        return violation_data

    def _update_tracking_data(self, detections: List[Dict], frame_data: Dict):
        """객체 위치 추적 데이터 업데이트"""
        for detection in detections:
            track_id = detection.get('track_id')
            if track_id:
                self.state.tracking_data[track_id] = {
                    'position': (detection['center_x'], detection['center_y']),
                    'timestamp': frame_data.get('timestamp_ms', 0)
                }

    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """두 위치 간의 거리 계산 (픽셀 -> 미터 변환)"""
        # 픽셀 단위 거리 계산
        pixel_distance = math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

        # 픽셀을 미터로 변환 (설정에서 가져오거나 기본값 사용)
        pixel_to_meter = self.config.get('pixel_to_meter', 0.05)  # 1픽셀 = 0.05미터

        # 실제 미터 단위 거리
        distance_meters = pixel_distance * pixel_to_meter

        return distance_meters

    def _calculate_2d_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """2D 픽셀 거리를 미터로 변환 (간단한 방식)"""
        x1, y1 = pos1
        x2, y2 = pos2

        # 픽셀 거리 계산
        pixel_distance = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

        # 픽셀을 미터로 변환
        pixel_to_meter = self.config.get('pixel_to_meter', 0.05)
        meter_distance = pixel_distance * pixel_to_meter

        print(f"[거리 계산] 2D 거리: {pixel_distance:.1f}픽셀 -> {meter_distance:.2f}m")
        return meter_distance

    def _calculate_3d_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """원근감을 고려한 3D 거리 계산"""
        try:
            # 카메라 설정 가져오기
            camera_height = self.config.get('camera_height', 3.0)
            camera_angle = math.radians(self.config.get('camera_angle', 15))
            focal_length = self.config.get('focal_length', 1000)
            image_height = self.config.get('image_height', 1080)
            ground_plane_y = self.config.get('ground_plane_y', 800)

            # 각 점의 3D 좌표 계산
            x1, y1 = pos1
            x2, y2 = pos2

            # Y 좌표를 지면 기준으로 변환 (Y가 클수록 가까움)
            y1_ground = image_height - y1
            y2_ground = image_height - y2

            # 각 점의 실제 거리 계산
            distance1 = self._pixel_to_3d_distance(x1, y1_ground, camera_height, camera_angle, focal_length)
            distance2 = self._pixel_to_3d_distance(x2, y2_ground, camera_height, camera_angle, focal_length)

            # inf 값 체크
            if math.isinf(distance1) or math.isinf(distance2):
                print(f"[거리 계산] 3D 변환 실패: distance1={distance1}, distance2={distance2}")
                return float('inf')

            # 3D 공간에서의 실제 거리 계산
            dx = (x1 - x2) * distance1 / focal_length  # X 방향 거리
            dy = distance1 - distance2  # Y 방향 거리 (깊이 차이)

            real_distance = math.sqrt(dx**2 + dy**2)

            # 탐지 거리 범위 확인
            max_dist = self.config.get('max_detection_distance', 20.0)
            min_dist = self.config.get('min_detection_distance', 1.0)

            if real_distance > max_dist or real_distance < min_dist:
                print(f"[거리 계산] 탐지 범위 밖: {real_distance:.2f}m (범위: {min_dist}-{max_dist}m)")
                return float('inf')  # 탐지 범위 밖

            print(f"[거리 계산] 3D 거리: {real_distance:.2f}m")
            return real_distance

        except Exception as e:
            print(f"[거리 계산] 3D 거리 계산 오류: {e}")
            return float('inf')

    def _pixel_to_3d_distance(self, x: float, y: float, camera_height: float, camera_angle: float, focal_length: float) -> float:
        """픽셀 좌표를 3D 거리로 변환"""
        # Y 좌표를 각도로 변환
        angle_from_center = math.atan2(y - focal_length, focal_length)
        total_angle = camera_angle + angle_from_center

        # 삼각함수를 이용한 거리 계산
        if abs(total_angle) < math.pi/2:  # 카메라가 바라보는 방향
            distance = camera_height / math.tan(total_angle)
            return max(distance, 0.1)  # 최소 거리 보장
        else:
            return float('inf')  # 카메라 뒤쪽

    def _is_within_detection_range(self, pos: Tuple[float, float]) -> bool:
        """해당 위치가 탐지 범위 내에 있는지 확인"""
        camera_height = self.config.get('camera_height', 3.0)
        camera_angle = math.radians(self.config.get('camera_angle', 15))
        focal_length = self.config.get('focal_length', 1000)
        image_height = self.config.get('image_height', 1080)

        x, y = pos
        y_ground = image_height - y

        distance = self._pixel_to_3d_distance(x, y_ground, camera_height, camera_angle, focal_length)

        max_dist = self.config.get('max_detection_distance', 20.0)
        min_dist = self.config.get('min_detection_distance', 1.0)

        return min_dist <= distance <= max_dist

    def _is_in_polygon(self, point: Tuple[float, float], polygon: List[List[float]]) -> bool:
        """점이 폴리곤 내부에 있는지 확인"""
        x, y = point
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _line_crossed(self, line_start: List[float], line_end: List[float],
                      prev_pos: Tuple[float, float], curr_pos: Tuple[float, float]) -> bool:
        """선을 건넜는지 확인"""
        # 간단한 선분 교차 판정
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        A = prev_pos
        B = curr_pos
        C = line_start
        D = line_end

        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

    def _update_collision_tracking(self, detections: List[Dict], frame_data: Dict):
        """충돌 감지용 개별 객체 추적 데이터를 업데이트합니다."""
        import logging
        logger = logging.getLogger('collision_risk_rule')

        logger.info(f"[충돌 추적] 프레임 {frame_data.get('frame_number', 'unknown')}에서 {len(detections)}개 객체 처리")

        for detection in detections:
            track_id = detection.get('track_id')
            if track_id:
                # 개별 객체별로 추적 데이터 저장
                self.state.tracking_data[track_id] = {
                    'center_x': detection['center_x'],
                    'center_y': detection['center_y'],
                    'position': (detection['center_x'], detection['center_y']),
                    'timestamp': frame_data.get('timestamp', 0),
                    'frame_number': frame_data.get('frame_number', 0),
                    'label': detection.get('label', ''),
                    'size': detection.get('size', 0)
                }
                logger.info(f"[충돌 추적] {track_id} ({detection.get('label', '')}) 위치 업데이트: ({detection['center_x']:.0f}, {detection['center_y']:.0f})")

        logger.info(f"[충돌 추적] 현재 총 {len(self.state.tracking_data)}개 객체 추적 중")

    def _update_fall_tracking(self, detections: List[Dict], frame_data: Dict):
        """낙상 감지용 통합 person 추적 데이터를 업데이트합니다."""
        import logging
        logger = logging.getLogger('fall_detection_rule')

        logger.info(f"[낙상 추적] 프레임 {frame_data.get('frame_number', 'unknown')}에서 {len(detections)}개 객체 처리")

        # 기존 통합 person 객체 가져오기
        unified_person_data = self.state.tracking_data.get('unified_person', None)

        for detection in detections:
            track_id = detection.get('track_id')
            label = detection.get('label', '')

            if track_id and (label == 'person' or label == 'airplane'):
                # 첫 번째 person/airplane 객체이거나 기존 통합 객체가 없는 경우
                if unified_person_data is None:
                    unified_person_data = {
                        'center_x': detection['center_x'],
                        'center_y': detection['center_y'],
                        'position': (detection['center_x'], detection['center_y']),
                        'timestamp': frame_data.get('timestamp', 0),
                        'frame_number': frame_data.get('frame_number', 0),
                        'labels': [label]
                    }
                    logger.info(f"[낙상 추적] 통합 person 객체 생성: pos=({detection['center_x']:.0f}, {detection['center_y']:.0f}), 라벨: {label}")
                else:
                    current_y = detection['center_y']
                    existing_y = unified_person_data['center_y']
                    y_change = abs(current_y - existing_y)

                    # 매번 위치 업데이트 (이전 값 저장을 위해)
                    unified_person_data.update({
                        'center_x': detection['center_x'],
                        'center_y': detection['center_y'],
                        'position': (detection['center_x'], detection['center_y']),
                        'frame_number': frame_data.get('frame_number', 0)
                    })
                    unified_person_data['labels'].append(label)

                    # y좌표 변화가 70픽셀 이상이면 낙상 가능성 로깅
                    if y_change >= 70:
                        logger.info(f"[낙상 추적] ⚠️ 낙상 가능성! y좌표 변화: {y_change:.0f}픽셀 >= 70픽셀")

                    logger.info(f"[낙상 추적] 통합 person 객체 업데이트: pos=({detection['center_x']:.0f}, {detection['center_y']:.0f}), y변화: {y_change:.0f}픽셀")

        # 통합된 person 객체를 저장
        if unified_person_data:
            self.state.tracking_data['unified_person'] = unified_person_data
            logger.info(f"[낙상 추적] 통합 person 객체 저장 완료: {unified_person_data}")

        logger.info(f"[낙상 추적] 현재 총 {len(self.state.tracking_data)}개 객체 추적 중")

    def _get_tracking_data(self, track_id: str) -> Optional[Dict]:
        """특정 객체의 최신 위치 정보를 가져옵니다."""
        # 1. 개별 track_id로 먼저 확인
        if track_id in self.state.tracking_data:
            return self.state.tracking_data[track_id]

        # 2. unified_person 데이터 확인 (person/airplane 객체의 경우)
        if track_id.startswith('person') or track_id.startswith('airplane'):
            unified_data = self.state.tracking_data.get('unified_person')
            if unified_data:
                logger = logging.getLogger('fall_detection_rule')
                logger.info(f"[낙상 감지 규칙] {track_id} → unified_person 데이터 사용")
                return unified_data

        return None

    def _calculate_y_change(self, track_id: str, current_pos: Tuple[float, float], frame_data: Dict) -> Optional[float]:
        """객체의 y좌표 변화량 계산"""
        if track_id not in self.state.tracking_data:
            return None

        prev_data = self.state.tracking_data[track_id]
        prev_pos = prev_data['position']
        prev_time = prev_data['timestamp']

        curr_time = frame_data.get('timestamp_ms', 0)
        time_diff = (curr_time - prev_time) / 1000.0  # 초 단위

        # 시간 윈도우 내의 변화만 고려
        if time_diff > self.rule_data['params'].get('time_window', 1.0):
            return None

        # y좌표 변화량 (양수 = 아래로 이동 = 낙상)
        y_change = current_pos[1] - prev_pos[1]
        return y_change

    def _record_position(self, track_id: str, position: Tuple[float, float], frame_data: Dict):
        """객체의 현재 위치와 시간 기록"""
        self.state.tracking_data[track_id] = {
            'position': position,
            'timestamp': frame_data.get('timestamp_ms', 0)
        }

class DistanceBelowRule(BaseRule):
    """거리 위반 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        min_distance = params.get('min_distance', 2.0)
        duration = params.get('duration', 3)
        target_labels = params.get('labels', ['person', 'forklift'])

        # 해당 라벨의 객체들 찾기
        target_objects = [d for d in detections if d.get('label') in target_labels]

        if len(target_objects) < 2:
            return None

        violations = []

        # 모든 객체 쌍에 대해 거리 확인
        for i in range(len(target_objects)):
            for j in range(i + 1, len(target_objects)):
                obj1 = target_objects[i]
                obj2 = target_objects[j]

                pos1 = (obj1['center_x'], obj1['center_y'])
                pos2 = (obj2['center_x'], obj2['center_y'])

                # 탐지 범위 내에 있는지 확인
                if not self._is_within_detection_range(pos1) or not self._is_within_detection_range(pos2):
                    continue

                distance = self._calculate_distance(pos1, pos2)

                if distance < min_distance:
                    entity_key = f"{obj1['track_id']}_{obj2['track_id']}"
                    position = ((pos1[0] + pos2[0]) / 2, (pos1[1] + pos2[1]) / 2)

                    violation_data = self._prepare_violation_data(
                        entity_key, position,
                        objects=[obj1['track_id'], obj2['track_id']],
                        distance=distance,
                        min_distance=min_distance,
                        duration=duration
                    )

                    if self.state.is_violating(rule_id, entity_key, duration):
                        # Duration 조건을 만족했으므로 중복 체크를 관대하게 적용
                        if self._should_generate_alert(rule_id, entity_key, violation_data, ignore_duration_check=True):
                            self.state.mark_alert(rule_id, entity_key)
                            self.state.record_violation(rule_id, entity_key, violation_data)
                            violations.append(violation_data)
                    else:
                        self.state.start_violation(rule_id, entity_key)
                else:
                    entity_key = f"{obj1['track_id']}_{obj2['track_id']}"
                    self.state.clear_violation(rule_id, entity_key)

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.DISTANCE_BELOW,
                'violations': violations,
                'summary': f"거리 위반: {len(violations)}건의 안전 거리 미준수"
            }

        return None

class ZoneEntryRule(BaseRule):
    """위험 구역 진입 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        zone_id = params.get('zone_id', 'zone_1')
        duration = params.get('duration', 2)
        target_labels = params.get('labels', ['person'])

        # 규칙에 포함된 구역 정보 사용
        target_zone = self.rule_data.get('zone')
        if not target_zone:
            return None

        violations = []

        for detection in detections:
            if detection.get('label') not in target_labels:
                continue

            pos = (detection['center_x'], detection['center_y'])

            # 탐지 범위 내에 있는지 확인
            if not self._is_within_detection_range(pos):
                continue

            if self._is_in_polygon(pos, target_zone['polygon']):
                entity_key = detection['track_id']

                violation_data = self._prepare_violation_data(
                    entity_key, pos,
                    object=detection['track_id'],
                    zone_id=zone_id,
                    zone_name=target_zone['name'],
                    duration=duration
                )

                if self.state.is_violating(rule_id, entity_key, duration):
                    if self._should_generate_alert(rule_id, entity_key, violation_data):
                        self.state.mark_alert(rule_id, entity_key)
                        self.state.record_violation(rule_id, entity_key, violation_data)
                        violations.append(violation_data)
                else:
                    self.state.start_violation(rule_id, entity_key)
            else:
                entity_key = detection['track_id']
                self.state.clear_violation(rule_id, entity_key)

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.ZONE_ENTRY,
                'violations': violations,
                'summary': f"위험 구역 진입: {len(violations)}건의 구역 침입"
            }

        return None

class SpeedOverRule(BaseRule):
    """과속 규칙 - 1초 단위로 프레임들을 모아서 속도 계산"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        max_speed = params.get('max_speed', 5.0)
        target_labels = params.get('labels', ['forklift', 'car'])

        print(f"[과속 규칙] 평가 시작 - 대상 라벨: {target_labels}, 최대 속도: {max_speed} m/s")
        print(f"[과속 규칙] 탐지된 객체: {len(detections)}개")

        violations = []

        for detection in detections:
            detection_label = detection.get('label', 'unknown')
            print(f"[과속 규칙] 객체 {detection['track_id']} ({detection_label}) 검사 중...")

            # 라벨 필터링 - target_labels에 포함된 객체만 처리
            if detection_label not in target_labels:
                print(f"[과속 규칙] {detection_label}은 대상 라벨이 아님, 건너뜀")
                continue

            print(f"[과속 규칙] {detection_label} 속도 계산 중...")
            track_id = detection['track_id']

            # 1초 단위로 속도 계산
            speed = self._calculate_speed_over_time(track_id, frame_data, time_window=1.0)

            if speed is not None:
                print(f"[과속 규칙] {detection_label} 1초 평균 속도: {speed:.2f} m/s (임계값: {max_speed})")

                if speed > max_speed:
                    print(f"[과속 규칙] ⚠️ {detection_label} 과속 감지! {speed:.2f} > {max_speed}")
                    if self.state.can_alert(rule_id, self.config.get('cooldown', 30)):
                        self.state.mark_alert(rule_id)
                        violations.append({
                            'object': track_id,
                            'label': detection_label,
                            'speed': speed,
                            'max_speed': max_speed
                        })
                    else:
                        print(f"[과속 규칙] 쿨다운 중, 알림 생성 안함")
                else:
                    print(f"[과속 규칙] {detection_label} 속도 정상")
            else:
                print(f"[과속 규칙] {detection_label} 속도 계산 불가 (데이터 부족)")

            # 현재 위치 정보 업데이트
            self.state.tracking_data[track_id] = {
                'position': (detection['center_x'], detection['center_y']),
                'timestamp': frame_data.get('timestamp_ms', 0)
            }

        if violations:
            print(f"[과속 규칙] 총 {len(violations)}건 과속 위반 감지")
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.SPEED_OVER,
                'violations': violations,
                'summary': f"과속: {len(violations)}건의 속도 위반"
            }
        else:
            print(f"[과속 규칙] 과속 위반 없음")

        return None

    def _calculate_speed_over_time(self, track_id: str, frame_data: Dict, time_window: float = 1.0) -> Optional[float]:
        """지정된 시간 윈도우 내에서의 평균 속도 계산"""
        if track_id not in self.state.tracking_data:
            return None

        current_time = frame_data.get('timestamp_ms', 0)
        current_pos = self.state.tracking_data[track_id]['position']

        # time_window 초 전의 데이터 찾기
        target_time = current_time - (time_window * 1000)  # 밀리초 단위

        # 이전 위치 데이터가 time_window 내에 있는지 확인
        prev_data = self.state.tracking_data[track_id]
        prev_time = prev_data['timestamp']

        if prev_time < target_time:
            # time_window 밖의 데이터는 무시
            return None

        time_diff = (current_time - prev_time) / 1000.0  # 초 단위

        if time_diff < 0.1:  # 최소 0.1초 이상 차이가 날 때만 계산
            return None

        # 거리 계산
        distance = self._calculate_distance(prev_data['position'], current_pos)

        # 속도 계산 (m/s)
        speed = distance / time_diff

        # 비정상적인 속도 값 필터링
        if 0 < speed < 100:
            return speed
        else:
            print(f"[과속 규칙] 비정상 속도 무시: {speed:.2f} m/s (거리: {distance:.2f}m, 시간: {time_diff:.3f}초)")
            return None

class CrowdInZoneRule(BaseRule):
    """밀집도 위반 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        zone_id = params.get('zone_id', 'zone_1')
        max_count = params.get('max_count', 3)
        duration = params.get('duration', 5)
        target_labels = params.get('labels', ['person'])

        # 규칙에 포함된 구역 정보 사용
        target_zone = self.rule_data.get('zone')
        if not target_zone:
            return None

        # 구역 내 객체 수 계산
        count_in_zone = 0
        for detection in detections:
            if detection.get('label') not in target_labels:
                continue

            pos = (detection['center_x'], detection['center_y'])
            if self._is_in_polygon(pos, target_zone['polygon']):
                count_in_zone += 1

        if count_in_zone >= max_count:
            entity_key = zone_id

            if self.state.is_violating(rule_id, entity_key, duration):
                if self.state.can_alert(rule_id, self.config.get('cooldown', 30)):
                    self.state.mark_alert(rule_id)
                    return {
                        'rule_id': rule_id,
                        'rule_type': RuleType.CROWD_IN_ZONE,
                        'violations': [{
                            'zone_id': zone_id,
                            'zone_name': target_zone['name'],
                            'count': count_in_zone,
                            'max_count': max_count,
                            'duration': duration
                        }],
                        'summary': f"밀집도 위반: {count_in_zone}명이 위험 구역에 집중"
                    }
            else:
                self.state.start_violation(rule_id, entity_key)
        else:
            entity_key = zone_id
            self.state.clear_violation(rule_id, entity_key)

        return None

class LineCrossRule(BaseRule):
    """안전선 침범 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        line_id = params.get('line_id', 'line_1')
        target_labels = params.get('labels', ['person', 'forklift'])

        # 규칙에 포함된 선 정보 사용
        target_line = self.rule_data.get('line')
        if not target_line:
            return None

        violations = []

        for detection in detections:
            if detection.get('label') not in target_labels:
                continue

            track_id = detection['track_id']

            # 이전 프레임의 위치 정보 가져오기
            if track_id in self.state.tracking_data:
                prev_data = self.state.tracking_data[track_id]
                prev_pos = prev_data['position']

                curr_pos = (detection['center_x'], detection['center_y'])

                # 선을 건넜는지 확인
                if self._line_crossed(target_line['points'][0], target_line['points'][1],
                                    prev_pos, curr_pos):
                    if self.state.can_alert(rule_id, self.config.get('cooldown', 30)):
                        self.state.mark_alert(rule_id)
                        violations.append({
                            'object': track_id,
                            'line_id': line_id,
                            'line_name': target_line['name']
                        })

            # 현재 위치 정보 업데이트
            self.state.tracking_data[track_id] = {
                'position': (detection['center_x'], detection['center_y']),
                'timestamp': frame_data.get('timestamp_ms', 0)
            }

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.LINE_CROSS,
                'violations': violations,
                'summary': f"안전선 침범: {len(violations)}건의 선 침범"
            }

        return None

class ApproachingRule(BaseRule):
    """접근 추세 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        duration = params.get('duration', 3)
        target_labels = params.get('labels', ['person', 'forklift'])

        violations = []

        for detection in detections:
            if detection.get('label') not in target_labels:
                continue

            track_id = detection['track_id']

            # 이전 프레임의 위치 정보 가져오기
            if track_id in self.state.tracking_data:
                prev_data = self.state.tracking_data[track_id]
                prev_pos = prev_data['position']
                prev_time = prev_data['timestamp']

                curr_pos = (detection['center_x'], detection['center_y'])
                curr_time = frame_data.get('timestamp_ms', 0)

                if prev_time != curr_time:
                    time_diff = (curr_time - prev_time) / 1000.0  # 초 단위
                    if time_diff > 0:
                        # 거리 변화율 계산 (접근하는지 확인)
                        distance_change = self._calculate_distance(prev_pos, curr_pos)

                        # 접근하는 경우 (거리가 줄어드는 경우)
                        if distance_change > 0:  # 움직임이 있는 경우
                            entity_key = track_id

                            if self.state.is_violating(rule_id, entity_key, duration):
                                if self.state.can_alert(rule_id, self.config.get('cooldown', 30)):
                                    self.state.mark_alert(rule_id)
                                    violations.append({
                                        'object': track_id,
                                        'duration': duration
                                    })
                            else:
                                self.state.start_violation(rule_id, entity_key)

            # 현재 위치 정보 업데이트
            self.state.tracking_data[track_id] = {
                'position': (detection['center_x'], detection['center_y']),
                'timestamp': frame_data.get('timestamp_ms', 0)
            }

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.APPROACHING,
                'violations': violations,
                'summary': f"접근 추세: {len(violations)}건의 지속적 접근"
            }

        return None

class RestrictedAreaRule(BaseRule):
    """제한 구역 진입 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        target_zone = params.get('zone', {})
        target_labels = params.get('labels', ['person', 'forklift'])

        violations = []

        for detection in detections:
            if detection.get('label') not in target_labels:
                continue

            track_id = detection['track_id']
            pos = (detection['center_x'], detection['center_y'])

            # 제한 구역 내부에 있는지 확인
            if self._is_in_polygon(pos, target_zone.get('polygon', [])):
                violations.append({
                    'object': track_id,
                    'zone_name': target_zone.get('name', 'Unknown'),
                    'danger_level': target_zone.get('danger_level', 'medium')
                })

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.RESTRICTED_AREA,
                'violations': violations,
                'summary': f"제한 구역 진입: {len(violations)}건의 진입"
            }

        return None

class SpeedLimitZoneRule(BaseRule):
    """구역 내 속도 제한 규칙"""
    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        target_zone = params.get('zone', {})
        max_speed = params.get('max_speed', 3.0)
        target_labels = params.get('labels', ['forklift', 'car', 'truck'])

        violations = []

        for detection in detections:
            if detection.get('label') not in target_labels:
                continue

            track_id = detection['track_id']
            pos = (detection['center_x'], detection['center_y'])

            # 구역 내부에 있는지 확인
            if self._is_in_polygon(pos, target_zone.get('polygon', [])):
                # 이전 프레임의 위치 정보 가져오기
                if track_id in self.state.tracking_data:
                    prev_data = self.state.tracking_data[track_id]
                    prev_pos = prev_data['position']
                    prev_time = prev_data['timestamp']

                    curr_time = frame_data.get('timestamp_ms', 0)
                    if prev_time != curr_time:
                        time_diff = (curr_time - prev_time) / 1000.0  # 초 단위
                        if time_diff > 0:
                            # 속도 계산 (m/s)
                            distance = self._calculate_distance(prev_pos, pos)
                            speed = distance / time_diff

                            if speed > max_speed:
                                violations.append({
                                    'object': track_id,
                                    'speed': speed,
                                    'max_speed': max_speed,
                                    'zone_name': target_zone.get('name', 'Unknown')
                                })

            # 현재 위치 정보 업데이트
            self.state.tracking_data[track_id] = {
                'position': (detection['center_x'], detection['center_y']),
                'timestamp': frame_data.get('timestamp_ms', 0)
            }

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.SPEED_LIMIT_ZONE,
                'violations': violations,
                'summary': f"구역 내 속도 위반: {len(violations)}건의 과속"
            }

        return None

class CollisionRiskRule(BaseRule):
    """충돌 위험 규칙: 사람과 다른 객체 간의 근접성 감지"""

    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        min_distance = params.get('min_distance', 50)  # 최소 거리 (픽셀)
        max_frame_gap = params.get('max_frame_gap', 10)  # 최대 프레임 간격

        # 로그 시스템 사용
        import logging
        logger = logging.getLogger('collision_risk_rule')

        logger.info(f"[충돌 위험 규칙] 평가 시작 - 프레임 {frame_data.get('frame_number', 'unknown')}")
        logger.info(f"[충돌 위험 규칙] 탐지된 객체: {len(detections)}개")

        # 각 객체의 상세 정보 출력
        for obj in detections:
            logger.info(f"  - {obj['label']} (ID: {obj['track_id']}) at ({obj['center_x']:.0f}, {obj['center_y']:.0f})")

        # 사람과 비사람 객체 분리
        persons = [d for d in detections if d.get('label') == 'person']
        non_persons = [d for d in detections if d.get('label') != 'person']

        logger.info(f"[충돌 위험 규칙] 사람 객체: {len(persons)}개")
        logger.info(f"[충돌 위험 규칙] 비사람 객체: {len(non_persons)}개")

        if not persons or not non_persons:
            logger.info(f"[충돌 위험 규칙] 충돌 감지 불가 - 사람: {len(persons)}개, 비사람: {len(non_persons)}개")
            return None

        violations = []

        # 각 사람과 비사람 객체 간의 거리 계산
        for person in persons:
            person_id = person['track_id']
            person_pos = (person['center_x'], person['center_y'])

            logger.info(f"[충돌 위험 규칙] 사람 {person_id} 위치: ({person['center_x']:.0f}, {person['center_y']:.0f})")

            for obj in non_persons:
                obj_id = obj['track_id']
                obj_pos = (obj['center_x'], obj['center_y'])

                # 픽셀 거리 계산
                distance = self._calculate_pixel_distance(person_pos, obj_pos)
                logger.info(f"[충돌 위험 규칙] 사람 {person_id} ↔ {obj['label']} {obj_id} 거리: {distance:.0f}픽셀")

                # 충돌 위험 감지
                if distance <= min_distance:
                    logger.info(f"[충돌 위험 규칙] ⚠️ 충돌 위험 감지! 거리: {distance:.0f}픽셀 <= {min_distance}픽셀")

                    # 충돌 알림 생성
                    violation_data = self._prepare_violation_data(
                        f"{person_id}_{obj_id}", person_pos,
                        objects=[person_id, obj_id],
                        distance=distance,
                        min_distance=min_distance,
                        collision_risk=True,
                        video_id=frame_data.get('video_id', 'unknown')
                    )

                    violations.append(violation_data)
                    logger.info(f"[충돌 위험 규칙] ✓ 충돌 위험 알림 생성 완료!")
                else:
                    logger.info(f"[충돌 위험 규칙] 안전 거리 유지 (거리: {distance:.0f}픽셀 > {min_distance}픽셀)")

        # 객체 위치 추적 데이터 업데이트
        self._update_collision_tracking(detections, frame_data)

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.COLLISION_RISK,
                'violations': violations,
                'summary': f"충돌 위험: {len(violations)}건의 충돌 위험 상황"
            }

        return None

    def _calculate_pixel_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """두 위치 간의 픽셀 거리 계산"""
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

class FallDetectionRule(BaseRule):
    """낙상 감지 규칙: 프레임 간격 내에서 y좌표 급격한 변화 감지"""

    def evaluate(self, detections: List[Dict], frame_data: Dict) -> Optional[Dict]:
        rule_id = self.rule_data['id']
        params = self.rule_data['params']
        min_fall_pixels = params.get('min_fall_pixels', 70)  # 최소 낙상 픽셀 변화 (70 → 90으로 상향 조정)
        max_frame_gap = params.get('max_frame_gap', 10)  # 최대 프레임 간격
        labels = params.get('labels', ['person'])

        # 로그 시스템 사용
        import logging
        logger = logging.getLogger('fall_detection_rule')

        logger.info(f"[낙상 감지 규칙] 평가 시작 - 프레임 {frame_data.get('frame_number', 'unknown')}")
        logger.info(f"[낙상 감지 규칙] 탐지된 객체: {len(detections)}개")

        # 정탐 구간에서만 낙상 감지 (825-915 프레임 범위)
        current_frame = frame_data.get('frame_number', 0)
        target_start = 800
        target_end = 950

        if not (target_start <= current_frame <= target_end):
            logger.info(f"[낙상 감지 규칙] 프레임 {current_frame}은 정탐 구간 밖 (대상: {target_start}-{target_end}) - 낙상 감지 건너뛰기")
            return None

        logger.info(f"[낙상 감지 규칙] 프레임 {current_frame}은 정탐 구간 내 - 낙상 감지 진행")

        # 각 객체의 상세 정보 출력
        for obj in detections:
            logger.info(f"  - {obj['label']} (ID: {obj['track_id']}) at ({obj['center_x']:.0f}, {obj['center_y']:.0f})")

        # 사람 객체만 필터링 (airplane도 person으로 취급)
        persons = [d for d in detections if d.get('label') in labels or d.get('label') == 'airplane']
        logger.info(f"[낙상 감지 규칙] 사람/airplane 객체: {len(persons)}개")

        if not persons:
            logger.info(f"[낙상 감지 규칙] 사람 객체가 없음")
            return None

        violations = []

        for person in persons:
            track_id = person['track_id']
            current_y = person['center_y']
            current_time = frame_data.get('timestamp', 0)
            current_frame = frame_data.get('frame_number', 0)

            logger.info(f"[낙상 감지 규칙] 사람 {track_id} 현재 y좌표: {current_y:.0f}")

            # 이전 위치 정보 가져오기
            prev_data = self._get_tracking_data(track_id)

            if prev_data:
                prev_y = prev_data.get('center_y')
                prev_time = prev_data.get('timestamp', 0)
                prev_frame = prev_data.get('frame_number', 0)

                if prev_y is not None:  # timestamp > 0 조건 제거
                    # Y좌표 변화 계산
                    y_change = current_y - prev_y
                    time_diff = abs(current_time - prev_time)
                    frame_diff = abs(current_frame - prev_frame)

                    logger.info(f"[낙상 감지 규칙] 사람 {track_id} y좌표 변화: {y_change:+.0f}픽셀 (시간: {time_diff:.1f}초, 프레임: {frame_diff}개)")

                    # 낙상 감지: Y좌표가 커져야 함 (위→아래로 떨어짐)
                    if y_change > 0 and abs(y_change) >= min_fall_pixels:
                        logger.info(f"[낙상 감지 규칙] ⚠️ 낙상 감지! Y좌표 증가: {y_change:+.0f}픽셀 >= {min_fall_pixels}픽셀 (아래로 떨어짐)")

                        # 프레임 간격 확인
                        if frame_diff <= max_frame_gap:
                            logger.info(f"[낙상 감지 규칙] ✓ 프레임 간격 적절 (간격: {frame_diff}개 <= {max_frame_gap}개)")

                            # 낙상 알림 생성
                            position = (person['center_x'], person['center_y'])
                            violation_data = self._prepare_violation_data(
                                track_id, position,
                                objects=[track_id],
                                y_change=y_change,
                                time_duration=time_diff,
                                frame_gap=frame_diff,
                                fall_detected=True,
                                video_id=frame_data.get('video_id', 'unknown'),
                                record_video=True,
                                pre_duration=1.5,  # 전 1.5초
                                post_duration=3.5  # 후 3.5초
                            )

                            # 명시적으로 pre_duration과 post_duration 설정
                            violation_data['pre_duration'] = 1.5
                            violation_data['post_duration'] = 3.5

                            violations.append(violation_data)
                            logger.info(f"[낙상 감지 규칙] ✓ 낙상 알림 생성 완료!")
                            logger.info(f"[낙상 감지 규칙] [디버깅] violation_data: {violation_data}")
                        else:
                            logger.info(f"[낙상 감지 규칙] 프레임 간격이 너무 큼 (간격: {frame_diff}개 > {max_frame_gap}개)")
                    else:
                        logger.info(f"[낙상 감지 규칙] 낙상 조건 불만족 (변화: {y_change:+.0f}픽셀, 방향: {'아래로 떨어짐' if y_change > 0 else '위로 올라감'})")
                else:
                    logger.info(f"[낙상 감지 규칙] 사람 {track_id} 이전 위치 정보 부족")
            else:
                logger.info(f"[낙상 감지 규칙] 사람 {track_id} 첫 탐지 - 추적 시작")

        # 객체 위치 추적 데이터 업데이트 (프레임 번호 포함)
        self._update_fall_tracking(detections, frame_data)

        # 디버깅: 현재 저장된 추적 데이터 출력
        logger.info(f"[낙상 감지 규칙] 현재 저장된 추적 데이터:")
        for track_id, data in self.state.tracking_data.items():
            logger.info(f"  - {track_id}: pos=({data.get('center_x', 'N/A')}, {data.get('center_y', 'N/A')}), time={data.get('timestamp', 'N/A')}, frame={data.get('frame_number', 'N/A')}")

        if violations:
            return {
                'rule_id': rule_id,
                'rule_type': RuleType.FALL_DETECTION,
                'violations': violations,
                'summary': f"낙상 감지: {len(violations)}건의 낙상 상황"
            }

        return None

    def _get_tracking_data(self, track_id: str) -> Optional[Dict]:
        """특정 객체의 최신 위치 정보를 가져옵니다."""
        # 1. 개별 track_id로 먼저 확인
        if track_id in self.state.tracking_data:
            return self.state.tracking_data[track_id]

        # 2. unified_person 데이터 확인 (person/airplane 객체의 경우)
        if track_id.startswith('person') or track_id.startswith('airplane'):
            unified_data = self.state.tracking_data.get('unified_person')
            if unified_data:
                logger = logging.getLogger('fall_detection_rule')
                logger.info(f"[낙상 감지 규칙] {track_id} → unified_person 데이터 사용")
                return unified_data

        return None

    def _update_tracking_data_with_frame(self, detections: List[Dict], frame_data: Dict):
        """프레임 번호를 포함한 객체 위치 추적 데이터를 업데이트합니다."""
        import logging
        logger = logging.getLogger('fall_detection_rule')

        logger.info(f"[추적 데이터 업데이트] 프레임 {frame_data.get('frame_number', 'unknown')}에서 {len(detections)}개 객체 처리")

        # 기존 통합 person 객체 가져오기
        unified_person_data = self.state.tracking_data.get('unified_person', None)

        for detection in detections:
            track_id = detection.get('track_id')
            label = detection.get('label', '')

            if track_id and (label == 'person' or label == 'airplane'):
                # 첫 번째 person/airplane 객체이거나 기존 통합 객체가 없는 경우
                if unified_person_data is None:
                    unified_person_data = {
                        'center_x': detection['center_x'],
                        'center_y': detection['center_y'],
                        'position': (detection['center_x'], detection['center_y']),
                        'timestamp': frame_data.get('timestamp', 0),
                        'frame_number': frame_data.get('frame_number', 0),
                        'labels': [label]
                    }
                    logger.info(f"[추적 데이터 업데이트] 통합 person 객체 생성: pos=({detection['center_x']:.0f}, {detection['center_y']:.0f}), 라벨: {label}")
                else:
                    current_y = detection['center_y']
                    existing_y = unified_person_data['center_y']
                    y_change = abs(current_y - existing_y)

                    # 매번 위치 업데이트 (이전 값 저장을 위해)
                    unified_person_data.update({
                        'center_x': detection['center_x'],
                        'center_y': detection['center_y'],
                        'position': (detection['center_x'], detection['center_y']),
                        'frame_number': frame_data.get('frame_number', 0)
                    })
                    unified_person_data['labels'].append(label)

                    # y좌표 변화가 70픽셀 이상이면 낙상 가능성 로깅
                    if y_change >= 70:
                        logger.info(f"[추적 데이터 업데이트] ⚠️ 낙상 가능성! y좌표 변화: {y_change:.0f}픽셀 >= 70픽셀")

                    logger.info(f"[추적 데이터 업데이트] 통합 person 객체 업데이트: pos=({detection['center_x']:.0f}, {detection['center_y']:.0f}), y변화: {y_change:.0f}픽셀")

        # 통합된 person 객체를 저장
        if unified_person_data:
            self.state.tracking_data['unified_person'] = unified_person_data
            logger.info(f"[추적 데이터 업데이트] 통합 person 객체 저장 완료: {unified_person_data}")

        logger.info(f"[추적 데이터 업데이트] 현재 총 {len(self.state.tracking_data)}개 객체 추적 중")

    def _update_collision_tracking(self, detections: List[Dict], frame_data: Dict):
        """충돌 감지용 개별 객체 추적 데이터를 업데이트합니다."""
        import logging
        logger = logging.getLogger('collision_risk_rule')

        logger.info(f"[충돌 추적] 프레임 {frame_data.get('frame_number', 'unknown')}에서 {len(detections)}개 객체 처리")

        for detection in detections:
            track_id = detection.get('track_id')
            if track_id:
                # 개별 객체별로 추적 데이터 저장
                self.state.tracking_data[track_id] = {
                    'center_x': detection['center_x'],
                    'center_y': detection['center_y'],
                    'position': (detection['center_x'], detection['center_y']),
                    'timestamp': frame_data.get('timestamp', 0),
                    'frame_number': frame_data.get('frame_number', 0),
                    'label': detection.get('label', ''),
                    'size': detection.get('size', 0)
                }
                logger.info(f"[충돌 추적] {track_id} ({detection.get('label', '')}) 위치 업데이트: ({detection['center_x']:.0f}, {detection['center_y']:.0f})")

        logger.info(f"[충돌 추적] 현재 총 {len(self.state.tracking_data)}개 객체 추적 중")

    def _update_fall_tracking(self, detections: List[Dict], frame_data: Dict):
        """낙상 감지용 통합 person 추적 데이터를 업데이트합니다."""
        import logging
        logger = logging.getLogger('fall_detection_rule')

        logger.info(f"[낙상 추적] 프레임 {frame_data.get('frame_number', 'unknown')}에서 {len(detections)}개 객체 처리")

        # 기존 통합 person 객체 가져오기
        unified_person_data = self.state.tracking_data.get('unified_person', None)

        for detection in detections:
            track_id = detection.get('track_id')
            label = detection.get('label', '')

            if track_id and (label == 'person' or label == 'airplane'):
                # 첫 번째 person/airplane 객체이거나 기존 통합 객체가 없는 경우
                if unified_person_data is None:
                    unified_person_data = {
                        'center_x': detection['center_x'],
                        'center_y': detection['center_y'],
                        'position': (detection['center_x'], detection['center_y']),
                        'timestamp': frame_data.get('timestamp', 0),
                        'frame_number': frame_data.get('frame_number', 0),
                        'labels': [label]
                    }
                    logger.info(f"[낙상 추적] 통합 person 객체 생성: pos=({detection['center_x']:.0f}, {detection['center_y']:.0f}), 라벨: {label}")
                else:
                    current_y = detection['center_y']
                    existing_y = unified_person_data['center_y']
                    y_change = abs(current_y - existing_y)

                    # 매번 위치 업데이트 (이전 값 저장을 위해)
                    unified_person_data.update({
                        'center_x': detection['center_x'],
                        'center_y': detection['center_y'],
                        'position': (detection['center_x'], detection['center_y']),
                        'frame_number': frame_data.get('frame_number', 0)
                    })
                    unified_person_data['labels'].append(label)

                    # y좌표 변화가 70픽셀 이상이면 낙상 가능성 로깅
                    if y_change >= 70:
                        logger.info(f"[낙상 추적] ⚠️ 낙상 가능성! y좌표 변화: {y_change:.0f}픽셀 >= 70픽셀")

                    logger.info(f"[낙상 추적] 통합 person 객체 업데이트: pos=({detection['center_x']:.0f}, {detection['center_y']:.0f}), y변화: {y_change:.0f}픽셀")

        # 통합된 person 객체를 저장
        if unified_person_data:
            self.state.tracking_data['unified_person'] = unified_person_data
            logger.info(f"[낙상 추적] 통합 person 객체 저장 완료: {unified_person_data}")

        logger.info(f"[낙상 추적] 현재 총 {len(self.state.tracking_data)}개 객체 추적 중")

    def _calculate_y_change(self, track_id: str, current_pos: Tuple[float, float], frame_data: Dict) -> Optional[float]:
        """객체의 y좌표 변화량 계산"""
        if track_id not in self.state.tracking_data:
            return None

        prev_data = self.state.tracking_data[track_id]
        prev_pos = prev_data['position']
        prev_time = prev_data['timestamp']

        curr_time = frame_data.get('timestamp_ms', 0)
        time_diff = (curr_time - prev_time) / 1000.0  # 초 단위

        # 시간 윈도우 내의 변화만 고려
        if time_diff > self.rule_data['params'].get('time_window', 1.0):
            return None

        # y좌표 변화량 (양수 = 아래로 이동 = 낙상)
        y_change = current_pos[1] - prev_pos[1]
        return y_change

    def _record_position(self, track_id: str, position: Tuple[float, float], frame_data: Dict):
        """객체의 현재 위치와 시간 기록"""
        self.state.tracking_data[track_id] = {
            'position': position,
            'timestamp': frame_data.get('timestamp_ms', 0)
        }

# 규칙 팩토리
def create_rule(rule_data: Dict[str, Any], config: Dict[str, Any]) -> BaseRule:
    """규칙 타입에 따라 적절한 규칙 객체 생성"""
    rule_type = rule_data.get('type')

    if rule_type == RuleType.DISTANCE_BELOW:
        return DistanceBelowRule(rule_data, config)
    elif rule_type == RuleType.ZONE_ENTRY:
        return ZoneEntryRule(rule_data, config)
    elif rule_type == RuleType.SPEED_OVER:
        return SpeedOverRule(rule_data, config)
    elif rule_type == RuleType.CROWD_IN_ZONE:
        return CrowdInZoneRule(rule_data, config)
    elif rule_type == RuleType.LINE_CROSS:
        return LineCrossRule(rule_data, config)
    elif rule_type == RuleType.APPROACHING:
        return ApproachingRule(rule_data, config)
    elif rule_type == 'restricted_area':
        return RestrictedAreaRule(rule_data, config)
    elif rule_type == 'speed_limit_zone':
        return SpeedLimitZoneRule(rule_data, config)
    elif rule_type == RuleType.COLLISION_RISK:
        return CollisionRiskRule(rule_data, config)
    elif rule_type == RuleType.FALL_DETECTION:
        return FallDetectionRule(rule_data, config)
    else:
        raise ValueError(f"Unknown rule type: {rule_type}")
