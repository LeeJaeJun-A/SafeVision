import os
import json
import uuid
import logging
from typing import Dict, Any
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"
CONFIG_FILE = STORAGE_DIR / "config.json"
RULES_FILE = STORAGE_DIR / "rules.json"

# 로거 설정
logger = logging.getLogger('config')

# 기본 설정값 (config.json이 없을 때 사용)
FALLBACK_CONFIG = {
    "pixel_to_meter": 0.05,  # 픽셀당 미터 비율 (더 정밀하게)
    "sample_fps": 5,         # 분석할 프레임 수 (초당)
    "cooldown": 60,          # 알림 쿨다운 (초) - 중복 방지
    "confidence_threshold": 0.5,  # YOLO 신뢰도 임계값
    "tracking_buffer": 10,   # 트래킹 버퍼 크기
    "min_violation_interval": 30,  # 최소 위반 간격 (초) - 같은 현상 재탐지 방지

    # 원근감 관련 설정
    "camera_height": 3.0,    # 카메라 설치 높이 (미터)
    "camera_angle": 15,      # 카메라 설치 각도 (도, 수평에서 아래로)
    "focal_length": 1000,    # 카메라 초점 거리 (픽셀)
    "image_height": 1080,    # 이미지 높이 (픽셀)
    "ground_plane_y": 800,   # 지면 기준선 Y 좌표 (픽셀)
    "max_detection_distance": 20.0,  # 최대 탐지 거리 (미터)
    "min_detection_distance": 1.0,   # 최소 탐지 거리 (미터)
}

# 기본 규칙 설정
DEFAULT_RULES = [
    {
        "id": str(uuid.uuid4()),
        "name": "거리 위반",
        "type": "distance_below",
        "enabled": True,
        "severity": "medium",
        "description": "두 객체 간 거리가 지정된 최소 거리 미만으로 유지되는 경우",
        "params": {
            "min_distance": 1.5,  # 더 가까운 거리에서 탐지
            "duration": 3,
            "labels": ["person", "forklift"]
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "위험 구역 진입",
        "type": "zone_entry",
        "enabled": True,
        "severity": "high",
        "description": "사람이나 차량이 위험 구역에 진입하여 지정된 시간 동안 체류하는 경우",
        "params": {
            "zone": {
                "id": "zone_1",
                "name": "작업 구역 A",
                "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
                "danger_level": "high"
            },
            "duration": 2,
            "labels": ["person"]
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "과속",
        "type": "speed_over",
        "enabled": True,
        "severity": "high",
        "description": "차량이나 지게차의 속도가 지정된 최대 속도를 초과하는 경우",
        "params": {
            "max_speed": 3.0,  # 더 낮은 속도에서 탐지
            "labels": ["forklift", "car"]
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "밀집도 위반",
        "type": "crowd_in_zone",
        "enabled": True,
        "severity": "medium",
        "description": "특정 구역에 지정된 최대 인원 수를 초과하여 밀집하는 경우",
        "params": {
            "zone": {
                "id": "zone_1",
                "name": "작업 구역 A",
                "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
                "danger_level": "high"
            },
            "max_count": 3,
            "duration": 5,
            "labels": ["person"]
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "안전선 침범",
        "type": "line_cross",
        "enabled": True,
        "severity": "critical",
        "description": "사람이나 차량이 지정된 안전선을 침범하는 경우",
        "params": {
            "line": {
                "id": "line_1",
                "name": "접근 금지선",
                "points": [[50, 200], [350, 200]],
                "direction": "horizontal"
            },
            "labels": ["person", "forklift"]
        }
    },
    {
        "id": str(uuid.uuid4()),
        "name": "접근 추세",
        "type": "approaching",
        "enabled": True,
        "severity": "low",
        "description": "한 객체가 다른 객체를 향해 지속적으로 접근하는 경우",
        "params": {
            "duration": 3,
            "labels": ["person", "forklift"]
        }
    }
]

class Config:
    def __init__(self):
        self._config = {}
        self._rules = []
        self.load_config()
        self.load_rules()

    def load_config(self):
        """설정 파일 로드"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
                self._config = FALLBACK_CONFIG.copy()
                self.save_config()
        else:
            self._config = FALLBACK_CONFIG.copy()
            self.save_config()

    def load_rules(self):
        """규칙 디렉토리에서 모든 JSON 파일 로드"""
        rules_dir = STORAGE_DIR / "rules"
        self._rules = []

        if rules_dir.exists():
            try:
                for rule_file in rules_dir.glob("*.json"):
                    try:
                        with open(rule_file, 'r', encoding='utf-8') as f:
                            rule_data = json.load(f)
                            self._rules.append(rule_data)
                            logger.info(f"규칙 로드: {rule_data.get('name')} (enabled: {rule_data.get('enabled')} - 타입: {type(rule_data.get('enabled'))})")
                    except Exception as e:
                        logger.error(f"규칙 파일 로드 실패 {rule_file}: {e}")
                        continue
            except Exception as e:
                logger.error(f"규칙 디렉토리 로드 실패: {e}")

        # 규칙이 없으면 기본 규칙 생성
        if not self._rules:
            self._rules = DEFAULT_RULES.copy()
            self.save_rules()

        logger.info(f"로드된 규칙 수: {len(self._rules)}")

        # 활성화된 규칙만 출력
        enabled_rules = [rule for rule in self._rules if rule.get('enabled', False)]
        logger.info(f"활성화된 규칙 수: {len(enabled_rules)}")
        for rule in enabled_rules:
            logger.info(f"  - 활성화: {rule.get('name')} ({rule.get('type')})")

    def save_config(self):
        """설정 파일 저장"""
        STORAGE_DIR.mkdir(exist_ok=True)
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")

    def save_rules(self):
        """규칙을 개별 JSON 파일로 저장"""
        rules_dir = STORAGE_DIR / "rules"
        rules_dir.mkdir(exist_ok=True)

        try:
            for rule in self._rules:
                rule_file = rules_dir / f"{rule['id']}.json"
                with open(rule_file, 'w', encoding='utf-8') as f:
                    json.dump(rule, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"규칙 파일 저장 실패: {e}")

    def get(self, key: str, default=None):
        """설정값 조회"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """설정값 설정"""
        self._config[key] = value
        self.save_config()

    def get_rules(self):
        """모든 규칙 조회"""
        return self._rules

    def get_enabled_rules(self):
        """활성화된 규칙만 조회"""
        enabled_rules = [rule for rule in self._rules if rule.get('enabled', False)]
        logger.info(f"[get_enabled_rules] 활성화된 규칙 {len(enabled_rules)}개 반환:")
        for rule in enabled_rules:
            logger.info(f"  - {rule.get('name')} ({rule.get('type')}) - enabled: {rule.get('enabled')}")
        return enabled_rules

    def add_rule(self, rule: Dict):
        """규칙 추가 (UUID 자동 생성)"""
        if 'id' not in rule or not rule['id']:
            rule['id'] = str(uuid.uuid4())
        self._rules.append(rule)
        self.save_rules()

    def update_rule(self, rule_id: str, rule: Dict):
        """규칙 업데이트"""
        for i, existing_rule in enumerate(self._rules):
            if existing_rule.get('id') == rule_id:
                # ID는 변경하지 않음
                rule['id'] = rule_id
                self._rules[i] = rule
                self.save_rules()
                return True
        return False

    def delete_rule(self, rule_id: str):
        """규칙 삭제"""
        # 파일도 함께 삭제
        rules_dir = STORAGE_DIR / "rules"
        rule_file = rules_dir / f"{rule_id}.json"
        if rule_file.exists():
            try:
                rule_file.unlink()
            except Exception as e:
                logger.error(f"규칙 파일 삭제 실패: {e}")

        self._rules = [rule for rule in self._rules if rule.get('id') != rule_id]
        self.save_rules()

    def toggle_rule(self, rule_id: str, enabled: bool):
        """규칙 활성화/비활성화"""
        for rule in self._rules:
            if rule.get('id') == rule_id:
                rule['enabled'] = enabled
                self.save_rules()
                return True
        return False

    def refresh_rules(self):
        """규칙 디렉토리에서 규칙 새로고침"""
        self.load_rules()

# 전역 설정 인스턴스
cfg = Config()

def save_config():
    """설정 저장 (외부에서 호출용)"""
    cfg.save_config()
