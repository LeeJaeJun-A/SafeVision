# Smart Safety - FastAPI + YOLO + SSE
동영상 분석 기반 안전 모니터링 시스템입니다. YOLO 객체 감지, 규칙 엔진, 실시간 알림을 통해 공사 현장이나 위험 구역의 안전을 모니터링합니다.

## 주요 기능

### 비디오 분석
- **동영상 업로드**: MP4, MOV, AVI, MKV 등 다양한 형식 지원
- **YOLO 객체 감지**: 80+ 클래스 지원 (사람, 차량, 건설장비, 동물, 물체 등)
- **프레임 샘플링**: 설정 가능한 FPS로 효율적인 분석
- **동적 규칙 적용**: 분석 시마다 최신 규칙 자동 적용

### 안전 규칙 엔진
- **거리 위반**: 두 객체 간 안전 거리 미준수 감지
- **위험 구역 진입**: 지정된 구역 침입 감지 (구역 정보 포함)
- **과속 감지**: 차량/장비의 속도 위반 감지 (구역 제한 옵션)
- **밀집도 위반**: 특정 구역의 과밀 집중 감지
- **안전선 침범**: 지정된 선을 건넌 경우 감지
- **접근 추세**: 지속적인 접근 패턴 감지
- **충돌 위험**: 사람과 다른 객체 간의 충돌 위험 감지 (거리 + 속도 + 방향)
- **낙상 감지**: 사람의 급격한 Y좌표 변화로 낙상 감지 (프레임 범위 필터링)

### 실시간 알림
- **SSE 스트리밍**: Server-Sent Events를 통한 실시간 알림
- **데이터베이스 저장**: MongoDB에 알림 히스토리 저장
- **알림 쿨다운**: 동영상별 3초 쿨다운 (낙상 감지 제외)
- **상태 관리**: unprocessed, processing, completed 상태 관리
- **비디오 클립**: 규칙별 맞춤 영상 길이 (낙상: 전 1.5초, 후 3.5초)

### 설정 관리
- **JSON 기반 규칙**: 개별 파일로 저장되는 동적 규칙 시스템
- **동적 규칙 로딩**: 분석 시마다 규칙 새로고침으로 실시간 반영
- **전역 설정**: 픽셀당 미터 비율, FPS, 쿨다운 등
- **위험 구역/안전선**: 폴리곤과 라인 기반 구역 정의

## 시스템 아키텍처

```
smart_safety/
├─ app/                    # FastAPI 애플리케이션
│  ├─ main.py             # 메인 앱 및 라우터 등록
│  └─ api/                # API 엔드포인트
│     ├─ uploads.py       # 비디오 업로드 API
│     ├─ alerts.py        # 알림 관리 API (SSE 포함)
│     └─ rules.py         # 규칙 관리 API
├─ core/                   # 핵심 모듈
│  ├─ config.py           # 설정 관리
│  ├─ broker.py           # SSE 브로커 (연결 관리, 메시지 브로드캐스트)
│  ├─ db.py               # 데이터베이스 관리 (MongoDB)
│  └─ video_utils.py      # 비디오 유틸리티
├─ vision/                 # 컴퓨터 비전
│  ├─ detector.py         # YOLO 객체 감지
│  └─ worker.py           # 비디오 처리 워커
├─ rules/                  # 규칙 엔진
│  ├─ engine.py           # 규칙 실행 엔진 (알림 생성, 비디오 클립)
│  ├─ builtins.py         # 내장 규칙 구현 (충돌 위험, 낙상 감지)
│  └─ schemas.py          # Pydantic 스키마 (RuleType, AlertStatus)
├─ storage/                # 저장소
│  ├─ uploads/            # 업로드된 비디오
│  ├─ rules/              # 규칙 JSON 파일들
│  ├─ config.json         # 전역 설정
│  └─ alert_clips/        # 알림 비디오 클립 저장소
├─ deploy_aws.sh          # AWS EC2 배포 스크립트
└─ requirements.txt        # Python 의존성
```

## 설치 및 실행

### 1. MongoDB 설정
```bash
# MongoDB 설치 (macOS)
brew install mongodb-community

# MongoDB 서비스 시작
brew services start mongodb-community

# 또는 Docker로 실행
docker run -d -p 27017:27017 --name mongodb mongo:latest

# MongoDB 연결 확인
mongosh mongodb://localhost:27017
```

### 2. 의존성 설정
```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. 서버 실행
```bash
# 방법 1: 실행 스크립트 사용
chmod +x run.sh
./run.sh

# 방법 2: 직접 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 접속
- **API 문서**: http://localhost:8000/docs
- **메인 페이지**: http://localhost:8000/
- **상태 확인**: http://localhost:8000/health

## API 엔드포인트

### 비디오 업로드
- `POST /api/v1/uploads` - 비디오 파일 업로드 및 분석

### 알림 관리
- `GET /api/v1/alerts` - 알림 목록 조회
- `GET /api/v1/alerts/{alert_id}` - 특정 알림 조회
- `PATCH /api/v1/alerts/{alert_id}/status` - 알림 상태 업데이트
- `GET /api/v1/alerts/unprocessed/count` - 미처리 알림 수 조회
- `GET /api/v1/alerts/sse/alerts` - SSE 실시간 알림 스트리밍
- `GET /api/v1/alerts/sse/status` - SSE 연결 상태 확인

### 규칙 관리
- `GET /api/v1/rules` - 모든 규칙 목록 조회
- `GET /api/v1/rules/enabled` - 활성화된 규칙만 조회
- `GET /api/v1/rules/{rule_id}` - 특정 규칙 조회
- `POST /api/v1/rules` - 새 규칙 생성
- `PUT /api/v1/rules/{rule_id}` - 규칙 수정
- `DELETE /api/v1/rules/{rule_id}` - 규칙 삭제
- `GET /api/v1/rules/types` - 사용 가능한 규칙 타입 목록

### 설정 관리
- `GET /api/v1/config` - 전역 설정 조회
- `PUT /api/v1/config` - 전역 설정 업데이트

## 규칙 타입

### 기본 안전 규칙
- **`distance_below`** - 거리 위반
- **`zone_entry`** - 위험 구역 진입
- **`speed_over`** - 과속
- **`crowd_in_zone`** - 밀집도 위반
- **`line_cross`** - 안전선 침범
- **`approaching`** - 접근 추세

### 고급 안전 규칙
- **`collision_risk`** - 충돌 위험 (거리 + 속도 + 방향)
- **`fall_detection`** - 낙상 감지 (Y좌표 변화 + 프레임 범위)

## 알림 상태

- **`unprocessed`** - 미처리
- **`processing`** - 처리중
- **`completed`** - 처리완료

##  문제 해결
### 일반적인 문제들
1. **MongoDB 연결 실패**: MongoDB 서비스 상태 확인
2. **YOLO 모델 로딩 실패**: `yolov8n.pt` 파일 존재 확인
3. **SSE 연결 실패**: 방화벽 및 포트 설정 확인
4. **비디오 업로드 실패**: 파일 형식 및 크기 제한 확인

### 로그 확인
```bash
# 서비스 로그
sudo journalctl -u smart-safety -f

# Nginx 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 개발 가이드

### 새로운 규칙 추가
1. `rules/schemas.py`에 RuleType 추가
2. `rules/builtins.py`에 규칙 클래스 구현
3. `app/api/rules.py`에 API 엔드포인트 추가

### SSE 이벤트 추가
1. `core/broker.py`에 새로운 이벤트 타입 추가
2. `app/api/alerts.py`에 SSE 이벤트 처리 로직 추가