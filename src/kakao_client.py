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
            theme: Optional[str] = None,
            radius: int = 2000,
            size: int = 10
    ) -> List[Location]:
        """
        활동 장소 검색 (테마별)

        theme:
        - cultural: 문화/예술 (미술관, 박물관, 갤러리, 공연장)
        - healing: 힐링/자연 (공원, 카페, 한강, 산책로)
        - activity: 액티비티 (방탈출, VR, 볼링, 스크린골프)
        - foodie: 맛집 투어 (유명 맛집)
        - nightlife: 나이트 라이프 (클럽, 바, 루프탑)
        """
        # 테마별 키워드 매핑 및 카테고리 코드
        theme_configs = {
            "cultural": {
                "keywords": [f"{location_name} 미술관", f"{location_name} 박물관", f"{location_name} 전시"],
                "category_code": "CT1"  # 문화시설
            },
            "healing": {
                "keywords": [f"{location_name} 공원", f"{location_name} 산책", f"{location_name} 힐링"],
                "category_code": "AT4"  # 관광명소
            },
            "activity": {
                "keywords": [f"{location_name} 방탈출", f"{location_name} 체험", f"{location_name} 액티비티", f"{location_name} 보드게임카페"],
                "category_code": None
            },
            "foodie": {
                "keywords": [f"{location_name} 맛집"],
                "category_code": "FD6"  # 음식점
            },
            "nightlife": {
                "keywords": [f"{location_name} 바", f"{location_name} 펍", f"{location_name} 이자카야"],
                "category_code": None  # 술집은 FD6지만 주점 등으로 분류될 수 있어 키워드 위주
            }
        }

        # 기본 설정 (테마가 없거나 매칭 안될 때)
        default_config = {
            "keywords": [f"{location_name} 가볼만한곳", f"{location_name} 명소"],
            "category_code": "AT4"  # 기본적으로 관광명소 위주
        }

        config = theme_configs.get(theme, default_config)
        keywords = config["keywords"]
        category_code = config.get("category_code")

        all_results = []
        async with httpx.AsyncClient() as client:
            for keyword in keywords:
                params = {
                    "query": keyword,
                    "size": size,
                    "sort": "accuracy"
                }
                
                # 카테고리 코드가 있으면 파라미터에 추가하여 필터링 강화
                if category_code:
                    params["category_group_code"] = category_code

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
            atmosphere: Optional[str] = None,
            radius: int = 500,
            size: int = 10
    ) -> List[Location]:
        """
        식사 장소 검색 (분위기별)

        atmosphere:
        - casual: 캐주얼한 식당
        - romantic: 로맨틱한 레스토랑
        - energetic: 활기찬 맛집
        """
        # 분위기별 추가 필터링
        places = await self.search_by_category("FD6", x, y, radius, size * 2)

        if not atmosphere or atmosphere == "casual":
            return places[:size]

        # 분위기별 키워드 필터링
        atmosphere_keywords = {
            "romantic": ["레스토랑", "파인다이닝", "뷰맛집", "루프탑", "분위기"],
            "energetic": ["맛집", "인기", "핫플", "줄서는"]
        }

        keywords = atmosphere_keywords.get(atmosphere, [])

        if keywords:
            filtered = []
            for place in places:
                if any(kw in place.name or kw in place.category for kw in keywords):
                    filtered.append(place)

            # 키워드 매칭이 부족하면 원본 사용
            if len(filtered) < 3:
                return places[:size]
            return filtered[:size]

        return places[:size]

    async def find_cafe_places(
            self,
            x: float,
            y: float,
            atmosphere: Optional[str] = None,
            radius: int = 500,
            size: int = 10
    ) -> List[Location]:
        """카페 검색 (분위기별)"""
        places = await self.search_by_category("CE7", x, y, radius, size * 2)

        if not atmosphere or atmosphere == "casual":
            return places[:size]

        atmosphere_keywords = {
            "romantic": ["조용한", "분위기", "힐링", "루프탑", "뷰"],
            "energetic": ["핫플", "인기", "트렌디"]
        }

        keywords = atmosphere_keywords.get(atmosphere, [])

        if keywords:
            filtered = []
            for place in places:
                if any(kw in place.name or kw in place.category for kw in keywords):
                    filtered.append(place)

            if len(filtered) < 3:
                return places[:size]
            return filtered[:size]

        return places[:size]