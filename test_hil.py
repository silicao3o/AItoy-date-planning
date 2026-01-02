import asyncio
import httpx
import uuid

async def test_hil_flow():
    thread_id = str(uuid.uuid4())
    print(f"Starting HIL Test with Thread ID: {thread_id}")
    
    # 1. Start Plan (Region)
    print("\n1. Sending initial plan request (Region: 홍대)...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://localhost:8000/api/plan", 
                json={"region": "홍대", "thread_id": thread_id},
                timeout=30.0
            )
            print("Status:", resp.status_code)
            data = resp.json()
            
            status = data.get("status")
            print(f"Current Status: {status}")
            print("Messages:", data.get("messages", [])[-2:]) # Show last 2 messages
            
            if status == "waiting_permission":
                print("\n-> Agent is waiting for user preference!")
                
                # 2. Provide Feedback
                print("\n2. Sending feedback (Category: 방탈출)...")
                # wait a bit
                await asyncio.sleep(1)
                
                resp2 = await client.post(
                    "http://localhost:8000/api/feedback",
                    json={"thread_id": thread_id, "category": "방탈출"},
                    timeout=30.0
                )
                print("Status:", resp2.status_code)
                data2 = resp2.json()
                
                print(f"Final Status: {data2.get('status')}")
                schedule = data2.get("result", {}).get("schedule", [])
                print(f"Schedule items: {len(schedule)}")
                
                # Check if attractions match preference
                attractions = data2.get("result", {}).get("attractions", [])
                print("\nFound Attractions:")
                for a in attractions:
                    print(f"- {a['name']} ({a['category']})")
                    
            else:
                print("Unexpected status. HIL didn't trigger?")

        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_hil_flow())
