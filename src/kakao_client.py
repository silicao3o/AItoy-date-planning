import httpx
from typing import List, Optional
from models import Location
import os
from dotenv import load_dotenv

load_dotenv()


class KakaoMapClient:
    """카카오맵 API 클라이언트"""

    BASE_URL = "https://dapi.kakao.com/v2/local"

    def __init__(self):
        self.api_key = os.getenv("KAKAO_REST_API_KEY")

        # 디버깅 출력
        print(f"🔑 API Key loaded: {self.api_key[:10] if self.api_key else 'None'}...")

        if not self.api_key:
            raise ValueError("KAKAO_REST_API_KEY not found in environment")

        self.headers = {
            "Authorization": f"KakaoAK {self.api_key}"
        }

        # 헤더 확인
        print(f"📋 Authorization Header: KakaoAK {self.api_key[:10]}...")

    async def find_activity_places(
            self,
            location_name: str,
            radius: int = 2000,
            size: int = 10
    ) -> List[Location]:
        """활동 장소 검색 (관광지, 명소, 박물관 등)"""
        keywords = [
            f"{location_name} 관광지",
            f"{location_name} 명소",
            f"{location_name} 공원",
            f"{location_name} 박물관"
        ]

        all_results = []
        async with httpx.AsyncClient() as client:
            for keyword in keywords:
                params = {
                    "query": keyword,
                    "size": size,
                    "sort": "accuracy"
                }

                response = await client.get(
                    f"{self.BASE_URL}/search/keyword.json",
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()

                for doc in data.get("documents", []):
                    location = Location(
                        name=doc["place_name"],
                        category=doc["category_name"],
                        address=doc["address_name"],
                        x=float(doc["x"]),
                        y=float(doc["y"]),
                        phone=doc.get("phone"),
                        place_url=doc.get("place_url"),
                        distance=int(doc.get("distance", 0)) if doc.get("distance") else None
                    )
                    all_results.append(location)

        # 중복 제거 (같은 이름의 장소)
        seen = set()
        unique_results = []
        for loc in all_results:
            if loc.name not in seen:
                seen.add(loc.name)
                unique_results.append(loc)

        return unique_results[:size]

    async def find_specific_place(self, place_name: str) -> Optional[Location]:
        """특정 장소 하나 검색 (제일 정확도 높은 것)"""
        async with httpx.AsyncClient() as client:
            params = {
                "query": place_name,
                "size": 1,
                "sort": "accuracy"
            }
            response = await client.get(
                f"{self.BASE_URL}/search/keyword.json",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("documents"):
                return None

            doc = data["documents"][0]
            return Location(
                name=doc["place_name"],
                category=doc["category_name"],
                address=doc["address_name"],
                x=float(doc["x"]),
                y=float(doc["y"]),
                phone=doc.get("phone"),
                place_url=doc.get("place_url"),
                distance=int(doc.get("distance", 0)) if doc.get("distance") else None
            )

    async def search_by_category(
            self,
            category_code: str,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 5,
            sort: str = "distance"
    ) -> List[Location]:
        """카테고리별 장소 검색 (FD6: 음식점, CE7: 카페 등)"""
        async with httpx.AsyncClient() as client:
            params = {
                "category_group_code": category_code,
                "x": x,
                "y": y,
                "radius": radius,
                "size": size,
                "sort": sort
            }

            response = await client.get(
                f"{self.BASE_URL}/search/category.json",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for doc in data.get("documents", []):
                location = Location(
                    name=doc["place_name"],
                    category=doc["category_name"],
                    address=doc["address_name"],
                    x=float(doc["x"]),
                    y=float(doc["y"]),
                    phone=doc.get("phone"),
                    place_url=doc.get("place_url"),
                    distance=int(doc["distance"])
                )
                results.append(location)

            return results

    async def search_nearby_by_keyword(
            self,
            keyword: str,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 5
    ) -> List[Location]:
        """좌표 주변 키워드 검색"""
        async with httpx.AsyncClient() as client:
            params = {
                "query": keyword,
                "x": x,
                "y": y,
                "radius": radius,
                "size": size,
                "sort": "distance"
            }

            response = await client.get(
                f"{self.BASE_URL}/search/keyword.json",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for doc in data.get("documents", []):
                location = Location(
                    name=doc["place_name"],
                    category=doc["category_name"],
                    address=doc["address_name"],
                    x=float(doc["x"]),
                    y=float(doc["y"]),
                    phone=doc.get("phone"),
                    place_url=doc.get("place_url"),
                    distance=int(doc.get("distance", 0))
                )
                results.append(location)

            return results

    async def find_dining_places(
            self,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 5
    ) -> List[Location]:
        """특정 좌표 주변 음식점 검색"""
        return await self.search_by_category("FD6", x, y, radius, size)