# Neon PostgreSQL + Alembic 마이그레이션 통합 완료

## 🎉 완료 사항

SQLite에서 **Neon PostgreSQL**로 전환하고 **Alembic**을 사용한 데이터베이스 버전 관리 시스템을 구축했습니다.

## 📦 추가된 패키지

```toml
dependencies = [
    # ... 기존 패키지들
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",  # PostgreSQL 드라이버
    "alembic>=1.13.0",         # 마이그레이션 도구
]
```

## 📁 생성된 파일 및 디렉토리

### 1. Alembic 설정
```
alembic/
├── versions/           # 마이그레이션 파일들이 저장될 디렉토리
├── env.py             # Alembic 환경 설정 (수정됨)
├── script.py.mako     # 마이그레이션 템플릿
└── README

alembic.ini            # Alembic 설정 파일 (수정됨)
```

### 2. 문서
- **ALEMBIC_GUIDE.md** - Alembic 사용 가이드
- **.env.example** - 환경 변수 예시 (DATABASE_URL 포함)
- **init_migration.sh** - 초기 마이그레이션 자동화 스크립트

### 3. 수정된 파일
- **src/database.py** - PostgreSQL 연결 및 환경 변수 지원
- **alembic/env.py** - 프로젝트 모델 자동 인식
- **alembic.ini** - 환경 변수 기반 설정
- **README.md** - Neon PostgreSQL 설정 가이드 추가

## 🔧 주요 변경사항

### 1. database.py 개선

**이전 (SQLite):**
```python
def init_db(db_url: str = "sqlite:///trip_planner.db"):
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return engine
```

**현재 (PostgreSQL + 환경 변수):**
```python
def init_db(db_url: Optional[str] = None):
    """데이터베이스 초기화
    
    Args:
        db_url: 데이터베이스 URL. None이면 환경 변수 DATABASE_URL 사용
    """
    if db_url is None:
        load_dotenv()
        db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            raise ValueError("DATABASE_URL not set")
    
    # PostgreSQL 연결 풀 설정 (Neon 최적화)
    engine = create_engine(
        db_url,
        echo=False,
        pool_pre_ping=True,  # 연결 유효성 검사
        pool_size=5,
        max_overflow=10
    )
    
    Base.metadata.create_all(engine)
    return engine
```

### 2. Alembic env.py 설정

```python
# 프로젝트 모델 자동 인식
from src.database import Base
target_metadata = Base.metadata

# 환경 변수에서 DATABASE_URL 읽기
def get_url():
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL not set")
    return url
```

## 🚀 사용 방법

### 1. Neon PostgreSQL 설정

1. [Neon Console](https://console.neon.tech/) 접속
2. 새 프로젝트 생성
3. 데이터베이스 생성 (예: `trip_planner`)
4. 연결 문자열 복사

### 2. 환경 변수 설정

`.env` 파일에 추가:

```env
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.region.aws.neon.tech/trip_planner?sslmode=require
```

### 3. 초기 마이그레이션 (자동)

```bash
# 스크립트 실행 (권장)
./init_migration.sh
```

이 스크립트는 자동으로:
- ✅ 환경 변수 확인
- ✅ 마이그레이션 파일 생성
- ✅ 데이터베이스에 적용
- ✅ 현재 상태 확인

### 4. 초기 마이그레이션 (수동)

```bash
# 1. 마이그레이션 생성
alembic revision --autogenerate -m "Initial schema"

# 2. 마이그레이션 적용
alembic upgrade head

# 3. 상태 확인
alembic current
```

## 📊 마이그레이션 워크플로우

### 모델 변경 시

1. **모델 수정** (예: `src/database.py`)
```python
class User(Base):
    # ... 기존 필드
    phone = Column(String(20), nullable=True)  # 새 필드 추가
```

2. **마이그레이션 생성**
```bash
alembic revision --autogenerate -m "Add phone to User"
```

3. **마이그레이션 파일 확인**
```bash
# alembic/versions/xxx_add_phone_to_user.py 확인
# 필요시 수동 수정
```

4. **마이그레이션 적용**
```bash
alembic upgrade head
```

### 마이그레이션 되돌리기

```bash
# 한 단계 되돌리기
alembic downgrade -1

# 특정 버전으로
alembic downgrade <revision_id>

# 모두 되돌리기
alembic downgrade base
```

## 🔍 유용한 명령어

```bash
# 현재 버전 확인
alembic current

# 마이그레이션 히스토리
alembic history

# 다음 적용될 마이그레이션 확인
alembic show head

# 특정 버전으로 업그레이드
alembic upgrade <revision_id>

# SQL 미리보기 (실제 적용 안 함)
alembic upgrade head --sql
```

## 🌟 Neon PostgreSQL 장점

### 1. 서버리스 아키텍처
- 자동 스케일링
- 사용한 만큼만 과금
- 무료 플랜 제공

### 2. 개발자 친화적
- 빠른 브랜치 생성 (Git처럼)
- 자동 백업
- 웹 기반 SQL 에디터

### 3. 성능
- 빠른 콜드 스타트
- 자동 연결 풀링
- SSD 스토리지

### 4. 보안
- SSL/TLS 암호화
- IP 화이트리스트
- 역할 기반 접근 제어

## 📈 마이그레이션 모범 사례

### 1. 항상 백업
```bash
# Neon은 자동 백업을 제공하지만, 중요한 변경 전에는 수동 스냅샷 생성
# Neon Console > Restore 탭에서 확인
```

### 2. 테스트 환경에서 먼저 테스트
```bash
# 로컬 또는 스테이징 환경에서 먼저 테스트
DATABASE_URL=postgresql://localhost:5432/trip_planner_test alembic upgrade head
```

### 3. 마이그레이션 파일 검토
```bash
# 자동 생성된 마이그레이션 파일을 항상 검토
# alembic/versions/xxx_*.py 파일 확인
```

### 4. 점진적 변경
```bash
# 큰 변경은 여러 작은 마이그레이션으로 나누기
alembic revision -m "Step 1: Add new column"
alembic revision -m "Step 2: Migrate data"
alembic revision -m "Step 3: Remove old column"
```

## 🔧 문제 해결

### DATABASE_URL 오류
```
ValueError: DATABASE_URL environment variable is not set
```

**해결:**
- `.env` 파일이 프로젝트 루트에 있는지 확인
- `DATABASE_URL`이 올바르게 설정되었는지 확인

### 연결 오류
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**해결:**
- Neon 대시보드에서 데이터베이스가 활성 상태인지 확인
- 연결 문자열에 `?sslmode=require` 포함 확인
- 네트워크 연결 확인

### 마이그레이션 충돌
```
alembic.util.exc.CommandError: Multiple head revisions
```

**해결:**
```bash
alembic merge heads -m "Merge conflicting migrations"
alembic upgrade head
```

## 📚 참고 문서

- **ALEMBIC_GUIDE.md** - 상세한 Alembic 사용 가이드
- **DATABASE_GUIDE.md** - 데이터베이스 통합 가이드
- **DATABASE_SCHEMA.md** - 스키마 다이어그램
- **.env.example** - 환경 변수 예시

## ✅ 체크리스트

설정이 완료되었는지 확인:

- [ ] Neon PostgreSQL 계정 생성
- [ ] 데이터베이스 생성
- [ ] `.env` 파일에 `DATABASE_URL` 설정
- [ ] `uv sync`로 의존성 설치
- [ ] `./init_migration.sh` 실행 또는 수동 마이그레이션
- [ ] `alembic current`로 상태 확인
- [ ] 애플리케이션 실행 테스트

## 🎯 다음 단계

1. **프로덕션 배포**
   - Neon 프로덕션 브랜치 생성
   - 환경별 DATABASE_URL 설정
   - CI/CD 파이프라인에 마이그레이션 통합

2. **모니터링**
   - Neon 대시보드에서 쿼리 성능 모니터링
   - 연결 풀 사용량 확인
   - 스토리지 사용량 추적

3. **최적화**
   - 인덱스 추가
   - 쿼리 최적화
   - 연결 풀 튜닝

---

**구현 완료일**: 2026-01-11  
**데이터베이스**: Neon PostgreSQL  
**마이그레이션 도구**: Alembic 1.13+  
**상태**: ✅ 완료 및 문서화 완료
