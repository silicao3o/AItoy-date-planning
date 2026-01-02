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

@app.post("/api/plan")
async def plan_trip(request: PlanRequest):
    """
    Plan a trip for a given region.
    """
    try:
        print(f"Received request for region: {request.region}")
        result = await agent.plan_trip(request.region)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
