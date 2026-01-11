#!/bin/bash

# 초기 마이그레이션 생성 및 적용 스크립트

set -e  # 에러 발생 시 중단

echo "🚀 데이터베이스 마이그레이션 초기화"
echo ""

# 1. 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    echo "📝 .env.example을 복사하여 .env 파일을 생성하고 DATABASE_URL을 설정하세요."
    echo ""
    echo "예시:"
    echo "  cp .env.example .env"
    echo "  # .env 파일을 편집하여 DATABASE_URL 설정"
    exit 1
fi

# 2. DATABASE_URL 확인
source .env
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL 환경 변수가 설정되지 않았습니다."
    echo "📝 .env 파일에 DATABASE_URL을 추가하세요."
    echo ""
    echo "예시:"
    echo "  DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/trip_planner?sslmode=require"
    exit 1
fi

echo "✅ DATABASE_URL 확인 완료"
echo ""

# 3. 기존 마이그레이션 확인
if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions)" ]; then
    echo "⚠️  기존 마이그레이션 파일이 존재합니다."
    echo "계속하시겠습니까? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "취소되었습니다."
        exit 0
    fi
fi

# 4. 초기 마이그레이션 생성
echo "📝 초기 마이그레이션 생성 중..."
alembic revision --autogenerate -m "Initial schema - User, Workflow, Node, Generation tables"

if [ $? -ne 0 ]; then
    echo "❌ 마이그레이션 생성 실패"
    exit 1
fi

echo "✅ 마이그레이션 파일 생성 완료"
echo ""

# 5. 마이그레이션 적용
echo "🔄 데이터베이스에 마이그레이션 적용 중..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ 마이그레이션 적용 실패"
    exit 1
fi

echo "✅ 마이그레이션 적용 완료"
echo ""

# 6. 현재 상태 확인
echo "📊 현재 데이터베이스 상태:"
alembic current

echo ""
echo "🎉 데이터베이스 초기화 완료!"
echo ""
echo "다음 명령으로 테이블을 확인할 수 있습니다:"
echo "  psql \$DATABASE_URL -c '\\dt'"
