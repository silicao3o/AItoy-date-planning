# 데이터베이스 스키마 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE SCHEMA                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│       User           │
├──────────────────────┤
│ id (PK)              │
│ username (UNIQUE)    │
│ email (UNIQUE)       │
│ created_at           │
│ updated_at           │
└──────────────────────┘
         │
         │ 1:N
         │
         ▼
┌──────────────────────┐
│     Workflow         │
├──────────────────────┤
│ id (PK)              │
│ user_id (FK)         │────────────────────────┐
│ name                 │                        │
│ status               │                        │
│ user_input           │                        │
│ input_type           │                        │
│ time_settings (JSON) │                        │
│ date_theme (JSON)    │                        │
│ user_intent (JSON)   │                        │
│ search_radius        │                        │
│ final_itinerary (JSON)│                       │
│ created_at           │                        │
│ updated_at           │                        │
│ completed_at         │                        │
└──────────────────────┘                        │
         │                                      │
         │ 1:N                                  │ 1:N
         │                                      │
         ▼                                      ▼
┌──────────────────────┐              ┌──────────────────────┐
│       Node           │              │    Generation        │
├──────────────────────┤              ├──────────────────────┤
│ id (PK)              │              │ id (PK)              │
│ workflow_id (FK)     │              │ workflow_id (FK)     │
│ node_name            │◄─────────────│ node_id (FK)         │
│ node_type            │     N:1      │ model_name           │
│ execution_order      │              │ model_provider       │
│ status               │              │ system_prompt        │
│ state_data (JSON)    │              │ user_prompt          │
│ input_data (JSON)    │              │ output               │
│ output_data (JSON)   │              │ parsed_output (JSON) │
│ error_message        │              │ temperature          │
│ error_traceback      │              │ max_tokens           │
│ started_at           │              │ prompt_tokens        │
│ completed_at         │              │ completion_tokens    │
│ duration_ms          │              │ total_tokens         │
└──────────────────────┘              │ latency_ms           │
                                      │ error_message        │
                                      │ created_at           │
                                      └──────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           KEY RELATIONSHIPS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User → Workflow (1:N)                                                       │
│    - 한 사용자는 여러 워크플로우를 실행할 수 있음                                    │
│                                                                              │
│  Workflow → Node (1:N)                                                       │
│    - 하나의 워크플로우는 여러 노드를 실행함                                          │
│    - execution_order로 실행 순서 추적                                           │
│                                                                              │
│  Workflow → Generation (1:N)                                                 │
│    - 하나의 워크플로우에서 여러 LLM 생성이 발생할 수 있음                              │
│                                                                              │
│  Node → Generation (1:N, optional)                                           │
│    - 각 LLM 생성은 특정 노드에서 발생 (선택적)                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          STATE DATA STRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Node.state_data (JSON) - 각 노드 실행 후의 TripState:                          │
│  {                                                                           │
│    "user_input": "홍대에서 데이트하고 싶어",                                        │
│    "parsed_location": "홍대",                                                 │
│    "user_intent": {                                                          │
│      "location": "홍대",                                                      │
│      "activity_required": true,                                              │
│      "activity_preference": "전시",                                           │
│      "activity_keywords": ["문화", "예술"],                                    │
│      ...                                                                     │
│    },                                                                        │
│    "activity_places": [                                                      │
│      {                                                                       │
│        "name": "홍대 미술관",                                                  │
│        "category": "문화시설",                                                 │
│        "address": "서울 마포구 홍익로",                                          │
│        "x": 126.9222,                                                        │
│        "y": 37.5511,                                                         │
│        ...                                                                   │
│      }                                                                       │
│    ],                                                                        │
│    "dining_places": [...],                                                   │
│    "cafe_places": [...],                                                     │
│    "drinking_places": [...],                                                 │
│    "final_itinerary": [...],                                                 │
│    "progress_messages": [...]                                                │
│  }                                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              STATUS VALUES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Workflow.status:                                                            │
│    - running: 실행 중                                                         │
│    - completed: 정상 완료                                                     │
│    - failed: 실패                                                            │
│    - cancelled: 사용자가 취소                                                  │
│                                                                              │
│  Node.status:                                                                │
│    - pending: 대기 중                                                         │
│    - running: 실행 중                                                         │
│    - completed: 정상 완료                                                     │
│    - failed: 실패                                                            │
│    - skipped: 건너뜀 (조건부 실행)                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              INDEXES                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User:                                                                       │
│    - username (UNIQUE)                                                       │
│    - email (UNIQUE)                                                          │
│                                                                              │
│  Workflow:                                                                   │
│    - user_id (FK, indexed)                                                   │
│                                                                              │
│  Node:                                                                       │
│    - workflow_id (FK, indexed)                                               │
│                                                                              │
│  Generation:                                                                 │
│    - workflow_id (FK, indexed)                                               │
│    - node_id (FK, indexed)                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 주요 특징

### 1. **User 테이블**
- 사용자 정보 저장
- username과 email은 unique constraint
- 여러 워크플로우 실행 기록 추적

### 2. **Workflow 테이블**
- 워크플로우 실행의 전체 컨텍스트 저장
- JSON 필드로 복잡한 설정 저장 (time_settings, date_theme, user_intent)
- 최종 결과(final_itinerary)도 JSON으로 저장
- status로 실행 상태 추적

### 3. **Node 테이블**
- 각 노드의 실행 기록
- execution_order로 실행 순서 보장
- state_data에 노드 실행 후의 전체 state 저장
- 성능 메트릭 (duration_ms)
- 에러 추적 (error_message, error_traceback)

### 4. **Generation 테이블**
- LLM 호출 기록
- 프롬프트와 출력 모두 저장
- 모델 정보 (model_name, model_provider)
- 성능 메트릭 (latency_ms, token counts)
- 어떤 노드에서 생성되었는지 추적 (node_id)

## 데이터 흐름

```
1. User 생성/조회
   ↓
2. Workflow 시작 (initial state 저장)
   ↓
3. Node 실행 시작
   ↓
4. LLM 호출 (Generation 기록)
   ↓
5. Node 완료 (state_data 업데이트)
   ↓
6. 다음 Node로 (3-5 반복)
   ↓
7. Workflow 완료 (final_itinerary 저장)
```

## 쿼리 예시

```sql
-- 사용자별 워크플로우 성공률
SELECT 
    u.username,
    COUNT(*) as total_workflows,
    SUM(CASE WHEN w.status = 'completed' THEN 1 ELSE 0 END) as completed,
    ROUND(100.0 * SUM(CASE WHEN w.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM users u
JOIN workflows w ON u.id = w.user_id
GROUP BY u.id;

-- 노드별 평균 실행 시간
SELECT 
    node_name,
    node_type,
    COUNT(*) as executions,
    AVG(duration_ms) as avg_duration_ms,
    MIN(duration_ms) as min_duration_ms,
    MAX(duration_ms) as max_duration_ms
FROM nodes
WHERE status = 'completed'
GROUP BY node_name, node_type
ORDER BY avg_duration_ms DESC;

-- LLM 모델별 사용 통계
SELECT 
    model_name,
    COUNT(*) as total_calls,
    AVG(latency_ms) as avg_latency_ms,
    SUM(total_tokens) as total_tokens_used
FROM generations
GROUP BY model_name;

-- 특정 워크플로우의 전체 실행 과정
SELECT 
    n.execution_order,
    n.node_name,
    n.status,
    n.duration_ms,
    g.model_name,
    g.latency_ms
FROM nodes n
LEFT JOIN generations g ON n.id = g.node_id
WHERE n.workflow_id = 1
ORDER BY n.execution_order;
```
