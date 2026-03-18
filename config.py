
# --- 설정 ---
WEBHOOK_URLS = ['',]
MY_INFO = {
    0: {
        'name': '',
        'webhook': '',
        'types': 0,
        'is_active': True,
        'market_type': 0,
        'genai_key':''
    }
}

# 감시 종목 및 목표가 (티커: [이름, 목표가격])
WATCHLIST = {
    0: ['005930.KS','삼성전자', 200000],
    1: ['000660.KS','SK하이닉스', 1000000],
    2: ['035720.KS','카카오', 60000],
    3: ['086520.KQ','에코프로', 180000],
    4: ['247540.KQ','에코프로비엠', 230000],
}

# 상수 정의
TEN, FIVE, ONE = 60, 45, 30

CUR_USER_ID = 0

def set_watch_list(watch_list):
    global WATCHLIST  # 함수 밖의 WATCHLIST를 사용하겠다고 명시
    WATCHLIST = watch_list

def set_webhook(result):
    import services.ui_helper as helper
    encrypted_key = result[3]
    decrypted_key = helper.decrypt_key(encrypted_key)
    new_dict = {
        result[0]: {
            "name": result[1],
            "webhook": result[2],
            "genai_key": decrypted_key,
            "types": result[4],
            "is_active": result[5],
            "market_type": result[6],
        }
    }
    global MY_INFO
    MY_INFO =  new_dict

def get_webhook():
    global MY_INFO
    return MY_INFO

def set_cur_user(user_id):
    global CUR_USER_ID
    CUR_USER_ID = user_id