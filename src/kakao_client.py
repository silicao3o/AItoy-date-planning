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

        print(f"🔑 API Key loaded: {self.api_key[:10] if self.api_key else 'None'}...")

        if not self.api_key:
            raise ValueError("KAKAO_REST_API_KEY not found in environment")

        self.headers = {
            "Authorization": f"KakaoAK {self.api_key}"
        }

        print(f"📋 Authorization Header: KakaoAK {self.api_key[:10]}...")

    def _parse_location(self, doc: dict) -> Location:
        """카카오맵 API 응답을 Location 객체로 변환"""
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

    async def find_activity_places(
            self,
            location_name: str,
            radius: int = 2000,
            size: int = 10
    ) -> List[Location]:
        """활동 장소 검색"""
        keywords = [f"{location_name} 가볼만한곳", f"{location_name} 명소"]

        all_results = []
        async with httpx.AsyncClient() as client:
            for keyword in keywords:
                params = {
                    "query": keyword,
                    "size": size,
                    "sort": "accuracy",
                    "category_group_code": "AT4"  # 관광명소
                }

                try:
                    response = await client.get(
                        f"{self.BASE_URL}/search/keyword.json",
                        headers=self.headers,
                        params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    for doc in data.get("documents", []):
                        location = self._parse_location(doc)
                        all_results.append(location)
                except Exception as e:
                    print(f"검색 실패 ({keyword}): {e}")

        # 중복 제거
        seen = set()
        unique_results = []
        for loc in all_results:
            if loc.name not in seen:
                seen.add(loc.name)
                unique_results.append(loc)

        return unique_results[:size]

    async def find_specific_place(self, place_name: str) -> Optional[Location]:
        """특정 장소 하나 검색"""
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
            return self._parse_location(doc)

    async def search_by_category(
            self,
            category_code: str,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 15,  # 필터링을 위해 더 많이 가져옴
            sort: str = "distance"
    ) -> List[Location]:
        """카테고리별 장소 검색"""
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
                location = self._parse_location(doc)
                results.append(location)

            return results[:size]  # 요청한 크기만큼 반환

    async def search_nearby_by_keyword(
            self,
            keyword: str,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 15
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
                location = self._parse_location(doc)
                results.append(location)

            return results[:size]

    async def find_dining_places(
            self,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 10
    ) -> List[Location]:
        """식사 장소 검색"""
        return await self.search_by_category("FD6", x, y, radius, size)

    async def find_cafe_places(
            self,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 10
    ) -> List[Location]:
        """카페 검색"""
        return await self.search_by_category("CE7", x, y, radius, size)