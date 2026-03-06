# --- 설정 ---
WEBHOOK_URLS = ['',]
MY_INFO = {0:['','',0,True]}

# 감시 종목 및 목표가 (티커: [이름, 목표가격])
WATCHLIST = {
    0: ['005930.KS','삼성전자', 200000],
    1: ['000660.KS','SK하이닉스', 1000000],
    2: ['035720.KS','카카오', 60000],
    3: ['086520.KQ','에코프로', 180000],
    4: ['247540.KQ','에코프로비엠', 230000],
}

# 상수 정의
TEN, FIVE, ONE = 10, 5, 1

CUR_USER_ID = 0

def set_watch_list(watch_list):
    global WATCHLIST  # 함수 밖의 WATCHLIST를 사용하겠다고 명시
    WATCHLIST = watch_list

def set_webhook(webhook):
    global MY_INFO
    MY_INFO =  webhook

def set_cur_user(user_id):
    global CUR_USER_ID
    CUR_USER_ID = user_id