
# --- 설정 ---
WEBHOOK_URLS = ['',]
MY_INFO = {
    0: {
        'name': '',
        'webhook': '',
        'types': 0,
        'genai_key':'' ,
        'is_active': True,
        'stock_type': 0
    }
}

# 감시 종목 및 목표가 (티커: [이름, 목표가격])
WATCHLIST = {
    0: ['005930','삼성전자', 200000,0.0,0,0.0,0,0.0,0],
    1: ['005930','삼성전자', 200000,0.0,0,0.0,0,0.0,0],
    2: ['005930','삼성전자', 200000,0.0,0,0.0,0,0.0,0],
    3: ['005930','삼성전자', 200000,0.0,0,0.0,0,0.0,0],
    4: ['005930','삼성전자', 200000,0.0,0,0.0,0,0.0,0],
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
            "stock_type": result[6],
        }
    }
    global MY_INFO
    MY_INFO =  new_dict

def update_webhook(user_id=None, name=None, webhook=None, genai_key=None, types=None, is_active=None, stock_type=None):
    global MY_INFO

    user_id = list(MY_INFO.keys())[0] if not user_id else user_id
    name = MY_INFO[user_id]['name'] if not name else name
    webhook = MY_INFO[user_id]['webhook'] if not webhook else webhook
    genai_key = MY_INFO[user_id]['genai_key'] if not genai_key else genai_key
    types = MY_INFO[user_id]['types'] if not types else types
    is_active = MY_INFO[user_id]['is_active'] if not is_active else is_active
    stock_type = MY_INFO[user_id]['stock_type'] if not stock_type else stock_type

    new_dict = {
        user_id: {
            "name": name,
            "webhook": webhook,
            "genai_key": genai_key,
            "types": types,
            "is_active": is_active,
            "stock_type": stock_type,
        }
    }
    MY_INFO = new_dict

def get_webhook():
    global MY_INFO
    return MY_INFO

def set_cur_user(user_id):
    global CUR_USER_ID
    CUR_USER_ID = user_id