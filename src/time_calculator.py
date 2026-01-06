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
        if distance <= 1200:
            # 도보 (시속 4km = 분당 67m)
            # 신호등 등 고려하여 분당 60m로 계산
            minutes = max(1, int(distance / 60))
            return "walk", minutes, distance
        
        else:
            # 차량/대중교통 (시속 30km = 분당 500m)
            # 기본 대기/탑승 시간 5분 + 이동 시간
            minutes = int(distance / 500) + 5
            
            # 5km 이상이면 지하철/버스 추천, 그 미만이면 택시 추천
            if distance < 5000:
                return "taxi", minutes, distance
            else:
                return "public_transport", minutes + 10, distance # 대중교통은 대기시간 더 김

    @classmethod
    def get_travel_description(cls, method: str, minutes: int, distance: int) -> str:
        """이동 정보를 사람이 읽기 쉬운 형식으로 변환"""
        if method == "walk":
            if distance < 100:
                return f"바로 옆 (도보 {minutes}분)"
            else:
                return f"도보 {minutes}분 ({distance}m)"
        elif method == "taxi":
            return f"택시 추천 {minutes}분 ({distance/1000:.1f}km)"
        elif method == "public_transport":
            return f"대중교통 {minutes}분 ({distance/1000:.1f}km)"
        else:
            return f"이동 {minutes}분"

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

    @classmethod
    def find_optimized_path(
        cls, 
        start_point, 
        activities: list, 
        dinings: list, 
        cafes: list, 
        bars: list
    ) -> list:
        """
        최단 이동 거리를 가지는 최적의 경로를 탐색합니다.
        (Greedy 방식은 최적해가 아닐 수 있으므로, 가능한 조합 중 최소 거리를 찾음)
        """
        best_path = []
        min_total_dist = float('inf')
        
        # 선택지가 없으면 빈 리스트 반환
        if not activities and not dinings:
            return []

        # 각 단계별 후보군 (최대 3개씩만 고려하여 연산량 조절)
        cand_activities = activities[:3] if activities else []
        cand_dinings = dinings[:3] if dinings else []
        cand_cafes = cafes[:3] if cafes else []
        cand_bars = bars[:3] if bars else []

        # 경로 구성을 위한 더미 리스트 (없을 경우 패스)
        temp_stages = []
        if cand_activities: temp_stages.append(("activity", cand_activities))
        if cand_dinings: temp_stages.append(("dining", cand_dinings))
        if cand_cafes: temp_stages.append(("cafe", cand_cafes))
        if cand_bars: temp_stages.append(("drinking", cand_bars))

        import itertools
        
        # 가능한 모든 조합 생성 (Cartesian Product)
        # 예: Act1 -> Din1 -> Caf1 -> Bar1 vs Act2 -> Din1 ...
        stage_names = [s[0] for s in temp_stages]
        stage_candidates = [s[1] for s in temp_stages]
        
        for path in itertools.product(*stage_candidates):
            current_dist = 0
            
            # 시작점이 있는 경우 시작점 -> 첫 장소 거리 추가
            prev_loc = start_point
            
            valid_path = True
            path_with_type = []

            for i, loc in enumerate(path):
                path_with_type.append((stage_names[i], loc))
                
                if prev_loc:
                    dist = cls.calculate_distance(prev_loc.y, prev_loc.x, loc.y, loc.x)
                    current_dist += dist
                
                prev_loc = loc
            
            if current_dist < min_total_dist:
                min_total_dist = current_dist
                best_path = path_with_type

        return best_path