import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime

class SSEBroker:
    def __init__(self):
        self._queues: List[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def connect(self) -> asyncio.Queue:
        """새로운 SSE 연결 생성"""
        queue = asyncio.Queue()
        async with self._lock:
            self._queues.append(queue)
        return queue

    async def disconnect(self, queue: asyncio.Queue):
        """SSE 연결 해제"""
        async with self._lock:
            if queue in self._queues:
                self._queues.remove(queue)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """모든 연결된 클라이언트에게 이벤트 브로드캐스트"""
        message = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        # 비활성 연결 제거
        active_queues = []
        async with self._lock:
            for queue in self._queues:
                if not queue.full():
                    active_queues.append(queue)
                else:
                    # 큐가 가득 찬 경우 제거 (로깅 추가)
                    print(f"큐가 가득 참 - 연결 제거: {queue}")
            self._queues = active_queues

        # 활성 연결에 메시지 전송
        for queue in active_queues:
            try:
                await queue.put(message)
            except Exception as e:
                print(f"메시지 전송 실패: {e}")
                # 실패한 큐는 다음에 제거
                continue

    async def send_alert(self, alert_data: Dict[str, Any]):
        """알림 데이터를 모든 클라이언트에게 전송"""
        await self.broadcast("alert", alert_data)

    async def send_rule_update(self, rule_data: Dict[str, Any]):
        """규칙 업데이트를 모든 클라이언트에게 전송"""
        await self.broadcast("rule_update", rule_data)

    async def send_config_update(self, config_data: Dict[str, Any]):
        """설정 업데이트를 모든 클라이언트에게 전송"""
        await self.broadcast("config_update", config_data)

    def get_connection_count(self) -> int:
        """현재 연결된 클라이언트 수 반환"""
        return len(self._queues)

# 전역 브로커 인스턴스
broker = SSEBroker()
