# Seoul Trip Planner

서울 데이트/놀거리 코스를 자동으로 계획해주는 AI 에이전트입니다. 자연어로 요청하면 놀거리 → 식사 → 카페 → 술집 순서의 시간표가 포함된 코스를 생성합니다.

## 주요 기능

- **자연어 입력 분석**: "홍대에서 보드게임하고 한식 먹을래" → 의도 파악 및 장소 검색
- **Human-in-the-Loop (HIL)**: 취향(놀거리/음식)이 불분명하면 질문 후 반영
- **시간표 생성**: 시작 시간, 장소별 체류 시간, 이동 시간 포함
- **Kakao Map 연동**: 실제 위치 기반 주변 장소 검색

## 사전 요구사항

- Python 3.12+
- [Ollama](https://ollama.com/) + `llama3.2` 모델 (또는 OpenAI API)
- [Kakao Developers](https://developers.kakao.com/) REST API Key
- [Neon PostgreSQL](https://console.neon.tech/) 데이터베이스

## 설치

```bash
git clone <repository-url>
cd AItoy-date-planning

# uv로 의존성 설치
uv sync
source .venv/bin/activate
```

## 환경 변수

`.env` 파일 생성:

```env
KAKAO_REST_API_KEY=your_kakao_api_key
DATABASE_URL=postgresql://user:password@ep-xxx.neon.tech/trip_planner?sslmode=require

# 선택사항
OPENAI_API_KEY=your_openai_api_key
```

## 실행

```bash
# 1. Ollama 실행 (별도 터미널)
ollama serve

# 2. DB 마이그레이션
alembic upgrade head

# 3. 서버 실행
uvicorn src.server:app --reload --port 8000
```

## API

### POST /api/itinerary/plan

여행 계획 생성 요청

```json
{
  "user_input": "홍대에서 보드게임하고 한식 먹을래",
  "session_id": "user123",
  "time_settings": {
    "enabled": true,
    "start_time": "14:00",
    "duration_hours": 6
  }
}
```

**Response**: `status: "awaiting_user_input"` (HIL 필요시) 또는 `status: "completed"` (일정 완성)

### POST /api/itinerary/feedback

HIL 응답 제출

```json
{
  "workflow_id": "uuid-from-plan-response",
  "feedback": "한식"
}
```

## 아키텍처

```
사용자 입력 → analyze_user_input
                    ↓
         [조건부] request_activity_preference → discover_activity_places
                                                        ↓
                              [조건부] request_food_preference → discover_dining_places
                                                                        ↓
                                                    discover_cafe_places → discover_drinking_places
                                                                                    ↓
                                                                         generate_itinerary
                                                                                    ↓
                                                              request_refinement_feedback → [완료 or 재검색]
```

LangGraph 기반 워크플로우로 HIL 인터럽트 포인트에서 사용자 입력을 대기합니다.

## 프로젝트 구조

| 파일 | 역할 |
|------|------|
| `src/server.py` | FastAPI 엔드포인트 |
| `src/agent.py` | 에이전트 오케스트레이션 |
| `src/graph.py` | LangGraph 워크플로우 정의 |
| `src/nodes.py` | 각 노드 로직 (분석, 검색, 생성) |
| `src/state.py` | TripState 상태 정의 |
| `src/models.py` | Pydantic 모델 (Location, ScheduleItem, UserIntent 등) |
| `src/kakao_client.py` | Kakao Maps API 클라이언트 |
| `src/time_calculator.py` | 이동 시간 계산 및 스케줄 생성 |
| `src/database.py` | SQLAlchemy ORM 모델 |
| `src/db_logger.py` | 워크플로우/노드/LLM 호출 로깅 |

## 데이터베이스

4개 테이블: `users`, `workflows`, `nodes`, `generations`

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "Description"

# 마이그레이션 적용
alembic upgrade head
```

## 개발

```bash
# 테스트
pytest -v

# 포맷팅
black src/

# HIL 시나리오 테스트
python test_hil.py
```
