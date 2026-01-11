# 🤖 AI Date Planner Agent

AI 기반으로 서울의 핫플레이스 데이트/놀거리 코스를 자동으로 계획해주는 에이전트입니다.
사용자의 의도를 파악하고(지역 vs 특정 장소), 부족한 정보는 질문(HIL)을 통해 보완하며 최적의 코스를 제안합니다.

## ✨ 주요 기능

- **자연어 입력 분석**: "홍대" 같은 지역명과 "롯데월드" 같은 특정 장소를 구분하여 처리합니다.
- **Human-In-The-Loop (HIL)**:
  - **놀거리 취향**: 전시, 이색체험, 힐링 등 선호하는 놀거리 스타일을 물어봅니다.
  - **음식 취향**: 양식, 한식, 일식 등 선호하는 음식 종류를 물어보고 반영합니다.
  - **장소 확인**: 입력한 장소가 모호할 경우 다시 확인합니다.
- **동선 기반 코스 추천**: 놀거리 -> 식사 -> 카페 -> 술집 순서의 자연스러운 코스를 생성합니다.
- **Kakao Map 연동**: 실제 위치 기반으로 주변 장소를 검색합니다.
- **📊 데이터베이스 로깅**: 
  - **사용자 추적**: 각 사용자의 워크플로우 히스토리 저장
  - **노드 실행 기록**: 각 노드의 실행 시간, 상태, state 변경 추적
  - **LLM 생성 기록**: 프롬프트, 출력, 모델 정보, 토큰 사용량 기록
  - **성능 분석**: 노드별 평균 실행 시간, LLM 응답 시간 등 메트릭 수집

## 🛠️ 사전 요구사항

- **Python 3.12+**
- **LLM (택 1)**:
  - **[Ollama](https://ollama.com/)** (로컬 실행): `llama3.2` 모델 설치 필요 (`ollama pull llama3.2`)
  - **OpenAI API** (클라우드 실행): `OPENAI_API_KEY` 발급 필요. `agent.py`에서 모델 변경 가능.
- **Kakao Developers API Key**: 로컬 검색 API 사용을 위해 필요합니다.
- **Neon PostgreSQL**: 데이터베이스 (무료 플랜 사용 가능)
  - [Neon Console](https://console.neon.tech/)에서 계정 생성 및 데이터베이스 설정

## 🚀 설치 및 실행 방법 (uv 사용)

이 프로젝트는 [uv](https://github.com/astral-sh/uv)를 사용하여 패키지를 관리합니다.

### 1. 프로젝트 클론 및 이동
```bash
git clone <repository-url>
cd AItoy-date-planning
```

### 2. 가상환경 생성 및 의존성 설치
```bash
# 의존성 동기화 (가상환경 자동 생성 및 패키지 설치)
uv sync

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate
```

**참고 (수동 설치 시):**
```bash
uv pip install -e .
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 다음 정보를 입력하세요.
```env
KAKAO_REST_API_KEY=your_kakao_api_key_here

# Database - Neon PostgreSQL (필수)
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/trip_planner?sslmode=require

# OpenAI 사용 시 (선택)
OPENAI_API_KEY=your_openai_api_key_here
# 사용할 모델 변경은 src/agent.py에서 가능합니다.

# LangSmith 추적 (선택)
# LANGCHAIN_API_KEY=... 
# LANGCHAIN_TRACING_V2=true
```

**Neon PostgreSQL 연결 문자열 얻기:**
1. [Neon Console](https://console.neon.tech/)에 로그인
2. 프로젝트 선택 또는 생성
3. "Connection Details" 섹션에서 연결 문자열 복사
4. `.env` 파일의 `DATABASE_URL`에 붙여넣기

### 4. 데이터베이스 초기화
```bash
# 초기 마이그레이션 생성 및 적용
./init_migration.sh

# 또는 수동으로:
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### 5. Ollama 실행
터미널에서 Ollama 서버가 실행 중이어야 합니다.
```bash
ollama serve
# 별도 터미널에서 모델 확인
ollama list
```

### 6. 서버 실행
FastAPI 서버를 실행합니다.
```bash
uvicorn src.server:app --reload --port 8000
```

## 🧪 테스트 방법

### API 엔드포인트
- `POST /api/plan`: 여행 계획 요청 시작
- `POST /api/feedback`: 사용자 피드백(취향) 전달

### 테스트 스크립트 실행
HIL 시나리오를 테스트하려면 별도의 터미널에서 다음 스크립트를 실행하세요.

```bash
# 기본 HIL 흐름 (지역 검색 -> 놀거리 취향 -> 음식 취향 -> 결과)
python test_hil.py

# 장소 불명확 시나리오 (잘못된 장소 -> 재확인 -> 진행)
python test_hil_place.py
```

## 📂 프로젝트 구조
```
.
├── src/
│   ├── agent.py           # 에이전트 오케스트레이션 및 초기화
│   ├── graph.py           # LangGraph 워크플로우 구성 (Graph, Edges)
│   ├── nodes.py           # 워크플로우(Graph)의 각 노드 로직
│   ├── state.py           # 에이전트 상태 정의 (TripState)
│   ├── models.py          # 데이터 모델 (Pydantic: Location, ScheduleItem 등)
│   ├── kakao_client.py    # 카카오맵 API 클라이언트
│   ├── time_calculator.py # 시간/거리 계산 유틸리티
│   ├── database.py        # 데이터베이스 스키마 정의 (SQLAlchemy ORM)
│   ├── db_logger.py       # 워크플로우 실행 로깅 헬퍼
│   ├── example_db_usage.py # 데이터베이스 사용 예시
│   ├── server.py          # FastAPI 서버 진입점
│   └── main.py            # (Optional) CLI 실행용
├── test_hil.py            # HIL 테스트 스크립트
├── DATABASE_GUIDE.md      # 데이터베이스 통합 가이드
├── DATABASE_SCHEMA.md     # 데이터베이스 스키마 다이어그램
├── .env                   # 환경 변수 설정
└── pyproject.toml         # 프로젝트 설정
```

## 📊 데이터베이스 사용법

### 데이터베이스 초기화 및 예시 실행
```bash
# 데이터베이스 사용 예시 실행 (자동으로 DB 생성)
uv run python src/example_db_usage.py

# 생성된 데이터베이스 확인
sqlite3 trip_planner.db
> SELECT * FROM users;
> SELECT * FROM workflows ORDER BY created_at DESC LIMIT 5;
```

### 주요 테이블
- **users**: 사용자 정보
- **workflows**: 워크플로우 실행 기록 (user_input, settings, final_itinerary 등)
- **nodes**: 각 노드 실행 기록 (실행 시간, state 변경, 에러 등)
- **generations**: LLM 생성 기록 (프롬프트, 출력, 모델, 토큰 사용량 등)

자세한 내용은 [DATABASE_GUIDE.md](DATABASE_GUIDE.md)와 [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)를 참조하세요.

