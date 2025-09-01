import openai
import json
from typing import Dict, Any
from rules.schemas import UserRuleCreate, RuleType, SeverityLevel
import uuid

class GPTRuleConverter:
    """GPT API를 사용하여 사용자 입력을 완전한 규칙으로 변환"""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)

    async def convert_user_rule_to_complete_rule(self, user_rule: UserRuleCreate) -> Dict[str, Any]:
        """사용자 입력을 GPT API로 완전한 규칙으로 변환"""

        # GPT 프롬프트 구성
        prompt = self._create_conversion_prompt(user_rule)

        try:
            # GPT API 호출
            response = await self.client.chat.completions.acreate(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 안전 모니터링 시스템의 규칙 생성 전문가입니다. 사용자의 간단한 입력을 완전한 규칙으로 변환해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )

            # GPT 응답 파싱
            gpt_response = response.choices[0].message.content
            complete_rule = self._parse_gpt_response(gpt_response, user_rule)

            return complete_rule

        except Exception as e:
            print(f"GPT API 변환 실패: {e}")
            # GPT 실패 시 기본 규칙 생성
            return self._create_default_rule(user_rule)

    def _create_conversion_prompt(self, user_rule: UserRuleCreate) -> str:
        """GPT 변환을 위한 프롬프트 생성"""

        # 타입을 문자열로 변환
        rule_type_str = user_rule.type.value if hasattr(user_rule.type, 'value') else str(user_rule.type)

        rule_type_info = {
            "distance_below": "두 객체 간의 거리가 임계값 미만인 경우. min_distance, labels 필요.",
            "zone_entry": "특정 객체가 위험 구역에 진입한 경우. zone 정보, labels 필요.",
            "speed_over": "객체의 속도가 임계값을 초과한 경우. max_speed, labels 필요.",
            "crowd_in_zone": "특정 구역에 객체가 너무 많이 집중된 경우. zone, max_count, labels 필요.",
            "line_cross": "객체가 안전선을 건넌 경우. line 정보, labels 필요.",
            "approaching": "객체가 지속적으로 접근하는 경우. duration, labels 필요.",
            "collision_risk": "사람과 다른 객체 간의 충돌 위험. min_distance, min_speed, labels 필요.",
            "fall_detection": "사람의 급격한 Y좌표 변화. min_fall_pixels, max_frame_gap, frame_range 필요."
        }

        prompt = f"""
사용자가 입력한 규칙을 완전한 규칙으로 변환해주세요.

사용자 입력:
- 이름: {user_rule.name}
- 타입: {rule_type_str}
- 심각도: {user_rule.severity}
- 설명: {user_rule.description or '설명 없음'}
- 지속시간: {user_rule.duration}초

규칙 타입 정보: {rule_type_info.get(rule_type_str, '알 수 없는 타입')}

다음 JSON 형식으로 응답해주세요:
{{
    "name": "규칙 이름",
    "type": "규칙 타입",
    "severity": "심각도",
    "description": "상세 설명",
    "params": {{
        // 규칙 타입에 맞는 파라미터들
    }}
}}

부족한 정보는 적절한 기본값으로 채워주세요.
"""
        return prompt

    def _parse_gpt_response(self, gpt_response: str, user_rule: UserRuleCreate) -> Dict[str, Any]:
        """GPT 응답을 파싱하여 규칙 생성"""
        try:
            # JSON 추출 시도
            if "```json" in gpt_response:
                json_start = gpt_response.find("```json") + 7
                json_end = gpt_response.find("```", json_start)
                json_str = gpt_response[json_start:json_end].strip()
            else:
                # JSON 블록이 없으면 전체 응답에서 JSON 찾기
                json_str = gpt_response

            # JSON 파싱
            rule_data = json.loads(json_str)

            # 필수 필드 검증 및 보완
            complete_rule = {
                "id": str(uuid.uuid4()),
                "name": rule_data.get("name", user_rule.name),
                "type": rule_data.get("type", user_rule.type.value),
                "enabled": True,
                "severity": rule_data.get("severity", user_rule.severity.value),
                "description": rule_data.get("description", user_rule.description),
                "params": rule_data.get("params", {})
            }

            return complete_rule

        except Exception as e:
            print(f"GPT 응답 파싱 실패: {e}")
            return self._create_default_rule(user_rule)

    def _create_default_rule(self, user_rule: UserRuleCreate) -> Dict[str, Any]:
        """GPT 실패 시 기본 규칙 생성"""

        # 타입을 문자열로 변환
        rule_type_str = user_rule.type.value if hasattr(user_rule.type, 'value') else str(user_rule.type)

        default_params = {
            "distance_below": {
                "min_distance": 2.0,
                "duration": user_rule.duration,
                "labels": ["person", "car"]
            },
            "zone_entry": {
                "zone": {
                    "id": "auto_generated_zone",
                    "name": "자동 생성 구역",
                    "polygon": [[100, 100], [300, 100], [300, 300], [100, 300]],
                    "danger_level": user_rule.severity.value
                },
                "duration": user_rule.duration,
                "labels": ["person"]
            },
            "speed_over": {
                "max_speed": 5.0,
                "labels": ["car", "truck"]
            },
            "crowd_in_zone": {
                "zone": {
                    "id": "auto_generated_crowd_zone",
                    "name": "자동 생성 밀집 구역",
                    "polygon": [[200, 200], [400, 200], [400, 400], [200, 400]]
                },
                "max_count": 3,
                "duration": user_rule.duration,
                "labels": ["person"]
            },
            "line_cross": {
                "line": {
                    "id": "auto_generated_line",
                    "name": "자동 생성 안전선",
                    "points": [[50, 250], [450, 250]],
                    "direction": "horizontal"
                },
                "labels": ["person", "car"]
            },
            "approaching": {
                "duration": user_rule.duration,
                "labels": ["person", "car"]
            },
            "collision_risk": {
                "min_distance": 2.0,
                "min_speed": 2.0,
                "duration": user_rule.duration,
                "labels": ["person", "car"]
            },
            "fall_detection": {
                "min_fall_pixels": 80,
                "max_frame_gap": 30,
                "frame_range": [800, 950],
                "labels": ["person"]
            }
        }

        return {
            "id": str(uuid.uuid4()),
            "name": user_rule.name,
            "type": rule_type_str,
            "enabled": True,
            "severity": user_rule.severity.value,
            "description": user_rule.description or f"자동 생성된 {rule_type_str} 규칙",
            "params": default_params.get(rule_type_str, {})
        }
