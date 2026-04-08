import os
import sqlite3
import sys
import pandas as pd

DB_NAME = "rich_db.sqlite"
CSV_PATH = "data/data_0322_20260313.csv" # 배포 시 resource_path로 감싸야 함

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
                            '시장구분': 'stock_name',
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

    # DB 연결 (없으면 생성됨)
    conn = sqlite3.connect(db_path)
    return conn

def setup_database():
    try:
        import queries.select as select_db
        import queries.update as update_db
        user_db_ver = select_db.select_db_ver()

        cur_db_ver = 3

        if user_db_ver == 0:
            ver_1("sqlver_1.sql")
            update_db.update_version_record(cur_db_ver)
        elif user_db_ver < cur_db_ver:
            ver_2()
            ver_3("sqlver_3.sql")
            update_db.update_version_record(cur_db_ver)

        if init_db_from_csv():
            create_index_default_ticker()

        current_user = select_db.select_user_id()
        select_db.select_user_ticker_list(current_user)
        select_db.select_user_webhook()
        print_ok("모든 DB 설정이 완료되었습니다.")
        return True
    except Exception as e:
        print_error(f"setup 오류 발생: {e}")
        return False

def ver_2():
    import queries.alter as alter_db
    alter_db.migrate_user_table("users","genai_key","users_new")

def ver_3(sql_filename):
    import queries.alter as alter_db
    sql_path = resource_path(os.path.join("queries", sql_filename))
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            full_sql = f.read()
        with get_connection() as conn:
            conn.executescript(full_sql)
            print_ok(f"{sql_filename} ver3 실행 완료")
    except Exception as e:
        print_error(f"ver_3 SQL 실행 실패: {e}")

    alter_db.migrate_tickers_table("tickers","buy_price","tickers_new")

def create_index_default_ticker():
    try:
        with get_connection() as conn:
            with conn:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_name_ko ON default_tickers(short_name_ko)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_std_code ON default_tickers(short_code)")
                print_ok("기본 주식 목록 인덱스 생성 성공")
    except Exception as e:
        print_error(f"기본 주식 목록 인덱스 생성 실패:{e}")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def ver_1(sql_filename):
    sql_path = resource_path(os.path.join("queries", sql_filename))
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            full_sql = f.read()
        with get_connection() as conn:
            conn.executescript(full_sql)
            print_ok(f"{sql_filename} 실행 완료")
    except Exception as e:
        print_error(f"ver_1 SQL 실행 실패: {e}")

def execute_many_transactions(query, data_list):
    try:
        with get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.executemany(query, data_list)
                cur.close()
    except Exception as e:
        print_error(f"execute_many_transactions SQL 실행 실패:{e}")

def print_error(msg):
    print(f"[ERROR] {msg}")

def print_ok(msg):
    print(f"[OK] {msg}")



