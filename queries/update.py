import database.connection_SQL as sql_db


def update_ticker_in_db(db_id, code, name, price, stock_type):
    try:
        target_col = "target_price" if stock_type == 0 else "target_price_us"
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                query = f"""
                UPDATE tickers SET 
                ticker_code  = ?, 
                ticker_name  = ?, 
                {target_col} = ? 
                WHERE id = ?"""
                param = (code, name, price, db_id)
                cur.execute(query, param)
                cur.close()
                sql_db.print_ok(f"종목 업데이트 완료: {name}:{code}:{price}")
                return True
    except Exception as e:
        sql_db.print_error(f"종목 업데이트 실패:{e}")
        return False


# 사용자 웹훅 주소 변경
def update_user_webhook(user_id, name, webhook, types, is_active, stock_type, genai_key):
    import services.ui_helper as helper
    en_key = helper.encrypt_key(genai_key)
    import config
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE users SET user_name = ?, webhook = ?, types = ?, is_active = ?, stock_type = ?, genai_key =? WHERE id = ?",
                    (name, webhook, types, is_active, stock_type, en_key, user_id))
                cur.close()
                new_dict = [user_id, name, webhook, genai_key, types, is_active, stock_type]
                config.set_webhook(new_dict)
                return True
    except Exception as e:
        sql_db.print_error(f"사용자 ID 조회 실패: {e}")
        return False


# 사용자 마켓 타입 변경
def update_user_market_type(user_id, stock_type):
    import config
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET stock_type = ? WHERE id = ?", (stock_type, user_id))
                cur.close()
                return True
    except Exception as e:
        sql_db.print_error(f"사용자 ID 조회 실패: {e}")
        return False


# DB 버전 업데이트
def update_version_record(new_ver):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM db_ver")

                # 2. 새로운 버전 하나만 딱 넣습니다.
                cur.execute("INSERT INTO db_ver (ver) VALUES (?)", (new_ver,))
                cur.close()
    except Exception as e:
        sql_db.print_error(f"버전 정보 얻기 실패: {e}")


# DB stock 버전 업데이트
def update_stock_version_us(new_ver):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("UPDATE ticker_ver SET us_ver =?", (new_ver,))
                cur.close()
    except Exception as e:
        sql_db.print_error(f"버전 정보 얻기 실패: {e}")
