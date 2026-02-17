데이터베이스 마이그레이션을 실행합니다.

새 마이그레이션 생성:
```bash
alembic revision --autogenerate -m "$ARGUMENTS"
```

마이그레이션 적용:
```bash
alembic upgrade head
```

인자가 없으면 마이그레이션만 적용합니다.
