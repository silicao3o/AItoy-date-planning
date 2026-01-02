import httpx
import asyncio


async def test():
    api_key = "2b0e2842adcacfeb9731a68eb4b42048"
    headers = {"Authorization": f"KakaoAK {api_key}"}

    # 가장 간단한 요청
    params = {
        "query": "이태원",
        "size": 1
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers=headers,
            params=params
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")


asyncio.run(test())