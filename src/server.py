from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import TripPlannerAgent
from models import TimeSettings

app = FastAPI(
    title="Seoul Trip Planner API",
    description="자연어 기반 서울 여행 일정 생성 API",
    version="2.0.0"
)

agent = TripPlannerAgent()


class TripPlanRequest(BaseModel):
    """여행 계획 요청"""
    user_input: str = Field(..., description="사용자 입력 (자연어)")
    session_id: str = Field(..., description="세션 ID")

    # 프론트엔드에서 설정한 옵션들
    time_settings: Optional[TimeSettings] = Field(default=None, description="시간 설정")

    class Config:
        json_schema_extra = {
            "example": {
                "user_input": "홍대에서 보드게임하고 한식 먹을래",
                "session_id": "user123",
                "time_settings": {
                    "enabled": True,
                    "start_time": "14:00",
                    "duration_hours": 6
                }
            }
        }


class UserFeedbackRequest(BaseModel):
    """사용자 피드백"""
    workflow_id: str = Field(..., description="워크플로우 ID (DB)")
    feedback: str = Field(..., description="피드백 내용")


@app.post("/api/itinerary/plan", tags=["Itinerary"])
async def create_trip_plan(request: TripPlanRequest):
    """
    여행 일정 생성

    자연어 입력을 분석하여 활동 → 식사 → 카페 → 술집 순서의 일정을 생성합니다.

    ## Request Body
    - **user_input**: 자연어 입력 (예: "홍대에서 보드게임하고 한식 먹을래")
    - **session_id**: 세션 ID
    - **time_settings**: (선택) 시간 설정
        - enabled: 시간 설정 사용 여부
        - start_time: 시작 시간 (HH:MM)
        - duration_hours: 데이트 시간 (2~12시간)

    ## Response
    - **status**: "awaiting_user_input" (HIL 필요) 또는 "completed"
    - **itinerary**: 일정 정보
    - **progress**: 진행 메시지
    """
    try:
        print(f"[API] 여행 계획 요청")
        print(f"  - 입력: {request.user_input}")
        print(f"  - 세션: {request.session_id}")
        print(f"  - 시간 설정: {request.time_settings.enabled if request.time_settings else False}")

        result = await agent.plan_trip(
            user_input=request.user_input,
            session_id=request.session_id,
            time_settings=request.time_settings
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
        print(f"[API] 피드백 수신 - 워크플로우: {request.workflow_id}")
        result = await agent.provide_user_feedback(request.workflow_id, request.feedback)
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
        "service": "Seoul Trip Planner"
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
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)