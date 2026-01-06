import asyncio
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.agent import TripPlannerAgent
from src.models import TimeSettings, DateTheme


async def test_natural_language_planning():
    """자연어 기반 플래닝 테스트"""
    
    agent = TripPlannerAgent()
    
    print("=" * 80)
    print("🤖 자연어 기반 여행 플래닝 테스트")
    print("=" * 80)
    
    # 테스트 케이스 1: 보드게임카페 + 한식
    print("\n\n📝 테스트 1: 홍대에서 보드게임카페 가고 한식 먹고 싶어")
    print("-" * 80)
    
    result1 = await agent.plan_trip(
        user_input="홍대에서 보드게임카페 가고 한식 먹고 싶어",
        session_id="test_session_1",
        time_settings=TimeSettings(enabled=True, start_time="14:00", duration_hours=6)
    )
    
    print(f"\n상태: {result1['status']}")
    print("\n진행 메시지:")
    for msg in result1['progress']:
        print(f"  {msg}")
    
    if result1['status'] == 'completed':
        print(f"\n✅ 일정 생성 완료!")
        print(f"활동 장소: {len(result1['itinerary']['locations']['activities'])}개")
        print(f"식사 장소: {len(result1['itinerary']['locations']['dining'])}개")
        print(f"카페: {len(result1['itinerary']['locations']['cafes'])}개")
        print(f"술집: {len(result1['itinerary']['locations']['bars'])}개")
        
        print("\n📋 최종 일정:")
        for item in result1['itinerary']['schedule']:
            print(f"  {item['order']}. {item['location']['name']}")
            if item.get('start_time'):
                print(f"     ⏰ {item['start_time']} - {item['end_time']}")
            if item.get('travel_to_next'):
                print(f"     🚗 다음: {item['travel_to_next']['description']}")
    
    # 테스트 케이스 2: 전시 보고 술은 안 마실거야
    print("\n\n📝 테스트 2: 강남에서 전시 보고 술은 안 마실거야")
    print("-" * 80)
    
    result2 = await agent.plan_trip(
        user_input="강남에서 전시 보고 술은 안 마실거야",
        session_id="test_session_2",
        time_settings=TimeSettings(enabled=True, start_time="15:00", duration_hours=4)
    )
    
    print(f"\n상태: {result2['status']}")
    print("\n진행 메시지:")
    for msg in result2['progress']:
        print(f"  {msg}")
    
    if result2['status'] == 'completed':
        print(f"\n✅ 일정 생성 완료!")
        print(f"활동 장소: {len(result2['itinerary']['locations']['activities'])}개")
        print(f"식사 장소: {len(result2['itinerary']['locations']['dining'])}개")
        print(f"카페: {len(result2['itinerary']['locations']['cafes'])}개")
        print(f"술집: {len(result2['itinerary']['locations']['bars'])}개 (제외됨)")
    
    # 테스트 케이스 3: 밥만 먹고 싶어
    print("\n\n📝 테스트 3: 신촌에서 밥만 먹고 싶어. 놀거리랑 카페, 술집은 필요없어")
    print("-" * 80)
    
    result3 = await agent.plan_trip(
        user_input="신촌에서 밥만 먹고 싶어. 놀거리랑 카페, 술집은 필요없어",
        session_id="test_session_3",
        time_settings=TimeSettings(enabled=False)
    )
    
    print(f"\n상태: {result3['status']}")
    print("\n진행 메시지:")
    for msg in result3['progress']:
        print(f"  {msg}")
    
    if result3['status'] == 'completed':
        print(f"\n✅ 일정 생성 완료!")
        print(f"활동 장소: {len(result3['itinerary']['locations']['activities'])}개 (제외됨)")
        print(f"식사 장소: {len(result3['itinerary']['locations']['dining'])}개")
        print(f"카페: {len(result3['itinerary']['locations']['cafes'])}개 (제외됨)")
        print(f"술집: {len(result3['itinerary']['locations']['bars'])}개 (제외됨)")
    
    # 테스트 케이스 4: 방탈출 + 양식
    print("\n\n📝 테스트 4: 홍대에서 방탈출하고 양식 먹을래")
    print("-" * 80)
    
    result4 = await agent.plan_trip(
        user_input="홍대에서 방탈출하고 양식 먹을래",
        session_id="test_session_4",
        time_settings=TimeSettings(enabled=True, start_time="18:00", duration_hours=3)
    )
    
    print(f"\n상태: {result4['status']}")
    print("\n진행 메시지:")
    for msg in result4['progress']:
        print(f"  {msg}")
    
    if result4['status'] == 'completed':
        print(f"\n✅ 일정 생성 완료!")
        print(f"활동 장소: {len(result4['itinerary']['locations']['activities'])}개")
        print(f"식사 장소: {len(result4['itinerary']['locations']['dining'])}개")
        
        print("\n📋 최종 일정:")
        for item in result4['itinerary']['schedule']:
            print(f"  {item['order']}. {item['location']['name']}")
            if item.get('start_time'):
                print(f"     ⏰ {item['start_time']} - {item['end_time']}")
    
    # 테스트 케이스 5: 특정 장소 + 선호도
    print("\n\n📝 테스트 5: 롯데월드 갔다가 한식 먹을래")
    print("-" * 80)
    
    result5 = await agent.plan_trip(
        user_input="롯데월드 갔다가 한식 먹을래",
        session_id="test_session_5",
        time_settings=TimeSettings(enabled=True, start_time="11:00", duration_hours=8)
    )
    
    print(f"\n상태: {result5['status']}")
    print("\n진행 메시지:")
    for msg in result5['progress']:
        print(f"  {msg}")
    
    if result5['status'] == 'completed' or result5['status'] == 'awaiting_user_input':
        print(f"\n✅ 테스트 완료 (상태: {result5['status']})")

    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_natural_language_planning())
