import os
import sqlite3
import config
import sys
import shutil
import pandas as pd

DB_NAME = "rich_db.sqlite"
CSV_PATH = "data/data_0322_20260313.csv" # 배포 시 resource_path로 감싸야 함


def check_and_update_db():
    conn = get_connection()

    # 1. DB의 최신 데이터 날짜 확인
    last_date = pd.read_sql("SELECT MAX(listing_date) FROM default_tickers", conn).iloc[0, 0]

    # 2. 오늘 날짜와 비교 (예: 오늘이 2026-03-13이면 업데이트 체크)
    # 업데이트가 필요하다고 판단되면:
    if need_update(last_date):
        print("최신 데이터를 확인합니다...")

        # 3. 직접 다운로드 시도 (FinanceDataReader 대신 직접 요청)
        url = "http://data.krx.co.kr/comm/bldAtt/getJsonDownload.cmd"
        # ... 여기에 KRX에서 제공하는 다운로드 파라미터를 설정하여 요청 ...
        # requests.post(url, data=params)

        # 4. 새 데이터가 들어오면 기존 테이블 갱신 (REPLACE 활용)
        # df.to_sql('default_tickers', conn, if_exists='replace', index=False)
        print("데이터 업데이트 완료!")

    conn.close()

def init_db_from_csv():
    try:
        with get_connection() as conn:
            with conn:
                cursor = conn.cursor()
                # 2. 데이터 유무 확인
                cursor.execute("SELECT count(*) FROM default_tickers")
                if cursor.fetchone()[0] == 0:
                    print("데이터베이스가 비어 있습니다. CSV에서 데이터를 로드합니다...")

                    # 3. CSV 읽기 (실행 파일 경로 대응)
                    # 배포 시에는 resource_path() 함수를 사용하여 경로를 가져오세요
                    target_csv = resource_path(CSV_PATH)
                    if os.path.exists(target_csv):
                        df = pd.read_csv(target_csv,encoding='cp949')
                        file_name = os.path.basename(target_csv)
                        rename_map = {
                            '표준코드': 'std_code',
                            '단축코드': 'short_code',
                            '한글 종목명': 'name_ko',
                            '한글 종목약명': 'short_name_ko',
                            '영문 종목명': 'name_en',
                            '상장일': 'listing_date',
                            '시장구분': 'market_type',
                            '증권구분': 'security_type',
                            '소속부': 'dept_type',
                            '주식종류': 'stock_type',
                            '액면가': 'face_value',
                            '상장주식수': 'total_shares'
                        }
                        df = df.rename(columns=rename_map)
                        cols_to_use = list(rename_map.values())
                        df = df[cols_to_use]

                        df.to_sql('default_tickers', conn, if_exists='append', index=False)
                        sql = """INSERT OR REPLACE INTO ticker_ver (ver) VALUES (?)"""
                        cursor.execute(sql, (file_name,))
                        return True
                        print("데이터 로드 완료!")
                    else:
                        print(f"경로에 CSV 파일이 없습니다: {target_csv}")
                        return False
                else:
                    return True
    except Exception as e:
        print_error(f"주식목록 가져오기 에러:{e}")
        return False

def get_connection():
    # 1. 유저의 로컬 데이터 폴더 경로 설정 (Windows 기준)
    app_data_path = os.path.join(os.environ['APPDATA'], "RichProject")

    # 2. 폴더가 없으면 생성
    if not os.path.exists(app_data_path):
        os.makedirs(app_data_path)

    # 3. 사용할 실제 DB 경로
    db_path = os.path.join(app_data_path, DB_NAME)

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
        if (init_db_from_csv()):
            create_index_default_ticker()
        current_user = get_user_id()
        get_user_ticker_list(current_user)
        set_user_webhook()
        print_ok("모든 DB 설정이 완료되었습니다.")
    except Exception as e:
        print_error(f"setup 오류 발생: {e}")

def get_default_ticker_list():
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT short_code,short_name_ko FROM default_tickers")
                result = cur.fetchall()
                cur.close()
                return result
    except Exception as e:
        print_error(f"기본 주식 목록 인덱스 생성 실패:{e}")
        return []

def get_like_default_ticker_list(input):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                query = "SELECT short_code, short_name_ko, market_type FROM default_tickers WHERE short_code LIKE ? OR short_name_ko LIKE ? LIMIT 50"
                cur.execute(query, (f"%{input}%", f"%{input}%"))
                result = cur.fetchall()
                cur.close()
                return result
    except Exception as e:
        print_error(f"기본 주식 목록 인덱스 생성 실패:{e}")
        return []

def create_index_default_ticker():
    try:
        with get_connection() as conn:
            with conn:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_name_ko ON default_tickers(short_name_ko)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_std_code ON default_tickers(short_code)")
                print_ok("기본 주식 목록 인덱스 생성 성공")
    except Exception as e:
        print_error(f"기본 주식 목록 인덱스 생성 실패:{e}")

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
                cur.execute("INSERT OR REPLACE INTO db_ver (ver) VALUES (?)", (new_ver,))
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
        return []


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

