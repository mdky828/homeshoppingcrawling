import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
# main.py에서 Firebase Admin SDK를 초기화하므로, 여기서는 관련 임포트와 초기화 코드를 제거합니다.
# from firebase_admin import credentials, firestore # 이 줄들은 주석 처리하거나 제거하세요.
import firebase_admin
from firebase_admin import firestore # firestore 모듈만 임포트합니다.

# 채널 매핑 정보
channel_map = {
    '535773': 'LT', '590007': 'LTONE', '535775': 'GS', '535779': 'GSMY',
    '590003': '신세계', '590001': 'KT', '600003': 'KT+',
    '535778': '홈앤', '600004': 'SK', '535777': 'NS', '590008': 'NS+',
    '580002': '쇼핑엔', '535774': 'CJ', '590006': 'CJ+',
    '535776': 'HD', '590005': 'HD+', '580001': '공영', '590002': 'W홈'
}
live_channels = ['LT', 'GS', '홈앤', '공영', 'NS', 'CJ', 'HD']


def get_channel_name(code):
    """채널 코드를 채널 이름으로 변환합니다."""
    return channel_map.get(code, "알 수 없는 채널")


def get_channel_type(name):
    """채널 이름으로 라이브 방송 여부를 판단합니다."""
    return "라이브" if name in live_channels else "녹화방송"


def get_day_of_week(date_str):
    """YYYYMMDD 형식의 날짜 문자열을 요일 문자열로 변환합니다."""
    date = datetime.strptime(date_str, '%Y%m%d')
    week_days = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
    return week_days[date.weekday()]


def create_unique_key(schedule):
    """스케줄 정보를 기반으로 고유 키를 생성합니다."""
    # 날짜, 요일, 채널, 방송 타입, 카테고리, 시간, 상품명, 링크를 포함하여 고유성을 확보합니다.
    key_str = '|'.join(map(str, schedule))
    return hashlib.md5(key_str.encode()).hexdigest()


def crawl_schedule(date, category_code, category_text, only_live=False):
    """
    주어진 날짜와 카테고리 코드로 홈쇼핑 스케줄을 크롤링합니다.
    Args:
        date (str): 크롤링할 날짜 (YYYYMMDD 형식).
        category_code (str): 크롤링할 카테고리 코드.
        category_text (str): 크롤링할 카테고리 텍스트.
        only_live (bool): 라이브 방송만 수집할지 여부.
    Returns:
        list: 수집된 스케줄 정보 리스트.
    """
    url = f"https://m.livehs.co.kr/schedule?date={date}&category_code={category_code}&list_type=list"
    schedules = []
    unique_keys = set() # 중복 방지를 위해 set 사용

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] HTTP 요청 실패: {url}, 오류: {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    items = soup.select("li.schedule-product")

    for item in items:
        try:
            time_text = item.select_one(".date").get_text(strip=True)
            channel_logo = item.select_one(".sprite-site-logo-s")
            if not channel_logo:
                # 채널 로고가 없으면 유효한 항목이 아닐 수 있으므로 건너뜁니다.
                continue
            
            # 클래스 이름에서 채널 코드를 추출합니다. 예: sprite-site-logo-s-535773
            classes = channel_logo.get("class", [])
            channel_code = None
            for cls in classes:
                if cls.startswith("sprite-site-logo-s-"):
                    channel_code = cls.split("-")[-1]
                    break
            
            if not channel_code:
                print(f"[WARN] 채널 코드를 찾을 수 없습니다: {classes}")
                continue

            channel = get_channel_name(channel_code)
            channel_type = get_channel_type(channel)
            product = item.select_one(".title").get_text(strip=True)
            
            link_tag = item.select_one("a")
            link = "https://m.livehs.co.kr" + link_tag.get("href") if link_tag else ""

            if only_live and channel_type != "라이브":
                continue

            # 스케줄 데이터를 리스트로 구성
            schedule_data = [date, get_day_of_week(date), channel, channel_type, category_text, time_text, product, link]
            unique_key = create_unique_key(schedule_data)

            if unique_key not in unique_keys:
                unique_keys.add(unique_key)
                schedules.append(schedule_data)

        except Exception as e:
            # 특정 항목 처리 중 발생한 오류를 기록하고 다음 항목으로 넘어갑니다.
            print(f"[WARN] 항목 처리 오류 발생 (URL: {url}): {e}")
            continue

    return schedules


def save_to_firestore(run_id, schedules):
    """
    수집된 스케줄 데이터를 Firestore에 저장합니다.
    Args:
        run_id (str): 현재 크롤링 실행을 식별하는 고유 ID.
        schedules (list): 저장할 스케줄 데이터 리스트.
    """
    # main.py에서 firebase_admin.initialize_app(cred)가 호출되었음을 가정합니다.
    # 따라서 firestore.client()는 이미 초기화된 앱의 클라이언트를 반환합니다.
    db = firestore.client() 
    
    batch = db.batch()
    run_ref = db.collection("runs").document(run_id)

    # 실행 메타데이터 저장
    run_ref.set({"run_time": datetime.now().isoformat(), "total": len(schedules)})

    # 세부 데이터 저장
    for idx, s in enumerate(schedules):
        doc_ref = run_ref.collection("items").document(str(idx))
        batch.set(doc_ref, {
            "date": s[0],
            "day": s[1],
            "channel": s[2],
            "channel_type": s[3],
            "category": s[4],
            "time": s[5],
            "product": s[6],
            "product_link": s[7]
        })
    batch.commit()
    print(f"[INFO] Firestore 저장 완료: {len(schedules)}건 (Run ID: {run_id})")
