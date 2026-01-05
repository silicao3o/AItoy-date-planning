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
            distance=int(doc.get("distance", 0)) if doc.get("distance") else None,
            # 카카오맵 API에는 평점이 없으므로 더미값 또는 별도 API 필요
            rating=None,
            review_count=None
        )

    def _filter_by_rating(self, locations: List[Location], min_rating: float = 4.0) -> List[Location]:
        """
        평점 기반 필터링 (카카오맵 API에는 평점이 없으므로 대안 사용)

        대안 방법:
        1. 카테고리 신뢰도 사용 (대형 체인 > 로컬)
        2. 리뷰가 많은 장소 우선 (카카오맵 place_url 크롤링 필요)
        3. 현재는 거리 + 카테고리 신뢰도로 정렬
        """
        # 신뢰할 수 있는 카테고리 키워드
        trusted_keywords = ["맛집", "유명", "본점", "직영", "공식"]

        def calculate_score(loc: Location) -> float:
            score = 0.0

            # 거리 점수 (가까울수록 높음)
            if loc.distance:
                distance_score = max(0, 1000 - loc.distance) / 1000
                score += distance_score * 0.5

            # 카테고리 신뢰도 점수
            for keyword in trusted_keywords:
                if keyword in loc.name or keyword in loc.category:
                    score += 0.5
                    break

            # 전화번호가 있으면 신뢰도 증가
            if loc.phone:
                score += 0.3

            return score

        # 점수 기반 정렬
        scored_locations = [(loc, calculate_score(loc)) for loc in locations]
        scored_locations.sort(key=lambda x: x[1], reverse=True)

        return [loc for loc, score in scored_locations]

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
        # 테마별 키워드 매핑
        theme_keywords = {
            "cultural": [f"{location_name} 미술관", f"{location_name} 박물관",
                         f"{location_name} 갤러리", f"{location_name} 전시"],
            "healing": [f"{location_name} 공원", f"{location_name} 산책",
                        f"{location_name} 힐링", f"{location_name} 자연"],
            "activity": [f"{location_name} 방탈출", f"{location_name} 체험",
                         f"{location_name} 액티비티", f"{location_name} 놀거리"],
            "foodie": [f"{location_name} 맛집", f"{location_name} 유명 음식점"],
            "nightlife": [f"{location_name} 바", f"{location_name} 루프탑",
                          f"{location_name} 나이트"],
        }

        # 기본 키워드 (테마가 없을 때)
        default_keywords = [
            f"{location_name} 관광지",
            f"{location_name} 명소",
            f"{location_name} 공원",
            f"{location_name} 박물관"
        ]

        keywords = theme_keywords.get(theme, default_keywords)

        all_results = []
        async with httpx.AsyncClient() as client:
            for keyword in keywords:
                params = {
                    "query": keyword,
                    "size": size,
                    "sort": "accuracy"
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

        # 평점/신뢰도 기반 필터링
        filtered_results = self._filter_by_rating(unique_results)

        return filtered_results[:size]

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
        """카테고리별 장소 검색 (평점 필터링 포함)"""
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

            # 평점 기반 필터링
            filtered_results = self._filter_by_rating(results)

            return filtered_results[:10]  # 상위 10개만 반환

    async def search_nearby_by_keyword(
            self,
            keyword: str,
            x: float,
            y: float,
            radius: int = 500,
            size: int = 15
    ) -> List[Location]:
        """좌표 주변 키워드 검색 (평점 필터링 포함)"""
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

            # 평점 기반 필터링
            filtered_results = self._filter_by_rating(results)

            return filtered_results[:10]

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