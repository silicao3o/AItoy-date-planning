import asyncio
import httpx
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.kakao_client import KakaoMapClient

async def test_search():
    client = KakaoMapClient()
    location = "홍대"
    preference = "보드게임"
    
    keywords = [f"{location} {preference}", f"{location} 보드게임카페"]
    
    print(f"Testing keywords: {keywords}")
    
    async with httpx.AsyncClient() as http_client:
        for kw in keywords:
            params = {"query": kw, "size": 5, "sort": "accuracy"}
            headers = {"Authorization": f"KakaoAK {client.api_key}"}
            try:
                res = await http_client.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    headers=headers,
                    params=params
                )
                print(f"Status for {kw}: {res.status_code}")
                if res.status_code == 200:
                    data = res.json()
                    count = len(data.get("documents", []))
                    print(f"Found {count} docs for {kw}")
                    if count > 0:
                        print(f"First doc: {data['documents'][0]['place_name']}")
                else:
                    print(f"Error: {res.text}")
            except Exception as e:
                print(f"Exception for {kw}: {e}")

if __name__ == "__main__":
    asyncio.run(test_search())
