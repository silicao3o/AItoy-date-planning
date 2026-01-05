from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import TripPlannerAgent
from models import TimeSettings, DateTheme

app = FastAPI(
    title="Seoul Trip Planner API v2",
    description="⏰시간대별 일정 / ⭐평점 필터링 / 🎨테마 선택 기능 포함",
    version="2.0.0"
)

agent = TripPlannerAgent()


class TripPlanRequest(BaseModel):
    """여행 계획 요청"""
    location: str = Field(..., description="방문 장소 (예: 홍대, 롯데월드)")
    session_id: str = Field(..., description="세션 ID")

    # 프론트엔드에서 설정한 옵션들
    time_settings: Optional[TimeSettings] = Field(default=None, description="시간 설정")
    date_theme: Optional[DateTheme] = Field(default=None, description="데이트 테마")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "홍대",
                "session_id": "user123",
                "time_settings": {
                    "enabled": True,
                    "start_time": "14:00",
                    "duration_hours": 6
                },
                "date_theme": {
                    "theme": "cultural",
                    "atmosphere": "romantic"
                }
            }
        }


class UserFeedbackRequest(BaseModel):
    """사용자 피드백"""
    session_id: str = Field(..., description="세션 ID")
    feedback: str = Field(..., description="피드백 내용")


@app.post("/api/itinerary/plan", tags=["Itinerary"])
async def create_trip_plan(request: TripPlanRequest):
    """
    여행 일정 생성

    ## 새로운 기능 🎉
    - ⏰ **시간대별 일정**: 시작 시간과 소요 시간을 설정하면 구체적인 시간표 생성
    - ⭐ **평점 기반 필터링**: 신뢰도 높은 장소 우선 추천
    - 🎨 **데이트 테마**: 문화/힐링/액티비티/맛집/나이트 중 선택
    - 🎭 **분위기 설정**: 캐주얼/로맨틱/활기찬 분위기에 맞는 장소 추천

    ## Request Body
    - **location**: 방문 지역/장소
    - **session_id**: 세션 ID
    - **time_settings**: (선택)
        - enabled: 시간 설정 사용 여부
        - start_time: 시작 시간 (HH:MM)
        - duration_hours: 데이트 시간 (2~12시간)
    - **date_theme**: (선택)
        - theme: cultural/healing/activity/foodie/nightlife
        - atmosphere: casual/romantic/energetic

    ## Response
    - **status**: "awaiting_user_input" 또는 "completed"
    - **itinerary**: 일정 정보
        - schedule: 시간표 포함된 상세 일정 (time_settings가 enabled일 때)
        - locations: 장소 목록 (평점 기반 필터링 적용)
    - **progress**: 진행 메시지
    """
    try:
        print(f"[API] 여행 계획 요청 v2")
        print(f"  - 위치: {request.location}")
        print(f"  - 세션: {request.session_id}")
        print(f"  - 시간 설정: {request.time_settings.enabled if request.time_settings else False}")
        print(f"  - 테마: {request.date_theme.theme if request.date_theme else 'None'}")

        result = await agent.plan_trip(
            user_input=request.location,
            session_id=request.session_id,
            time_settings=request.time_settings,
            date_theme=request.date_theme
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/itinerary/feedback", tags=["Itinerary"])
async def submit_user_feedback(request: UserFeedbackRequest):
    """사용자 피드백 제공"""
    try:
        print(f"[API] 피드백 수신 - 세션: {request.session_id}")
        result = await agent.provide_user_feedback(request.session_id, request.feedback)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "Seoul Trip Planner v2",
        "features": [
            "⏰ 시간대별 일정 생성",
            "⭐ 평점 기반 필터링",
            "🎨 데이트 테마 선택",
            "🎭 분위기 맞춤 추천"
        ]
    }


@app.get("/api/settings/defaults", tags=["Settings"])
async def get_default_settings():
    """기본 설정값 조회 (프론트엔드용)"""
    return {
        "time": {
            "default_start_time": "14:00",
            "default_duration_hours": 6,
            "min_duration_hours": 2,
            "max_duration_hours": 12
        },
        "themes": {
            "options": [
                {"value": "cultural", "label": "🎨 문화/예술", "description": "미술관, 박물관, 갤러리, 전시"},
                {"value": "healing", "label": "🌳 힐링/자연", "description": "공원, 산책로, 조용한 카페"},
                {"value": "activity", "label": "🎮 액티비티", "description": "방탈출, 체험, 놀거리"},
                {"value": "foodie", "label": "🍽️ 맛집 투어", "description": "유명 맛집 중심"},
                {"value": "nightlife", "label": "🌃 나이트 라이프", "description": "바, 클럽, 루프탑"}
            ]
        },
        "atmosphere": {
            "options": [
                {"value": "casual", "label": "😊 캐주얼", "description": "편안하고 자연스러운"},
                {"value": "romantic", "label": "💕 로맨틱", "description": "분위기 있고 특별한"},
                {"value": "energetic", "label": "⚡ 활기찬", "description": "역동적이고 트렌디한"}
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)