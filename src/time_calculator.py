from datetime import datetime, timedelta
from typing import List, Tuple
import math


class TimeCalculator:
    """시간 계산 유틸리티"""

    # 장소 타입별 기본 소요 시간 (분)
    DEFAULT_DURATIONS = {
        "activity": 90,  # 활동 장소: 1.5시간
        "dining": 60,  # 식사: 1시간
        "cafe": 40,  # 카페: 40분
        "drinking": 90  # 술집: 1.5시간
    }

    @staticmethod
    def parse_time(time_str: str) -> datetime:
        """시간 문자열을 datetime으로 변환"""
        try:
            return datetime.strptime(time_str, "%H:%M")
        except:
            return datetime.strptime("14:00", "%H:%M")  # 기본값

    @staticmethod
    def format_time(dt: datetime) -> str:
        """datetime을 HH:MM 형식으로 변환"""
        return dt.strftime("%H:%M")

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        """두 좌표 간 거리 계산 (미터) - 하버사인 공식"""
        R = 6371000  # 지구 반지름 (미터)

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return int(distance)

    @classmethod
    def calculate_travel_time(cls, from_loc, to_loc) -> Tuple[str, int, int]:
        """
        두 장소 간 이동 시간 및 수단 계산

        Returns:
            Tuple[method, duration_minutes, distance_meters]
        """
        distance = cls.calculate_distance(
            from_loc.y, from_loc.x,
            to_loc.y, to_loc.x
        )

        # 거리에 따른 이동 수단 및 시간 결정
        if distance < 300:
            return "walk", 5, distance
        elif distance < 1000:
            # 도보 (시속 4.8km = 80m/분)
            minutes = int(distance / 80) + 2  # 여유 시간 추가
            return "walk", minutes, distance
        elif distance < 3000:
            # 짧은 대중교통 또는 도보
            minutes = int(distance / 200) + 5  # 대중교통 환승 시간 포함
            return "subway", minutes, distance
        else:
            # 대중교통
            minutes = int(distance / 400) + 10  # 환승 + 대기 시간
            return "subway", minutes, distance

    @classmethod
    def get_travel_description(cls, method: str, minutes: int, distance: int) -> str:
        """이동 정보를 사람이 읽기 쉬운 형식으로 변환"""
        if method == "walk":
            if distance < 100:
                return f"바로 옆 건물 (도보 {minutes}분)"
            else:
                return f"도보 {minutes}분 ({distance}m)"
        elif method == "subway":
            return f"지하철 {minutes}분"
        elif method == "bus":
            return f"버스 {minutes}분"
        else:
            return f"{minutes}분"

    @classmethod
    def format_duration(cls, minutes: int) -> str:
        """소요 시간을 읽기 쉬운 형식으로 변환"""
        if minutes < 60:
            return f"{minutes}분"
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours}시간"
            else:
                return f"{hours}시간 {mins}분"