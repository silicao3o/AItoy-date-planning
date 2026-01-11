# 데이터베이스 통합 가이드

## 개요

이 프로젝트에 데이터베이스 로깅 시스템이 추가되었습니다. 사용자, 워크플로우, 노드 실행, LLM 생성 기록을 추적할 수 있습니다.

## 데이터베이스 스키마

### 1. User (사용자)
- `id`: 사용자 고유 ID
- `username`: 사용자명 (unique)
- `email`: 이메일 (optional)
- `created_at`, `updated_at`: 타임스탬프

### 2. Workflow (워크플로우 실행 기록)
- `id`: 워크플로우 고유 ID
- `user_id`: 사용자 ID (FK)
- `status`: running, completed, failed, cancelled
- `user_input`: 사용자 초기 입력
- `input_type`: region, specific_place
- `time_settings`: JSON (TimeSettings)
- `date_theme`: JSON (DateTheme)
- `user_intent`: JSON (UserIntent)
- `search_radius`: 검색 반경
- `final_itinerary`: JSON (List[ScheduleItem])
- `created_at`, `updated_at`, `completed_at`: 타임스탬프

### 3. Node (노드 실행 기록)
- `id`: 노드 고유 ID
- `workflow_id`: 워크플로우 ID (FK)
- `node_name`: 노드 이름 (예: analyze_user_input)
- `node_type`: analysis, search, generation, routing
- `execution_order`: 실행 순서
- `status`: pending, running, completed, failed, skipped
- `state_data`: JSON (노드 실행 후 전체 state)
- `input_data`: JSON (노드 입력)
- `output_data`: JSON (노드 출력)
- `error_message`, `error_traceback`: 에러 정보
- `started_at`, `completed_at`, `duration_ms`: 실행 시간 정보

### 4. Generation (LLM 생성 기록)
- `id`: 생성 기록 고유 ID
- `workflow_id`: 워크플로우 ID (FK)
- `node_id`: 노드 ID (FK, optional)
- `model_name`: 모델 이름 (예: llama3.2)
- `model_provider`: ollama, openai 등
- `system_prompt`: 시스템 프롬프트
- `user_prompt`: 사용자 프롬프트
- `output`: LLM 출력
- `parsed_output`: JSON (파싱된 결과)
- `temperature`, `max_tokens`: 생성 파라미터
- `prompt_tokens`, `completion_tokens`, `total_tokens`: 토큰 사용량
- `latency_ms`: 응답 시간
- `created_at`: 생성 시간

## 사용 방법

### 1. 데이터베이스 초기화

```python
from database import init_db

# SQLite 사용 (개발용)
engine = init_db("sqlite:///trip_planner.db")

# PostgreSQL 사용 (프로덕션)
# engine = init_db("postgresql://user:password@localhost/trip_planner")
```

### 2. DatabaseLogger 사용

```python
from db_logger import DatabaseLogger

# Logger 생성
logger = DatabaseLogger(engine)

# 사용자 생성/가져오기
user = logger.get_or_create_user(username="user123", email="user@example.com")

# 워크플로우 시작
workflow = logger.start_workflow(user.id, initial_state)

# 노드 실행 (컨텍스트 매니저 사용)
with logger.node_context("analyze_user_input", "analysis") as node:
    # 노드 로직 실행
    result = await analyze_input(state)
    
    # LLM 호출 기록
    logger.log_generation(
        model_name="llama3.2",
        user_prompt=prompt,
        output=llm_response,
        node_id=node.id
    )
    
    # 노드 완료 (자동으로 state 저장)
    logger.log_node_complete(node.id, state)

# 워크플로우 완료
logger.complete_workflow(state, status="completed")

# 세션 종료
logger.close()
```

### 3. 기존 워크플로우에 통합

`graph.py` 또는 `agent.py`에서 워크플로우 실행 시:

```python
from database import init_db
from db_logger import DatabaseLogger

class TripPlanningAgent:
    def __init__(self, ...):
        # 기존 초기화
        ...
        
        # DB 로거 추가
        self.db_engine = init_db()
        self.db_logger = None
    
    async def plan_trip(self, user_input: str, username: str = "anonymous"):
        # DB 로거 시작
        self.db_logger = DatabaseLogger(self.db_engine)
        
        try:
            # 사용자 생성/가져오기
            user = self.db_logger.get_or_create_user(username)
            
            # State 초기화
            state = self._initialize_state(user_input)
            
            # 워크플로우 시작
            workflow = self.db_logger.start_workflow(user.id, state)
            
            # 각 노드 실행 시 로깅
            # 예시: analyze_user_input 노드
            with self.db_logger.node_context("analyze_user_input", "analysis") as node:
                state = await self.nodes.analyze_user_input(state)
                self.db_logger.log_node_complete(node.id, state)
            
            # ... 다른 노드들도 동일하게
            
            # 워크플로우 완료
            self.db_logger.complete_workflow(state)
            
            return state
            
        except Exception as e:
            if self.db_logger:
                self.db_logger.fail_workflow(str(e))
            raise
        finally:
            if self.db_logger:
                self.db_logger.close()
```

### 4. LLM 호출 시 로깅

`nodes.py`의 각 노드에서 LLM을 호출할 때:

```python
async def analyze_user_input(self, state: TripState) -> TripState:
    # 프롬프트 준비
    system_prompt = "..."
    user_prompt = state['user_input']
    
    # LLM 호출 시간 측정
    start_time = datetime.utcnow()
    response = await self.llm.ainvoke(messages)
    latency = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    # 로깅 (db_logger가 있는 경우)
    if hasattr(self, 'db_logger') and self.db_logger:
        self.db_logger.log_generation(
            model_name="llama3.2",
            model_provider="ollama",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output=response.content,
            latency_ms=latency,
            temperature=0.7
        )
    
    # 기존 로직 계속...
```

## 데이터 조회

### 사용자 히스토리 조회

```python
# 최근 10개 워크플로우
history = logger.get_workflow_history(user_id, limit=10)

for workflow in history:
    print(f"[{workflow.status}] {workflow.user_input}")
    print(f"  Created: {workflow.created_at}")
    print(f"  Itinerary items: {len(workflow.final_itinerary or [])}")
```

### 워크플로우 상세 정보

```python
details = logger.get_workflow_details(workflow_id)

workflow = details['workflow']
nodes = details['nodes']
generations = details['generations']

print(f"Workflow: {workflow.user_input}")
print(f"Status: {workflow.status}")
print(f"\nNodes executed:")
for node in nodes:
    print(f"  - {node.node_name} ({node.status}) - {node.duration_ms}ms")

print(f"\nLLM Generations:")
for gen in generations:
    print(f"  - {gen.model_name}: {gen.latency_ms}ms")
```

### 직접 쿼리

```python
from database import get_session, User, Workflow, Node, Generation

session = get_session(engine)

# 특정 사용자의 모든 워크플로우
workflows = session.query(Workflow).filter_by(user_id=user_id).all()

# 실패한 워크플로우 찾기
failed = session.query(Workflow).filter_by(status='failed').all()

# 특정 노드의 평균 실행 시간
from sqlalchemy import func
avg_duration = session.query(func.avg(Node.duration_ms)).filter_by(
    node_name='analyze_user_input'
).scalar()

# LLM 사용량 통계
total_tokens = session.query(func.sum(Generation.total_tokens)).scalar()
```

## 마이그레이션

프로덕션 환경에서는 Alembic을 사용하여 스키마 변경을 관리하는 것을 권장합니다:

```bash
# Alembic 설치
pip install alembic

# 초기화
alembic init alembic

# 마이그레이션 생성
alembic revision --autogenerate -m "Initial schema"

# 마이그레이션 적용
alembic upgrade head
```

## 성능 최적화

1. **인덱스**: 자주 쿼리하는 컬럼에 인덱스가 설정되어 있습니다 (user_id, workflow_id 등)

2. **배치 커밋**: 여러 노드를 실행할 때 각 노드마다 커밋하지 않고 워크플로우 완료 시 한 번에 커밋

3. **비동기 로깅**: 성능이 중요한 경우 별도 스레드나 큐를 사용하여 비동기로 로깅

4. **데이터 정리**: 오래된 워크플로우 데이터를 주기적으로 아카이브

## 예시 실행

```bash
# 예시 코드 실행
python src/example_db_usage.py

# 데이터베이스 확인 (SQLite)
sqlite3 trip_planner.db
> SELECT * FROM users;
> SELECT * FROM workflows ORDER BY created_at DESC LIMIT 5;
> SELECT * FROM nodes WHERE workflow_id = 1;
> SELECT * FROM generations WHERE workflow_id = 1;
```

## 다음 단계

1. **웹 대시보드**: 워크플로우 히스토리와 통계를 시각화하는 대시보드 구축
2. **분석**: 노드 성능, LLM 사용량, 사용자 패턴 분석
3. **A/B 테스트**: 다른 프롬프트나 모델의 성능 비교
4. **재실행**: 과거 워크플로우를 재실행하거나 디버깅
