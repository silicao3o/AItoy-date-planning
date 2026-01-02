import asyncio
import httpx

async def test_plan():
    print("Testing Region Case...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post("http://localhost:8000/api/plan", json={"region": "홍대"})
            print("Status:", resp.status_code)
            data = resp.json()
            print("Messages:", data.get("messages"))
            print("Schedule items:", len(data.get("schedule", [])))
        except Exception as e:
            print("Server likely not running or error:", e)

    print("\nTesting Spot Case...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post("http://localhost:8000/api/plan", json={"region": "롯데월드"})
            print("Status:", resp.status_code)
            data = resp.json()
            print("Messages:", data.get("messages"))
            print("Schedule:", len(data.get("schedule", [])))
        except Exception as e:
            print("Server likely not running or error:", e)

if __name__ == "__main__":
    asyncio.run(test_plan())
