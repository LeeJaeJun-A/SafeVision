from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional, Union
from enum import Enum

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    UNPROCESSED = "unprocessed"  # 미처리
    PROCESSING = "processing"    # 처리중
    COMPLETED = "completed"      # 처리완료

class RuleType(str, Enum):
    # 기본 안전 규칙들
    DISTANCE_BELOW = "distance_below"      # 두 객체 간 거리 위반
    ZONE_ENTRY = "zone_entry"              # 위험 구역 진입
    SPEED_OVER = "speed_over"              # 과속
    CROWD_IN_ZONE = "crowd_in_zone"        # 밀집도 위반
    LINE_CROSS = "line_cross"              # 안전선 침범
    APPROACHING = "approaching"            # 접근 추세

    # 고급 안전 규칙들
    COLLISION_RISK = "collision_risk"      # 충돌 위험 (거리 + 속도 + 방향)
    FALL_DETECTION = "fall_detection"      # 낙상 감지

class BaseRule(BaseModel):
    id: str = Field(..., description="규칙 고유 ID")
    name: str = Field(..., description="규칙 이름")
    type: RuleType = Field(..., description="규칙 타입")
    enabled: bool = Field(default=True, description="규칙 활성화 여부")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="알림 심각도")
    description: Optional[str] = Field(None, description="규칙 설명")
    params: Dict[str, Any] = Field(default_factory=dict, description="규칙 파라미터")

class DistanceBelowRule(BaseRule):
    type: RuleType = Field(default=RuleType.DISTANCE_BELOW)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "min_distance": 2.0,
        "duration": 3,
        "labels": ["person", "forklift"]
    })

class ZoneEntryRule(BaseRule):
    type: RuleType = Field(default=RuleType.ZONE_ENTRY)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "zone": {
            "id": "zone_1",
            "name": "위험 구역",
            "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
            "danger_level": "high"
        },
        "duration": 2,
        "labels": ["person", "forklift", "car"]
    })

class SpeedOverRule(BaseRule):
    type: RuleType = Field(default=RuleType.SPEED_OVER)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "max_speed": 5.0,
        "zone_restricted": False,  # 특정 구역에서만 적용할지 여부
        "zone": None,              # 구역이 지정된 경우에만 사용
        "labels": ["forklift", "car", "truck"]
    })

class CrowdInZoneRule(BaseRule):
    type: RuleType = Field(default=RuleType.CROWD_IN_ZONE)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "zone_id": "zone_1",
        "max_count": 3,
        "duration": 5,
        "labels": ["person"]
    })

class LineCrossRule(BaseRule):
    type: RuleType = Field(default=RuleType.LINE_CROSS)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "line_id": "line_1",
        "labels": ["person", "forklift"]
    })

class ApproachingRule(BaseRule):
    type: RuleType = Field(default=RuleType.APPROACHING)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "duration": 3,
        "labels": ["person", "forklift"]
    })

class CollisionRiskRule(BaseRule):
    """충돌 위험 복합 규칙: 거리 + 속도 조건"""
    type: RuleType = Field(default=RuleType.COLLISION_RISK)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "min_distance": 2.0,      # 최소 안전 거리 (미터)
        "min_speed": 2.0,         # 최소 위험 속도 (m/s) - 이 속도 이상일 때 위험
        "duration": 2,            # 지속 시간 (초)
        "labels": ["person", "forklift", "car"],
        "speed_labels": ["car", "forklift"]  # 속도 체크 대상
    })

class FallDetectionRule(BaseRule):
    """낙상 감지 규칙: person의 y좌표가 급격하게 감소하는 경우"""
    type: RuleType = Field(default=RuleType.FALL_DETECTION)
    params: Dict[str, Any] = Field(default_factory=lambda: {
        "min_y_change": 50,       # 최소 y좌표 변화량 (픽셀)
        "time_window": 1.0,       # 변화 감지 시간 윈도우 (초)
        "labels": ["person"],      # 감지 대상 라벨
        "min_confidence": 0.7     # 최소 신뢰도
    })

# 규칙 타입별 유니온 타입
Rule = Union[
    DistanceBelowRule,
    ZoneEntryRule,
    SpeedOverRule,
    CrowdInZoneRule,
    LineCrossRule,
    ApproachingRule,
    CollisionRiskRule,
    FallDetectionRule
]

class UserRuleCreate(BaseModel):
    """사용자 친화적인 규칙 생성 스키마"""
    name: str = Field(..., description="규칙 이름")
    type: str = Field(..., description="규칙 타입 (대소문자 구분 없음)")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="알림 심각도")
    description: Optional[str] = Field(None, description="규칙 설명")
    duration: Optional[int] = Field(default=3, description="위반 지속 시간 (초)")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """타입을 소문자로 변환하고 유효성 검사"""
        if isinstance(v, str):
            v = v.lower()

        # 유효한 타입인지 확인
        try:
            return RuleType(v)
        except ValueError:
            raise ValueError(f"유효하지 않은 규칙 타입: {v}. 사용 가능한 타입: {[t.value for t in RuleType]}")

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v):
        """심각도를 문자열로 변환하고 유효성 검사"""
        if isinstance(v, str):
            v = v.lower()

        try:
            return SeverityLevel(v)
        except ValueError:
            raise ValueError(f"유효하지 않은 심각도: {v}. 사용 가능한 심각도: {[s.value for s in SeverityLevel]}")

class RuleCreate(BaseModel):
    name: str = Field(..., description="규칙 이름")
    type: RuleType = Field(..., description="규칙 타입")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="알림 심각도")
    description: Optional[str] = Field(None, description="규칙 설명")
    params: Dict[str, Any] = Field(default_factory=dict, description="규칙 파라미터")

class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="규칙 이름")
    enabled: Optional[bool] = Field(None, description="규칙 활성화 여부")
    severity: Optional[SeverityLevel] = Field(None, description="알림 심각도")
    description: Optional[str] = Field(None, description="규칙 설명")
    params: Optional[Dict[str, Any]] = Field(None, description="규칙 파라미터")

class ConfigUpdate(BaseModel):
    pixel_to_meter: Optional[float] = Field(None, description="픽셀당 미터 비율")
    sample_fps: Optional[int] = Field(None, description="분석할 프레임 수 (초당)")
    cooldown: Optional[int] = Field(None, description="알림 쿨다운 (초)")
    confidence_threshold: Optional[float] = Field(None, description="YOLO 신뢰도 임계값")
    tracking_buffer: Optional[int] = Field(None, description="트래킹 버퍼 크기")

class DangerZone(BaseModel):
    id: str = Field(..., description="위험 구역 ID")
    name: str = Field(..., description="위험 구역 이름")
    polygon: List[List[int]] = Field(..., description="폴리곤 좌표")
    danger_level: SeverityLevel = Field(default=SeverityLevel.HIGH, description="위험도 레벨")

class SafetyLine(BaseModel):
    id: str = Field(..., description="안전선 ID")
    name: str = Field(..., description="안전선 이름")
    points: List[List[int]] = Field(..., description="선의 시작점과 끝점")
    direction: str = Field(default="horizontal", description="선의 방향")

class GlobalConfig(BaseModel):
    pixel_to_meter: float = Field(default=0.1, description="픽셀당 미터 비율")
    sample_fps: int = Field(default=5, description="분석할 프레임 수 (초당)")
    cooldown: int = Field(default=30, description="알림 쿨다운 (초)")
    confidence_threshold: float = Field(default=0.5, description="YOLO 신뢰도 임계값")
    tracking_buffer: int = Field(default=10, description="트래킹 버퍼 크기")
    danger_zones: List[DangerZone] = Field(default_factory=list, description="위험 구역 목록")
    safety_lines: List[SafetyLine] = Field(default_factory=list, description="안전선 목록")

class AlertCreate(BaseModel):
    rule_id: str = Field(..., description="규칙 ID")
    rule_type: RuleType = Field(..., description="규칙 타입")
    ts_ms: int = Field(..., description="타임스탬프 (밀리초)")
    summary: str = Field(..., description="알림 요약")
    detail: Dict[str, Any] = Field(default_factory=dict, description="상세 정보")
    video_id: Optional[str] = Field(None, description="비디오 ID")
    frame_number: Optional[int] = Field(None, description="프레임 번호")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="알림 심각도")

class AlertResponse(BaseModel):
    alertId: str = Field(..., description="알림 ID")
    rule_id: str = Field(..., description="규칙 ID")
    rule_type: RuleType = Field(..., description="규칙 타입")
    ts_ms: int = Field(..., description="타임스탬프 (밀리초)")
    summary: str = Field(..., description="알림 요약")
    detail: Dict[str, Any] = Field(..., description="상세 정보")
    created_at: str = Field(..., description="생성 시간")
    video_id: Optional[str] = Field(None, description="비디오 ID")
    frame_number: Optional[int] = Field(None, description="프레임 번호")
    severity: SeverityLevel = Field(..., description="알림 심각도")
    status: AlertStatus = Field(default=AlertStatus.UNPROCESSED, description="알림 상태")
    processed_at: Optional[str] = Field(None, description="처리 시간")
    video_clip_path: Optional[str] = Field(None, description="비디오 클립 파일 경로")

class AlertStatusUpdate(BaseModel):
    status: AlertStatus = Field(..., description="변경할 상태")
