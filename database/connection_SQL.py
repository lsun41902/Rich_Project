import os
import sqlite3
import config
import sys
import shutil

def get_connection():
    # 1. 유저의 로컬 데이터 폴더 경로 설정 (Windows 기준)
    app_data_path = os.path.join(os.environ['APPDATA'], "RichProject")

    # 2. 폴더가 없으면 생성
    if not os.path.exists(app_data_path):
        os.makedirs(app_data_path)

    # 3. 사용할 실제 DB 경로
    db_path = os.path.join(app_data_path, "rich_db.sqlite")

    # 4. DB 파일이 없으면(첫 실행 시), 내장된 초기 DB를 복사해옴
    if not os.path.exists(db_path):
        # 실행 파일 안에 포함된 템플릿 DB 경로 (resource_path 사용)
        template_db = resource_path("rich_db")
        if os.path.exists(template_db):
            shutil.copy(template_db, db_path)

    # 5. 이제 항상 내장 파일이 아닌 '유저 개인 폴더'의 파일을 연결함
    return sqlite3.connect(db_path)

def setup_database():
    try:
        current_ver = get_db_ver()

        cur_db_ver = 1

        if current_ver == 0:
            run_sql_file("sqlver_1.sql")
            update_version_record(1)
        elif current_ver < cur_db_ver:
            run_sql_file("sqlver_3.sql")
            update_version_record(cur_db_ver)
        current_user = get_user_id()
        get_user_ticker_list(current_user)
        set_user_webhook()
        print_ok("모든 DB 설정이 완료되었습니다.")
    except Exception as e:
        print_error(f"setup 오류 발생: {e}")


def get_user_market_type():
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT market_type FROM users")
                result = cur.fetchone()
                cur.close()
                return result[0]
    except Exception as e:
        print_error(f"사용자 ID 조회 실패: {e}")
        return 0


def set_user_webhook():
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users")
                result = cur.fetchone()
                cur.close()
                config.set_webhook(result)
    except Exception as e:
        print_error(f"사용자 webhook 가져외 실패: {e}")

def update_user_webhook(user_id, name, webhook, types, is_active, market_type):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET user_name = ?, webhook = ?, types = ?, is_active = ?, market_type = ? WHERE id = ?",(name, webhook, types, is_active,market_type, user_id))
                cur.close()
                new_dict = [user_id, name, webhook, types, is_active, market_type]
                config.set_webhook(new_dict)
                return True
    except Exception as e:
        print_error(f"사용자 ID 조회 실패: {e}")
        return False

def update_user_market_type(user_id, market_type):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET market_type = ? WHERE id = ?",(market_type ,user_id))
                cur.close()
                get_dict = config.get_webhook()
                get_dict[5] = market_type
                config.set_webhook(get_dict)
                return True
    except Exception as e:
        print_error(f"사용자 ID 조회 실패: {e}")
        return False

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def run_sql_file(sql_filename):
    sql_path = resource_path(os.path.join("queries", sql_filename))
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            full_sql = f.read()
        with get_connection() as conn:
            conn.executescript(full_sql)
            print_ok(f"{sql_filename} 실행 완료")
    except Exception as e:
        print_error(f"run_sql_file SQL 실행 실패: {e}")

def get_db_ver():
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS db_ver (ver INTEGER NOT NULL)")
                cur.execute("SELECT ver FROM db_ver LIMIT 1")
                result = cur.fetchone()
                cur.close()
                return result[0] if result else 0
    except Exception as e:
        print_error(f"버전 정보 얻기 실패: {e}")
        return 0

def update_version_record(new_ver):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM db_ver;")
                cur.execute("INSERT INTO db_ver (ver) VALUES (?)", (new_ver,))
                cur.close()
    except Exception as e:
        print_error(f"버전 정보 얻기 실패: {e}")

def get_user_id():
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT cur_user_id FROM configs")
                result = cur.fetchone()
                cur.close()
                config.set_cur_user(result[0])
                return result[0] if result else 0
    except Exception as e:
        print_error(f"user_id 가져오기 실패: {e}")

def insert_ticker_to_db(current_user, code, name, price):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO tickers (user_id, ticker_code, ticker_name, target_price) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (user_id, ticker_code) DO UPDATE 
                    SET ticker_name = EXCLUDED.ticker_name, 
                        target_price = EXCLUDED.target_price;
                """, (current_user, code, name, price))
                cur.close()
                print_ok(f"종목 추가 완료: {name}({code})")
                return True
    except Exception as e:
        print_error(f"종목 추가 실패:{e}")
        return False

def update_ticker_in_db(db_id, code, name, price):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE tickers SET ticker_code = ?, ticker_name = ?, target_price = ? WHERE id = ?
                """, (code, name, price,db_id))
                cur.close()
                print_ok(f"종목 업데이트 완료: {name}:{code}:{price}")
                return True
    except Exception as e:
        print_error(f"종목 업데이트 실패:{e}")
        return False

def delete_ticker_to_db(db_id):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                sql = "DELETE FROM tickers WHERE id = ?"
                cur.execute(sql, (db_id,))
                cur.close()
                print_ok(f"종목 삭제 완료:{db_id}")
                return True
    except Exception as e:
        print_error(f"종목 삭제 실패:{e}")
        return False

def get_user_ticker_list(user_id):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, ticker_code, ticker_name, target_price FROM tickers WHERE user_id = ? ORDER BY id",
                    (user_id,)
                )
                results = cur.fetchall()
                cur.close()
                new_dict = {ticker_id: [code, name, price] for ticker_id, code, name, price in results}
                config.set_watch_list(new_dict)
                return results
    except Exception as e:
        print_error(f"종목 삭제 실패:{e}")
        return False


def execute_many_transactions(query, data_list):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.executemany(query, data_list)
                cur.close()
                print_ok(f"기본 종목 {len(data_list)}개 추가 완료!")
    except Exception as e:
        print_error(f"execute_many_transactions SQL 실행 실패:{e}")

def print_error(msg):
    print(f"❌ {msg}")

def print_ok(msg):
    print(f"✅ {msg}")

