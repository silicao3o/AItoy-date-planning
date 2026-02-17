import asyncio
import uuid
from agent import TripPlannerAgent
from models import TimeSettings


async def main():
    agent = TripPlannerAgent()

    # 세션 ID 자동 생성
    session_id = str(uuid.uuid4())
    print(f"🔑 세션 ID: {session_id}\n")

    # 사용자 입력
    region = input("어느 지역을 여행하고 싶으신가요? (예: 홍대, 강남, 이태원): ")

    # 시간 설정 입력 (선택)
    use_time = input("\n시간 설정을 하시겠어요? (y/n, 기본값: n): ").lower() == 'y'
    time_settings = None

    if use_time:
        start_time = input("시작 시간을 입력하세요 (예: 14:00, 기본값: 14:00): ").strip() or "14:00"
        duration_str = input("데이트 시간을 입력하세요 (예: 6, 기본값: 6시간): ").strip() or "6"
        try:
            duration_hours = int(duration_str)
            time_settings = TimeSettings(
                enabled=True,
                start_time=start_time,
                duration_hours=duration_hours
            )
            print(f"✓ 시간 설정: {start_time} 시작, {duration_hours}시간")
        except ValueError:
            print("! 잘못된 입력. 기본값 사용")

    print(f"\n🔍 '{region}' 여행 계획을 생성하고 있습니다...\n")

    # 여행 계획 생성
    result = await agent.plan_trip(
        user_input=region,
        session_id=session_id,
        time_settings=time_settings
    )

    # 진행 상황 출력
    print("📋 진행 과정:")
    for msg in result.get("progress", []):
        print(f"  {msg}")

    # 최종 결과 확인
    if result["status"] == "awaiting_user_input":
        print("\n⏸️  사용자 입력이 필요합니다.")
        print(f"대기 중인 단계: {result['pending_step']}")

        # HIL 처리 (간단 버전)
        feedback = input("\n피드백을 입력하세요: ")
        result = await agent.provide_user_feedback(session_id, feedback)

        # 추가 진행 메시지 출력
        print("\n📋 추가 진행:")
        for msg in result.get("progress", []):
            print(f"  {msg}")

    # 최종 스케줄 출력
    if result["status"] == "completed":
        itinerary = result.get("itinerary", {})
        parsed_location = itinerary.get("input", {}).get("parsed", region)

        print(f"\n🎯 '{parsed_location}' 추천 일정:\n")
        print("=" * 80)

        schedule = itinerary.get("schedule", [])

        for item_dict in schedule:
            print(f"\n{item_dict['order']}. {item_dict['location']['name']}")

            # 시간 정보 표시 (있는 경우)
            if item_dict.get('start_time') and item_dict.get('end_time'):
                print(f"   🕐 시간: {item_dict['start_time']} - {item_dict['end_time']} ({item_dict['estimated_time']})")
            else:
                print(f"   ⏱️  예상 소요시간: {item_dict['estimated_time']}")

            print(f"   📍 주소: {item_dict['location']['address']}")
            print(f"   🏷️  카테고리: {item_dict['location']['category']}")

            if item_dict.get('notes'):
                print(f"   💡 참고: {item_dict['notes']}")

            if item_dict['location'].get('phone'):
                print(f"   📞 전화: {item_dict['location']['phone']}")

            if item_dict['location'].get('place_url'):
                print(f"   🔗 상세정보: {item_dict['location']['place_url']}")

            # 이동 정보 표시
            if item_dict.get('travel_to_next'):
                travel = item_dict['travel_to_next']
                print(f"   🚶 다음 장소까지: {travel['description']}")

        print("\n" + "=" * 80)
        print(f"\n총 {len(schedule)}개 장소 방문 예정")

        # 장소별 요약
        locations = itinerary.get("locations", {})

        activities = locations.get("activities", [])
        if activities:
            print(f"\n🎡 발견한 활동 장소 ({len(activities)}개):")
            for place in activities[:5]:
                print(f"  • {place['name']} - {place['category']}")

        dining = locations.get("dining", [])
        if dining:
            print(f"\n🍽️  발견한 식사 장소 ({len(dining)}개):")
            for place in dining[:5]:
                print(f"  • {place['name']} - {place['category']}")

        cafes = locations.get("cafes", [])
        if cafes:
            print(f"\n☕ 발견한 카페 ({len(cafes)}개):")
            for place in cafes[:5]:
                print(f"  • {place['name']} - {place['category']}")

        bars = locations.get("bars", [])
        if bars:
            print(f"\n🍺 발견한 술집/바 ({len(bars)}개):")
            for place in bars[:5]:
                print(f"  • {place['name']} - {place['category']}")

        # 세션 정보 표시
        print(f"\n📝 세션 ID: {session_id}")
        print("   (이 ID로 나중에 일정을 다시 조회할 수 있습니다)")


if __name__ == "__main__":
    asyncio.run(main())