# Alembic 마이그레이션 가이드

## 개요

이 프로젝트는 Alembic을 사용하여 데이터베이스 스키마 버전 관리를 수행합니다.
Neon PostgreSQL을 기본 데이터베이스로 사용합니다.

## 사전 준비

### 1. Neon PostgreSQL 설정

1. [Neon Console](https://console.neon.tech/)에 로그인
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 데이터베이스 생성 (예: `trip_planner`)
4. 연결 문자열 복사

### 2. 환경 변수 설정

`.env` 파일에 DATABASE_URL 추가:

```env
DATABASE_URL=postgresql://[user]:[password]@[endpoint]/[database]?sslmode=require
```

**예시:**
```env
DATABASE_URL=postgresql://myuser:mypassword@ep-cool-darkness-123456.us-east-2.aws.neon.tech/trip_planner?sslmode=require
```

## Alembic 사용법

### 초기 마이그레이션 생성

프로젝트를 처음 설정할 때 또는 모델을 변경했을 때:

```bash
# 현재 모델을 기반으로 마이그레이션 파일 자동 생성
alembic revision --autogenerate -m "Initial migration"
```

이 명령은 `alembic/versions/` 디렉토리에 새 마이그레이션 파일을 생성합니다.

### 마이그레이션 적용

```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade <revision_id>

# 한 단계 업그레이드
alembic upgrade +1
```

### 마이그레이션 되돌리기

```bash
# 한 단계 다운그레이드
alembic downgrade -1

# 특정 버전으로 다운그레이드
alembic downgrade <revision_id>

# 모든 마이그레이션 되돌리기
alembic downgrade base
```

### 현재 상태 확인

```bash
# 현재 데이터베이스 버전 확인
alembic current

# 마이그레이션 히스토리 확인
alembic history

# 적용 대기 중인 마이그레이션 확인
alembic show head
```

## 워크플로우 예시

### 1. 새 프로젝트 설정

```bash
# 1. 의존성 설치
uv sync

# 2. .env 파일 설정 (DATABASE_URL 추가)
cp .env.example .env
# .env 파일을 편집하여 실제 Neon 연결 문자열 입력

# 3. 초기 마이그레이션 생성
alembic revision --autogenerate -m "Initial schema"

# 4. 마이그레이션 적용
alembic upgrade head

# 5. 확인
alembic current
```

### 2. 모델 변경 시

예를 들어, `User` 테이블에 `phone` 필드를 추가했다면:

```python
# src/database.py
class User(Base):
    # ... 기존 필드들
    phone = Column(String(20), nullable=True)  # 새 필드 추가
```

마이그레이션 생성 및 적용:

```bash
# 1. 변경사항 기반 마이그레이션 생성
alembic revision --autogenerate -m "Add phone field to User"

# 2. 생성된 마이그레이션 파일 확인 (alembic/versions/xxx_add_phone_field_to_user.py)
# 필요시 수동으로 수정

# 3. 마이그레이션 적용
alembic upgrade head
```

### 3. 프로덕션 배포

```bash
# 1. 코드 배포 전에 마이그레이션 먼저 적용
alembic upgrade head

# 2. 애플리케이션 재시작
```

## 마이그레이션 파일 구조

```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_phone_to_user.py
│   └── 003_add_indexes.py
├── env.py          # Alembic 환경 설정
├── script.py.mako  # 마이그레이션 템플릿
└── README          # Alembic 기본 README

alembic.ini         # Alembic 설정 파일
```

## 수동 마이그레이션 작성

자동 생성이 완벽하지 않을 때 수동으로 작성:

```bash
# 빈 마이그레이션 파일 생성
alembic revision -m "Custom migration"
```

생성된 파일 편집:

```python
def upgrade():
    # 업그레이드 로직
    op.create_index('idx_user_email', 'users', ['email'])
    
def downgrade():
    # 다운그레이드 로직
    op.drop_index('idx_user_email', 'users')
```

## 유용한 팁

### 1. 마이그레이션 전 백업

프로덕션에서는 항상 마이그레이션 전에 백업:

```bash
# Neon은 자동 백업을 제공하지만, 수동 스냅샷도 가능
# Neon Console에서 "Restore" 탭 확인
```

### 2. 마이그레이션 테스트

로컬이나 스테이징 환경에서 먼저 테스트:

```bash
# 로컬 PostgreSQL 사용
DATABASE_URL=postgresql://localhost:5432/trip_planner_test alembic upgrade head
```

### 3. 마이그레이션 병합

여러 개발자가 동시에 마이그레이션을 만들었을 때:

```bash
# 충돌하는 마이그레이션 병합
alembic merge -m "Merge migrations" <rev1> <rev2>
```

### 4. 마이그레이션 스탬핑

기존 데이터베이스를 Alembic으로 관리하기 시작할 때:

```bash
# 현재 데이터베이스 상태를 특정 버전으로 표시
alembic stamp head
```

## 문제 해결

### 연결 오류

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**해결:**
- `.env` 파일의 `DATABASE_URL` 확인
- Neon 대시보드에서 데이터베이스가 활성 상태인지 확인
- 네트워크 연결 확인

### 마이그레이션 충돌

```
alembic.util.exc.CommandError: Multiple head revisions are present
```

**해결:**
```bash
alembic merge heads -m "Merge conflicting migrations"
alembic upgrade head
```

### 자동 생성이 변경사항을 감지하지 못함

**해결:**
- `alembic/env.py`에서 `target_metadata`가 올바르게 설정되었는지 확인
- 모델을 변경한 후 Python을 재시작
- 수동으로 마이그레이션 작성

## Neon 특화 설정

### 연결 풀링

Neon은 서버리스이므로 연결 풀링 최적화가 중요:

```python
# src/database.py에 이미 설정됨
engine = create_engine(
    db_url,
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_size=5,
    max_overflow=10
)
```

### SSL 연결

Neon은 SSL을 요구하므로 연결 문자열에 `?sslmode=require` 포함:

```
DATABASE_URL=postgresql://...?sslmode=require
```

## 참고 자료

- [Alembic 공식 문서](https://alembic.sqlalchemy.org/)
- [Neon 문서](https://neon.tech/docs/introduction)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)

## 빠른 참조

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "description"

# 적용
alembic upgrade head

# 되돌리기
alembic downgrade -1

# 상태 확인
alembic current

# 히스토리
alembic history
```
