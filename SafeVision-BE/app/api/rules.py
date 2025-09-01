import json
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from core.config import cfg
from core.broker import broker
from rules.engine import rule_engine
from rules.schemas import (
    RuleCreate, RuleUpdate, ConfigUpdate, GlobalConfig,
    DangerZone, SafetyLine, SeverityLevel, RuleType, UserRuleCreate
)
from core.gpt_converter import GPTRuleConverter
import os

router = APIRouter()


@router.get("/rules/types")
async def get_rule_types():
    """
    사용 가능한 규칙 타입 목록 조회
    """
    try:
        rule_types = [
            {
                "type": RuleType.DISTANCE_BELOW,
                "name": "거리 위반",
                "description": "두 객체 간의 거리가 임계값 미만인 경우",
                "params": {
                    "min_distance": "float - 최소 안전 거리 (미터)",
                    "duration": "int - 위반 지속 시간 (초)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.ZONE_ENTRY,
                "name": "위험 구역 진입",
                "description": "특정 객체가 위험 구역에 진입한 경우",
                "params": {
                    "zone": "Dict - 구역 정보 (id, name, polygon, danger_level)",
                    "duration": "int - 체류 시간 (초)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.SPEED_OVER,
                "name": "과속",
                "description": "객체의 속도가 임계값을 초과한 경우 (구역 제한 옵션 포함)",
                "params": {
                    "max_speed": "float - 최대 허용 속도 (m/s)",
                    "zone_restricted": "bool - 특정 구역에서만 적용할지 여부",
                    "zone": "Dict - 구역이 지정된 경우에만 사용 (id, name, polygon)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.CROWD_IN_ZONE,
                "name": "밀집도 위반",
                "description": "특정 구역에 객체가 너무 많이 집중된 경우",
                "params": {
                    "zone": "Dict - 구역 정보 (id, name, polygon)",
                    "max_count": "int - 최대 허용 객체 수",
                    "duration": "int - 지속 시간 (초)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.LINE_CROSS,
                "name": "안전선 침범",
                "description": "객체가 안전선을 건넌 경우",
                "params": {
                    "line": "Dict - 안전선 정보 (id, name, points)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.APPROACHING,
                "name": "접근 추세",
                "description": "객체가 지속적으로 접근하는 경우",
                "params": {
                    "duration": "int - 접근 지속 시간 (초)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.COLLISION_RISK,
                "name": "충돌 위험",
                "description": "사람과 다른 객체 간의 충돌 위험이 감지된 경우 (거리 + 속도 + 방향 조건)",
                "params": {
                    "min_distance": "float - 최소 안전 거리 (미터)",
                    "min_speed": "float - 최소 위험 속도 (m/s)",
                    "duration": "int - 위반 지속 시간 (초)",
                    "labels": "List[str] - 대상 객체 라벨"
                }
            },
            {
                "type": RuleType.FALL_DETECTION,
                "name": "낙상 감지",
                "description": "사람의 급격한 Y좌표 변화로 낙상을 감지한 경우",
                "params": {
                    "min_fall_pixels": "int - 최소 낙상 픽셀 변화 (기본값: 80)",
                    "max_frame_gap": "int - 최대 프레임 간격 (기본값: 30)",
                    "frame_range": "List[int] - 정탐 프레임 범위 [800, 950]"
                }
            }
        ]

        return {
            "success": True,
            "data": rule_types
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 타입 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/rules")
async def list_rules():
    """
    모든 규칙 목록 조회
    """
    try:
        rules = cfg.get_rules()
        return {
            "success": True,
            "data": rules,
            "total_count": len(rules)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/rules/enabled")
async def list_enabled_rules():
    """
    활성화된 규칙만 조회
    """
    try:
        enabled_rules = cfg.get_enabled_rules()
        return {
            "success": True,
            "data": enabled_rules,
            "total_count": len(enabled_rules)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"활성 규칙 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """
    특정 규칙 조회

    - **rule_id**: 조회할 규칙 ID
    """
    try:
        rules = cfg.get_rules()
        rule = next((r for r in rules if r['id'] == rule_id), None)

        if not rule:
            raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

        return {
            "success": True,
            "data": rule
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/rules/user-friendly")
async def create_user_friendly_rule(user_rule: UserRuleCreate):
    """
    사용자 친화적인 규칙 생성 (GPT API로 자동 변환)

    - **user_rule**: 간단한 규칙 정보 (타입, 심각도, 설명, 지속시간만)
    """
    try:
        # GPT API 키 확인
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API 키가 설정되지 않았습니다."
            )

        # GPT 변환기 생성
        converter = GPTRuleConverter(openai_api_key)

        # GPT API로 완전한 규칙으로 변환
        complete_rule = await converter.convert_user_rule_to_complete_rule(user_rule)

        # 규칙 추가
        cfg.add_rule(complete_rule)

        # 규칙 엔진에 새 규칙 로드
        rule_engine.reload_rules()

        # SSE로 규칙 업데이트 알림
        await broker.send_rule_update({
            "action": "created",
            "rule": complete_rule
        })

        return {
            "success": True,
            "message": "규칙이 GPT API로 자동 변환되어 성공적으로 생성되었습니다.",
            "data": {
                "user_input": user_rule.dict(),
                "generated_rule": complete_rule
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/rules")
async def create_rule(rule_data: RuleCreate):
    """
    새 규칙 생성

    - **rule_data**: 생성할 규칙 정보
    """
    try:
        # 규칙 ID 생성
        new_rule = {
            "id": str(uuid.uuid4()),
            "name": rule_data.name,
            "type": rule_data.type,
            "enabled": True,
            "severity": rule_data.severity,
            "description": rule_data.description,
            "params": rule_data.params
        }

        # 규칙 추가
        cfg.add_rule(new_rule)

        # 규칙 엔진에 새 규칙 로드
        rule_engine.reload_rules()

        # SSE로 규칙 업데이트 알림
        await broker.send_rule_update({
            "action": "created",
            "rule": new_rule
        })

        return {
            "success": True,
            "message": "규칙이 성공적으로 생성되었습니다.",
            "data": new_rule
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, rule_update: RuleUpdate):
    """
    규칙 업데이트

    - **rule_id**: 업데이트할 규칙 ID
    - **rule_update**: 업데이트할 규칙 정보
    """
    try:
        # 기존 규칙 조회
        rules = cfg.get_rules()
        existing_rule = next((r for r in rules if r['id'] == rule_id), None)

        if not existing_rule:
            raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

        # 업데이트할 필드만 수정
        updated_rule = existing_rule.copy()

        if rule_update.name is not None:
            updated_rule['name'] = rule_update.name

        if rule_update.enabled is not None:
            updated_rule['enabled'] = rule_update.enabled

        if rule_update.severity is not None:
            updated_rule['severity'] = rule_update.severity

        if rule_update.description is not None:
            updated_rule['description'] = rule_update.description

        if rule_update.params is not None:
            updated_rule['params'] = rule_update.params

        # 규칙 업데이트
        success = cfg.update_rule(rule_id, updated_rule)

        if not success:
            raise HTTPException(status_code=500, detail="규칙 업데이트에 실패했습니다.")

        # 규칙 엔진에 업데이트된 규칙 로드
        rule_engine.reload_rules()

        # SSE로 규칙 업데이트 알림
        await broker.send_rule_update({
            "action": "updated",
            "rule": updated_rule
        })

        return {
            "success": True,
            "message": "규칙이 성공적으로 업데이트되었습니다.",
            "data": updated_rule
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """
    규칙 삭제

    - **rule_id**: 삭제할 규칙 ID
    """
    try:
        # 기존 규칙 조회
        rules = cfg.get_rules()
        existing_rule = next((r for r in rules if r['id'] == rule_id), None)

        if not existing_rule:
            raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

        # 규칙 삭제
        cfg.delete_rule(rule_id)

        # 규칙 엔진에서 규칙 제거
        rule_engine.reload_rules()

        # SSE로 규칙 업데이트 알림
        await broker.send_rule_update({
            "action": "deleted",
            "rule_id": rule_id
        })

        return {
            "success": True,
            "message": "규칙이 성공적으로 삭제되었습니다.",
            "deleted_rule": existing_rule
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 삭제 중 오류가 발생했습니다: {str(e)}"
        )

@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, enabled: bool = Body(..., embed=True)):
    """
    규칙 활성화/비활성화 토글

    - **rule_id**: 토글할 규칙 ID
    - **enabled**: 활성화 여부
    """
    try:
        success = cfg.toggle_rule(rule_id, enabled)

        if not success:
            raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

        # 규칙 엔진에 변경사항 반영
        rule_engine.reload_rules()

        # SSE로 규칙 업데이트 알림
        await broker.send_rule_update({
            "action": "toggled",
            "rule_id": rule_id,
            "enabled": enabled
        })

        status = "활성화" if enabled else "비활성화"
        return {
            "success": True,
            "message": f"규칙이 {status}되었습니다.",
            "rule_id": rule_id,
            "enabled": enabled
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 토글 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/config")
async def get_config():
    """
    전역 설정 조회
    """
    try:
        config_data = {
            "pixel_to_meter": cfg.get('pixel_to_meter'),
            "sample_fps": cfg.get('sample_fps'),
            "cooldown": cfg.get('cooldown'),
            "confidence_threshold": cfg.get('confidence_threshold'),
            "tracking_buffer": cfg.get('tracking_buffer'),
            "danger_zones": cfg.get('danger_zones'),
            "safety_lines": cfg.get('safety_lines')
        }

        return {
            "success": True,
            "data": config_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"설정 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.put("/config")
async def update_config(config_update: ConfigUpdate):
    """
    전역 설정 업데이트

    - **config_update**: 업데이트할 설정 정보
    """
    try:
        # 설정 업데이트
        if config_update.pixel_to_meter is not None:
            cfg.set('pixel_to_meter', config_update.pixel_to_meter)

        if config_update.sample_fps is not None:
            cfg.set('sample_fps', config_update.sample_fps)

        if config_update.cooldown is not None:
            cfg.set('cooldown', config_update.cooldown)

        if config_update.confidence_threshold is not None:
            cfg.set('confidence_threshold', config_update.confidence_threshold)

        if config_update.tracking_buffer is not None:
            cfg.set('tracking_buffer', config_update.tracking_buffer)

        # SSE로 설정 업데이트 알림
        await broker.send_config_update({
            "action": "updated",
            "config": config_update.dict(exclude_unset=True)
        })

        return {
            "success": True,
            "message": "설정이 성공적으로 업데이트되었습니다.",
            "data": config_update.dict(exclude_unset=True)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"설정 업데이트 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/config/danger-zones")
async def add_danger_zone(zone: DangerZone):
    """
    위험 구역 추가

    - **zone**: 추가할 위험 구역 정보
    """
    try:
        danger_zones = cfg.get('danger_zones', [])
        danger_zones.append(zone.dict())
        cfg.set('danger_zones', danger_zones)

        # SSE로 설정 업데이트 알림
        await broker.send_config_update({
            "action": "danger_zone_added",
            "zone": zone.dict()
        })

        return {
            "success": True,
            "message": "위험 구역이 추가되었습니다.",
            "data": zone.dict()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"위험 구역 추가 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/config/safety-lines")
async def add_safety_line(line: SafetyLine):
    """
    안전선 추가

    - **line**: 추가할 안전선 정보
    """
    try:
        safety_lines = cfg.get('safety_lines', [])
        safety_lines.append(line.dict())
        cfg.set('safety_lines', safety_lines)

        # SSE로 설정 업데이트 알림
        await broker.send_config_update({
            "action": "safety_line_added",
            "line": line.dict()
        })

        return {
            "success": True,
            "message": "안전선이 추가되었습니다.",
            "data": line.dict()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"안전선 추가 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/rules/refresh")
async def refresh_rules():
    """
    규칙 디렉토리에서 규칙 새로고침
    """
    try:
        # 설정에서 규칙 새로고침
        cfg.refresh_rules()

        # 규칙 엔진에 새로고침된 규칙 로드
        rule_engine.reload_rules()

        # SSE로 규칙 업데이트 알림
        await broker.send_rule_update({
            "action": "refreshed",
            "message": "규칙이 새로고침되었습니다."
        })

        return {
            "success": True,
            "message": "규칙이 성공적으로 새로고침되었습니다.",
            "total_rules": len(cfg.get_rules()),
            "enabled_rules": len(cfg.get_enabled_rules())
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 새로고침 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/rules/engine/status")
async def get_rule_engine_status():
    """
    규칙 엔진 상태 조회
    """
    try:
        rule_info = rule_engine.get_rule_info()

        return {
            "success": True,
            "data": {
                "total_rules": len(rule_info),
                "enabled_rules": len([r for r in rule_info if r['enabled']]),
                "disabled_rules": len([r for r in rule_info if not r['enabled']]),
                "rules": rule_info
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 엔진 상태 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/rules/test")
async def test_rule(
    rule_data: Dict[str, Any] = Body(...),
    test_detections: List[Dict[str, Any]] = Body(...),
    test_frame_data: Dict[str, Any] = Body(...)
):
    """
    규칙 테스트 (실제 비디오 없이)

    - **rule_data**: 테스트할 규칙 데이터
    - **test_detections**: 테스트용 감지 데이터
    - **test_frame_data**: 테스트용 프레임 데이터
    """
    try:
        result = rule_engine.test_rule(rule_data, test_detections, test_frame_data)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"규칙 테스트 중 오류가 발생했습니다: {str(e)}"
        )
