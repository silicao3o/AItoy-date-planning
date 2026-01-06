import asyncio
import os
from dotenv import load_dotenv
from src.kakao_client import KakaoMapClient

load_dotenv()


async def test_boardgame_cafe_search():
    """보드게임카페 검색 테스트"""
    
    print("=" * 60)
    print("🎲 보드게임카페 검색 테스트")
    print("=" * 60)
    
    client = KakaoMapClient()
    
    # 테스트 케이스 1: 키워드 검색 (홍대 보드게임카페)
    print("\n[테스트 1] 키워드 검색: '홍대 보드게임카페'")
    print("-" * 60)
    
    try:
        results = await client.search_nearby_by_keyword(
            keyword="홍대 보드게임카페",
            x=126.9244,  # 홍대입구역 좌표
            y=37.5563,
            radius=1000,
            size=5
        )
        
        if results:
            print(f"✅ 검색 결과: {len(results)}개 발견\n")
            for i, place in enumerate(results, 1):
                print(f"{i}. {place.name}")
                print(f"   📍 주소: {place.address}")
                print(f"   🏷️  카테고리: {place.category}")
                print(f"   📞 전화: {place.phone or 'N/A'}")
                if place.distance:
                    print(f"   📏 거리: {place.distance}m")
                print()
        else:
            print("❌ 검색 결과 없음")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    # 테스트 케이스 2: 카테고리 검색 (카페 카테고리로 검색 후 필터링)
    print("\n[테스트 2] 카테고리 검색: CE7 (카페) - '보드게임' 키워드 포함")
    print("-" * 60)
    
    try:
        results = await client.search_by_category(
            category_code="CE7",
            x=126.9244,
            y=37.5563,
            radius=1000,
            size=15
        )
        
        # '보드게임' 키워드가 포함된 카페만 필터링
        boardgame_cafes = [
            place for place in results 
            if "보드게임" in place.name or "보드" in place.name
        ]
        
        if boardgame_cafes:
            print(f"✅ 필터링 결과: {len(boardgame_cafes)}개 발견\n")
            for i, place in enumerate(boardgame_cafes, 1):
                print(f"{i}. {place.name}")
                print(f"   📍 주소: {place.address}")
                print(f"   🏷️  카테고리: {place.category}")
                print(f"   📞 전화: {place.phone or 'N/A'}")
                if place.distance:
                    print(f"   📏 거리: {place.distance}m")
                print()
        else:
            print("❌ '보드게임' 키워드를 포함한 카페 없음")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    # 테스트 케이스 3: find_activity_places 메서드 사용 (activity 테마)
    print("\n[테스트 3] find_activity_places 메서드: 'activity' 테마")
    print("-" * 60)
    
    try:
        results = await client.find_activity_places(
            location_name="홍대 보드게임카페",
            theme="activity",
            radius=1500,
            size=5
        )
        
        if results:
            print(f"✅ 검색 결과: {len(results)}개 발견\n")
            for i, place in enumerate(results, 1):
                print(f"{i}. {place.name}")
                print(f"   📍 주소: {place.address}")
                print(f"   🏷️  카테고리: {place.category}")
                print(f"   📞 전화: {place.phone or 'N/A'}")
                print()
        else:
            print("❌ 검색 결과 없음")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    # 테스트 케이스 4: 다양한 지역에서 검색
    print("\n[테스트 4] 다양한 지역 검색")
    print("-" * 60)
    
    locations = [
        ("강남역", 127.0276, 37.4979),
        ("신촌", 126.9368, 37.5559),
        ("건대입구", 127.0698, 37.5403)
    ]
    
    for location_name, x, y in locations:
        try:
            results = await client.search_nearby_by_keyword(
                keyword=f"{location_name} 보드게임카페",
                x=x,
                y=y,
                radius=800,
                size=3
            )
            
            print(f"\n📍 {location_name}: {len(results)}개 발견")
            for place in results:
                print(f"   - {place.name}")
        except Exception as e:
            print(f"   ❌ {location_name} 검색 실패: {e}")
    
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_boardgame_cafe_search())
