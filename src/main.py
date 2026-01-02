import asyncio
from agent import TripPlannerAgent


async def main():
    agent = TripPlannerAgent()

    # 사용자 입력
    region = input("어느 지역을 여행하고 싶으신가요? (예: 홍대, 강남, 이태원): ")

    print(f"\n🔍 '{region}' 여행 계획을 생성하고 있습니다...\n")

    # 여행 계획 생성
    result = await agent.plan_trip(region)

    # 진행 상황 출력
    print("📋 진행 과정:")
    for msg in result["messages"]:
        print(f"  {msg}")

    # 최종 스케줄 출력
    print(f"\n🎯 '{result['parsed_region']}' 추천 일정:\n")
    print("=" * 60)

    for item in result["schedule"]:
        loc = item.location
        print(f"\n{item.order}. {loc.name}")
        print(f"   📍 주소: {loc.address}")
        print(f"   ⏱️  예상 소요시간: {item.estimated_time}")
        if item.notes:
            print(f"   💡 참고: {item.notes}")
        if loc.phone:
            print(f"   📞 전화: {loc.phone}")
        if loc.place_url:
            print(f"   🔗 상세정보: {loc.place_url}")

    print("\n" + "=" * 60)
    print(f"\n총 {len(result['schedule'])}개 장소 방문 예정")

    # 놀거리 목록
    print(f"\n🎡 발견한 놀거리 ({len(result['attractions'])}개):")
    for attr in result["attractions"][:5]:
        print(f"  • {attr.name} - {attr.category}")

    # 음식점 목록
    print(f"\n🍽️  발견한 음식점 ({len(result['restaurants'])}개):")
    for rest in result["restaurants"]:
        print(f"  • {rest.name} - {rest.category}")


if __name__ == "__main__":
    asyncio.run(main())