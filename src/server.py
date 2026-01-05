from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# Ensure src is in python path so imports like 'from agent import ...' work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import TripPlannerAgent

app = FastAPI(title="Seoul Trip Planner API")

# Initialize agent
agent = TripPlannerAgent()


class TripPlanRequest(BaseModel):
    """여행 계획 요청"""
    location: str  # 지역명 또는 특정 장소
    session_id: str  # 세션 추적용 ID


class UserFeedbackRequest(BaseModel):
    """사용자 피드백"""
    session_id: str  # 세션 ID
    feedback: str  # 사용자 응답 내용


@app.post("/api/itinerary/plan")
async def create_trip_plan(request: TripPlanRequest):
    """
    여행 일정 생성

    - **location**: 방문하고 싶은 지역 또는 장소 (예: "홍대", "롯데월드")
    - **session_id**: 세션 추적을 위한 고유 ID

    Returns:
    - status: "awaiting_user_input" (사용자 입력 대기) 또는 "completed" (완료)
    - itinerary: 생성된 여행 일정 정보
    - progress: 진행 상황 메시지
    """
    try:
        print(f"[API] 여행 계획 요청 - 위치: {request.location}, 세션: {request.session_id}")
        result = await agent.plan_trip(request.location, request.session_id)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/itinerary/feedback")
async def submit_user_feedback(request: UserFeedbackRequest):
    """
    사용자 피드백 제공 및 일정 생성 재개

    - **session_id**: 세션 ID
    - **feedback**: 사용자 응답 (활동 선호도, 음식 선호도, 수정 요청 등)

    Returns:
    - status: "awaiting_user_input" (추가 입력 대기) 또는 "completed" (완료)
    - itinerary: 업데이트된 여행 일정 정보
    - progress: 진행 상황 메시지
    """
    try:
        print(f"[API] 피드백 수신 - 세션: {request.session_id}, 내용: {request.feedback}")
        result = await agent.provide_user_feedback(request.session_id, request.feedback)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "Seoul Trip Planner"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)