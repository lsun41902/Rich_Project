import database.connection_SQL as sql_db
import sqlite3

# 주식 시장 버전 정보
def select_stock_ver():
    try:
        with sql_db.get_connection() as conn:
            with conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM ticker_ver")
                result = cur.fetchone()
                cur.close()
                return result
    except Exception as e:
        sql_db.print_error(f"기본 주식 목록 인덱스 생성 실패:{e}")
        return []

# db 버전 확인
def select_db_ver():
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS db_ver (ver INTEGER NOT NULL)")
                cur.execute("SELECT ver FROM db_ver LIMIT 1")
                result = cur.fetchone()
                cur.close()
                return result[0] if result else 0
    except Exception as e:
        sql_db.print_error(f"버전 정보 얻기 실패: {e}")
        return 0

# 주식 코드 전체 가져오기
def select_default_ticker_list(stock_type):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                if stock_type == 0:
                    query = f"SELECT short_code FROM default_tickers"
                else:
                    query = f"SELECT symbol FROM default_tickers_US"
                cur.execute(query)
                result = cur.fetchall()
                cur.close()
                return result
    except Exception as e:
        sql_db.print_error(f"기본 주식 목록 인덱스 생성 실패:{e}")
        return []


# 기본 정보 유저의 위시리스트 가져오기
def select_user_ticker_list(user_id):
    import config
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, ticker_code, ticker_name, target_price, target_price_us, buy_price, buy_price_us, amount, dollar_price, market_type FROM tickers WHERE user_id = ? ORDER BY id",
                    (user_id,)
                )
                results = cur.fetchall()
                cur.close()
                new_dict = {row[0]: list(row[1:10]) for row in results}
                config.set_watch_list(new_dict)
                return new_dict
    except Exception as e:
        sql_db.print_error(f"종목 삭제 실패:{e}")
        return []

# input을 포함한 주식 검색
def select_like_default_ticker_list(input):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                query = "SELECT short_code, short_name_ko, 0 as market_type FROM default_tickers WHERE short_code LIKE ? OR short_name_ko LIKE ? LIMIT 50"
                cur.execute(query, (f"%{input}%", f"%{input}%"))
                result = cur.fetchall()
                cur.close()
                return result
    except Exception as e:
        sql_db.print_error(f"한국 주식 조회 실패:{e}")
        return []

# input을 포함한 주식 검색
def select_like_default_ticker_us_list(input):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                query = "SELECT symbol, name_en, 1 as market_type FROM default_tickers_US WHERE symbol LIKE ? OR name_en LIKE ? OR name_ko LIKE ? LIMIT 50"
                search_param = f"%{input}%"
                cur.execute(query, (search_param, search_param, search_param))
                result = cur.fetchall()
                cur.close()
                return result
    except Exception as e:
        sql_db.print_error(f"미국 주식 조회 실패:{e}")
        return []

# 기본 웹훅 정보 가져오기
def select_user_webhook():
    import config
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users")
                result = cur.fetchone()
                cur.close()
                config.set_webhook(result)
    except Exception as e:
        sql_db.print_error(f"사용자 webhook 가져외 실패: {e}")


# 유저 마켓 타입 가져오기
def select_user_market_type():
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT market_type FROM users")
                result = cur.fetchone()
                cur.close()
                return result[0]
    except Exception as e:
        sql_db.print_error(f"사용자 ID 조회 실패: {e}")
        return 0

# 유저 번호
def select_user_id():
    import config
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT cur_user_id FROM configs")
                result = cur.fetchone()
                cur.close()
                config.set_cur_user(result[0])
                return result[0] if result else 0
    except Exception as e:
        sql_db.print_error(f"user_id 가져오기 실패: {e}")