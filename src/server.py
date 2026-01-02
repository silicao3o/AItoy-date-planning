from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# Ensure src is in python path so imports like 'from agent import ...' work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import TripPlannerAgent

app = FastAPI(title="Seoul Trip Planner")

# Initialize agent - this might need environment variables loaded
agent = TripPlannerAgent()

class PlanRequest(BaseModel):
    region: str
    thread_id: str

class FeedbackRequest(BaseModel):
    thread_id: str
    category: str

@app.post("/api/plan")
async def plan_trip(request: PlanRequest):
    """
    Plan a trip for a given region. Use thread_id to track HIL state.
    """
    try:
        print(f"Received request for region: {request.region}, thread_id: {request.thread_id}")
        result = await agent.plan_trip(request.region, request.thread_id)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
async def provide_feedback(request: FeedbackRequest):
    """
    Provide feedback (preferred category) to continue the planning process.
    """
    try:
        print(f"Received feedback for thread_id: {request.thread_id}, category: {request.category}")
        result = await agent.provide_feedback(request.thread_id, request.category)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
