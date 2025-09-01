import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

# MongoDB 연결 설정
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "safe_vision"

# MongoDB 연결 옵션
MONGODB_OPTIONS = {
    "maxPoolSize": 10,
    "minPoolSize": 1,
    "maxIdleTimeMS": 30000,
    "serverSelectionTimeoutMS": 5000,
    "connectTimeoutMS": 10000,
    "socketTimeoutMS": 10000
}

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        # 비동기 초기화는 별도로 호출해야 함

    async def init_db(self):
        """MongoDB 연결 및 컬렉션 초기화"""
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL, **MONGODB_OPTIONS)
            self.db = self.client[DATABASE_NAME]

            # 컬렉션 존재 확인 및 인덱스 생성
            await self._create_indexes()

        except Exception as e:
            print(f"MongoDB 연결 실패: {e}")
            raise

    async def _create_indexes(self):
        """컬렉션 인덱스 생성"""
        try:
            # 알림 컬렉션 인덱스
            await self.db.alerts.create_index([("created_at", DESCENDING)])
            await self.db.alerts.create_index([("rule_type", ASCENDING)])
            await self.db.alerts.create_index([("status", ASCENDING)])
            await self.db.alerts.create_index([("video_id", ASCENDING)])

            # 비디오 분석 컬렉션 인덱스
            await self.db.video_analysis.create_index([("video_id", ASCENDING)])
            await self.db.video_analysis.create_index([("timestamp_ms", ASCENDING)])

            # 규칙 실행 히스토리 컬렉션 인덱스
            await self.db.rule_executions.create_index([("rule_id", ASCENDING)])
            await self.db.rule_executions.create_index([("video_id", ASCENDING)])
        except Exception as e:
            print(f"인덱스 생성 실패: {e}")

    def get_connection(self):
        """MongoDB 연결 반환 (하위 호환성을 위해 유지)"""
        return self.db

    async def create_alert(self, alert_data: Dict[str, Any]) -> str:
        """새 알림 생성"""
        try:
            # MongoDB 문서 생성
            alert_doc = {
                "alertId": alert_data['alertId'],
                "rule_id": alert_data['rule_id'],
                "rule_type": alert_data['rule_type'],
                "ts_ms": alert_data['ts_ms'],
                "summary": alert_data['summary'],
                "detail": alert_data.get('detail', {}),
                "video_id": alert_data.get('video_id'),
                "frame_number": alert_data.get('frame_number'),
                "severity": alert_data.get('severity', 'medium'),
                "status": alert_data.get('status', 'unprocessed'),
                "video_clip_path": alert_data.get('video_clip_path'),
                "created_at": datetime.now(),
                "processed_at": None
            }

            result = await self.db.alerts.insert_one(alert_doc)
            return alert_data['alertId']
        except Exception as e:
            print(f"알림 생성 실패: {e}")
            raise

    async def get_alerts(self, limit: int = 50, offset: int = 0, rule_type: Optional[str] = None,
                        video_id: Optional[str] = None, severity: Optional[str] = None,
                        status: Optional[str] = None) -> List[Dict]:
        """알림 목록 조회"""
        try:
            # MongoDB 필터 구성
            filter_query = {}

            if rule_type:
                filter_query["rule_type"] = rule_type

            if video_id:
                filter_query["video_id"] = video_id

            if severity:
                filter_query["severity"] = severity

            if status:
                filter_query["status"] = status

            # MongoDB 쿼리 실행
            cursor = self.db.alerts.find(filter_query).sort("created_at", DESCENDING).skip(offset).limit(limit)

            alerts = []
            async for doc in cursor:
                # ObjectId를 문자열로 변환
                doc["_id"] = str(doc["_id"])

                # created_at을 문자열로 변환
                if doc.get("created_at") and isinstance(doc["created_at"], datetime):
                    doc["created_at"] = doc["created_at"].isoformat()

                # processed_at을 문자열로 변환
                if doc.get("processed_at") and isinstance(doc["processed_at"], datetime):
                    doc["processed_at"] = doc["processed_at"].isoformat()

                alerts.append(doc)

            return alerts

        except Exception as e:
            print(f"알림 목록 조회 실패: {e}")
            raise

    async def get_alert(self, alert_id: str) -> Optional[Dict]:
        """특정 알림 조회"""
        try:
            doc = await self.db.alerts.find_one({"alertId": alert_id})
            if doc:
                # ObjectId를 문자열로 변환
                doc["_id"] = str(doc["_id"])

                # created_at을 문자열로 변환
                if doc.get("created_at") and isinstance(doc["created_at"], datetime):
                    doc["created_at"] = doc["created_at"].isoformat()

                # processed_at을 문자열로 변환
                if doc.get("processed_at") and isinstance(doc["processed_at"], datetime):
                    doc["processed_at"] = doc["processed_at"].isoformat()

                return doc
            return None
        except Exception as e:
            print(f"알림 조회 실패: {e}")
            raise

    async def save_video_analysis(self, video_id: str, frame_number: int, timestamp_ms: int, detections: List[Dict]) -> str:
        """비디오 분석 결과 저장"""
        try:
            analysis_doc = {
                "video_id": video_id,
                "frame_number": frame_number,
                "timestamp_ms": timestamp_ms,
                "detections": detections,
                "created_at": datetime.now()
            }

            result = await self.db.video_analysis.insert_one(analysis_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"비디오 분석 저장 실패: {e}")
            raise

    async def save_rule_execution(self, rule_id: str, video_id: str, frame_number: int, timestamp_ms: int, result: bool, details: Dict = None) -> str:
        """규칙 실행 결과 저장"""
        try:
            execution_doc = {
                "rule_id": rule_id,
                "video_id": video_id,
                "frame_number": frame_number,
                "timestamp_ms": timestamp_ms,
                "result": result,
                "details": details or {},
                "created_at": datetime.now()
            }

            result = await self.db.rule_executions.insert_one(execution_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"규칙 실행 결과 저장 실패: {e}")
            raise

    async def get_alert_stats(self) -> Dict[str, Any]:
        """알림 통계 조회"""
        try:
            # 전체 알림 수
            total_alerts = await self.db.alerts.count_documents({})

            # 규칙별 알림 수
            pipeline = [
                {"$group": {"_id": "$rule_type", "count": {"$sum": 1}}}
            ]
            rule_counts_cursor = self.db.alerts.aggregate(pipeline)
            rule_counts = {}
            async for doc in rule_counts_cursor:
                rule_counts[doc["_id"]] = doc["count"]

            # 최근 24시간 알림 수
            from datetime import timedelta
            yesterday = datetime.now() - timedelta(days=1)
            recent_alerts = await self.db.alerts.count_documents({
                "created_at": {"$gte": yesterday}
            })

            # 상태별 알림 수
            unprocessed_count = await self.db.alerts.count_documents({"status": "unprocessed"})
            processing_count = await self.db.alerts.count_documents({"status": "processing"})
            completed_count = await self.db.alerts.count_documents({"status": "completed"})

            return {
                'total_alerts': total_alerts,
                'rule_counts': rule_counts,
                'recent_alerts_24h': recent_alerts,
                'status_counts': {
                    'unprocessed': unprocessed_count,
                    'processing': processing_count,
                    'completed': completed_count
                }
            }
        except Exception as e:
            print(f"알림 통계 조회 실패: {e}")
            raise

    async def update_alert_status(self, alert_id: str, status: str) -> bool:
        """알림 상태 업데이트 (미처리/처리중/처리완료)"""
        try:
            update_data = {"status": status}

            if status in ['processing', 'completed']:
                update_data.update({
                    "processed_at": datetime.now()
                })
            elif status == 'unprocessed':
                update_data.update({
                    "processed_at": None
                })

            result = await self.db.alerts.update_one(
                {"alertId": alert_id},
                {"$set": update_data}
            )

            return result.modified_count > 0
        except Exception as e:
            print(f"알림 상태 업데이트 실패: {e}")
            raise

    async def get_unprocessed_alerts_count(self) -> int:
        """미처리 알림 수 조회"""
        try:
            count = await self.db.alerts.count_documents({"status": "unprocessed"})
            return count
        except Exception as e:
            print(f"미처리 알림 수 조회 실패: {e}")
            raise

    async def get_video_analysis_count(self, video_id: str) -> int:
        """특정 비디오의 분석 프레임 수 조회"""
        try:
            count = await self.db.video_analysis.count_documents({"video_id": video_id})
            return count
        except Exception as e:
            print(f"비디오 분석 프레임 수 조회 실패: {e}")
            return 0

    async def get_alerts_by_video_count(self, video_id: str) -> int:
        """특정 비디오에서 생성된 알림 수 조회"""
        try:
            count = await self.db.alerts.count_documents({"video_id": video_id})
            return count
        except Exception as e:
            print(f"비디오별 알림 수 조회 실패: {e}")
            return 0

    async def delete_video_data(self, video_id: str) -> bool:
        """특정 비디오와 관련된 모든 데이터 삭제"""
        try:
            # 비디오 분석 데이터 삭제
            await self.db.video_analysis.delete_many({"video_id": video_id})

            # 알림 데이터 삭제
            await self.db.alerts.delete_many({"video_id": video_id})

            # 규칙 실행 결과 삭제
            await self.db.rule_executions.delete_many({"video_id": video_id})

            return True
        except Exception as e:
            print(f"비디오 데이터 삭제 실패: {e}")
            return False

    async def is_alert_cooldown_active(self, video_id: str, rule_type: str, cooldown_seconds: int = 3) -> bool:
        """알림 쿨다운 상태 확인 (같은 동영상에 대해 3초 내 중복 알림 방지)"""
        try:
            # 같은 video_id와 rule_type으로 최근 생성된 알림 확인
            recent_alert = await self.db.alerts.find_one({
                'video_id': video_id,
                'rule_type': rule_type
            }, sort=[('created_at', -1)])  # 최신 알림부터 정렬

            if not recent_alert:
                return False  # 이전 알림이 없으면 쿨다운 없음

            # created_at 시간 확인
            created_at = recent_alert.get('created_at')
            if not created_at:
                return False

            # 현재 시간과 비교하여 쿨다운 상태 확인
            from datetime import datetime
            now = datetime.now()

            if isinstance(created_at, str):
                from datetime import datetime
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

            time_diff = (now - created_at).total_seconds()
            return time_diff < cooldown_seconds

        except Exception as e:
            print(f"쿨다운 체크 실패: {e}")
            return False  # 오류 시 쿨다운 비활성화

# 전역 데이터베이스 인스턴스
db = Database()

async def init_db():
    """데이터베이스 초기화 (외부에서 호출용)"""
    await db.init_db()
