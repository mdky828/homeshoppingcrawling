import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import secretmanager_v1beta1 as secretmanager # Secret Manager 클라이언트 임포트
from datetime import datetime, timedelta
from crawler import crawl_schedule, save_to_firestore # crawler.py의 함수들을 임포트합니다.

# --- Secret Manager에서 Firebase 키 로드 시작 ---
# Secret Manager 클라이언트 초기화
client = secretmanager.SecretManagerServiceClient()

# 환경 변수에서 비밀 리소스 경로 가져오기
secret_resource_name = os.environ.get("FIREBASE_KEY_JSON")

# Firebase Admin SDK 초기화 시 사용할 db 객체 선언
db = None

if secret_resource_name:
    try:
        # Secret Manager에서 비밀 값 가져오기
        response = client.access_secret_version(name=secret_resource_name)
        firebase_key_json_string = response.payload.data.decode("UTF-8")
        firebase_config = json.loads(firebase_key_json_string)

        # Firebase 초기화
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
        db = firestore.client() # 초기화된 Firestore 클라이언트 할당
        print("[INFO] Firebase Admin SDK가 Secret Manager의 키로 성공적으로 초기화되었습니다.")

    except Exception as e:
        print(f"[ERROR] Secret Manager에서 Firebase 키를 로드하는 데 실패했습니다: {e}")
        exit(1) # 초기화 실패 시 애플리케이션 종료
else:
    print("[ERROR] FIREBASE_KEY_JSON 환경 변수가 설정되지 않았습니다. Firebase 초기화에 실패했습니다.")
    exit(1) # 환경 변수 누락 시 애플리케이션 종료
# --- Secret Manager에서 Firebase 키 로드 끝 ---


def main():
    if not db: # db 객체가 초기화되지 않았다면 실행 중단
        print("[ERROR] Firestore client is not initialized. Exiting.")
        return

    category_mapping = {
        "1": ("H10", "렌탈"),
        "2": ("H03", "리빙"),
        "3": ("H09", "여행"),
        "4": ("H01", "여성패션"),
        "5": ("H11", "남성패션"),
        "6": ("H12", "언더웨어"),
        "7": ("H13", "명품")
    }

    today = datetime.now()
    # 어제부터 7일 후까지의 날짜를 생성합니다. (총 9일)
    dates = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 8)]
    all_schedules = []

    print(f"[INFO] 크롤링 시작. 대상 날짜: {dates[0]} ~ {dates[-1]}")

    for key, (code, text) in category_mapping.items():
        print(f"[INFO] 카테고리: {text} ({code}) 처리 중...")
        for date in dates:
            print(f"[INFO] 날짜: {date} 크롤링...")
            schedules = crawl_schedule(date, code, text) # crawler.py의 함수 호출
            all_schedules.extend(schedules)
            print(f"[INFO] {date} - {text} 에서 {len(schedules)}건의 스케줄 수집.")

    run_id = datetime.now().strftime("%Y%m%d%H%M%S") # 현재 시간으로 run_id 생성
    print(f"[INFO] 총 {len(all_schedules)}건의 스케줄 수집 완료. Firestore에 저장 시작. run_id: {run_id}")

    # save_to_firestore 함수에 db 객체를 인자로 전달하는 경우
    # save_to_firestore(db, run_id, all_schedules)
    # 현재 코드 구조에서는 crawler.py에서 `firestore.client()`를 다시 호출하여
    # 이미 초기화된 앱의 클라이언트를 얻는 방식이므로, db를 인자로 전달하지 않아도 됩니다.
    save_to_firestore(run_id, all_schedules) # crawler.py의 함수 호출

    print(f"[INFO] 모든 작업 완료.")

if __name__ == "__main__":
    main()

