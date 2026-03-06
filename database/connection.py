import psycopg2
from psycopg2 import sql
import os

import config

CUR_DB_VER = 1
_db_conn = None
target_db = "rich_db"
current_user = 0

def get_connection(db_name="postgres"):
    global _db_conn
    # 연결이 없거나 닫혀있으면 새로 연결
    if _db_conn is None or _db_conn.closed:
        _db_conn = connect_db(db_name)
    return _db_conn

def connect_db(db_name):
    """연결 로직을 공통 함수로 분리"""
    return psycopg2.connect(
        host="localhost",
        user="postgres",
        password="1234",
        port="5432",
        database=db_name
    )


def setup_database():
    try:
        # 1단계: postgres DB에 접속해서 rich_db 생성 확인
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (target_db,))
        if not cur.fetchone():
            print(f"🚀 '{target_db}' 생성 중...")
            cur.execute(f"CREATE DATABASE {target_db}")

        cur.close()
        conn.close()

        # 2단계: 버전 확인
        current_ver = get_db_ver()

        if current_ver == 0:  # 아예 새 DB인 경우
            run_sql_file("ver_1.sql")
            update_version_record(1)
        elif current_ver < CUR_DB_VER:
            # update_db 로직 실행
            run_sql_file("ver_3.sql")
            update_version_record(CUR_DB_VER)

        # 3단계: 마지막 사용한 유저 정보를 읽어오기
        current_user = get_user_id()
        get_user_ticker_list(current_user)
        get_user_webhook()



        print("✅ 모든 DB 설정이 완료되었습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def get_user_webhook():
    conn = get_connection(target_db)

    try:
        # 1. 커서를 생성해야 execute를 사용할 수 있습니다.
        with conn.cursor() as cur:
            # 2. tickers가 아닌 users 테이블에서 첫 번째 사용자를 찾는 것이 더 정확합니다.
            cur.execute("SELECT * FROM users")
            result = cur.fetchone()

            new_dict = {result[0]: [result[1], result[2], result[3], result[4]]}
            config.set_webhook(new_dict)
            # 결과가 있으면 id 반환, 없으면 0 반환
    except Exception as e:
        print(f"❌ 사용자 ID 조회 실패: {e}")

def update_user_webhook(user_id, name, webhook, types, is_active):
    conn = get_connection(target_db)

    try:
        # 1. 커서를 생성해야 execute를 사용할 수 있습니다.
        with conn:  # with conn을 써야 자동으로 commit이 됩니다.
            with conn.cursor() as cur:
                # 2. tickers가 아닌 users 테이블에서 첫 번째 사용자를 찾는 것이 더 정확합니다.
                cur.execute("UPDATE users SET user_name = %s, webhook = %s, types = %s, is_active = %s WHERE id = %s",(name, webhook, types, is_active, user_id))
                new_dict = {user_id: [name, webhook, types, is_active]}
                config.set_webhook(new_dict)
                return True
            # 결과가 있으면 id 반환, 없으면 0 반환
    except Exception as e:
        print(f"❌ 사용자 ID 조회 실패: {e}")
        return False

def run_sql_file(sql_filename):
    _db_conn = get_connection(target_db)
    """SQL 파일을 읽어 통째로 실행"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    # 경로 수정: main.py 위치에 맞춰 조정하세요
    sql_path = os.path.join(base_path, "..", "queries", sql_filename)

    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            full_sql = f.read()

        with _db_conn:
            with _db_conn.cursor() as cur:
                cur.execute(full_sql) # 통째로 실행
                print(f"✅ {sql_filename} 실행 완료")
    except Exception as e:
        print(f"❌ run_sql_file SQL 실행 실패: {e}")

def get_db_ver():
    _db_conn = get_connection(target_db)

    """현재 버전을 확인하고, 테이블이 없으면 0을 반환"""
    with _db_conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS db_ver (ver INTEGER NOT NULL);
        """)
        cur.execute("SELECT ver FROM db_ver LIMIT 1")
        result = cur.fetchone()
        return result[0] if result else 0



def update_version_record(new_ver):
    _db_conn = get_connection(target_db)

    with _db_conn:
        with _db_conn.cursor() as cur:
            cur.execute("DELETE FROM db_ver;")
            cur.execute("INSERT INTO db_ver (ver) VALUES (%s)", (new_ver,))

def get_user_id():
    conn = get_connection(target_db)

    try:
        # 1. 커서를 생성해야 execute를 사용할 수 있습니다.
        with conn.cursor() as cur:
            # 2. tickers가 아닌 users 테이블에서 첫 번째 사용자를 찾는 것이 더 정확합니다.
            cur.execute("SELECT cur_user_id FROM configs")
            result = cur.fetchone()
            config.set_cur_user(result[0])
            # 결과가 있으면 id 반환, 없으면 0 반환
            return result[0] if result else 0
    except Exception as e:
        print(f"❌ 사용자 ID 조회 실패: {e}")
        return 0

def insert_ticker_to_db(current_user, code, name, price):
    conn = get_connection(target_db)

    try:
        # 1. 데이터 삽입 및 트랜잭션 완료
        with conn: # with conn을 써야 자동으로 commit이 됩니다.
            with conn.cursor() as cur:
                # 올바른 INSERT 문법
                cur.execute("""
                    INSERT INTO tickers (user_id, ticker_code, ticker_name, target_price) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, ticker_code) DO UPDATE 
                    SET ticker_name = EXCLUDED.ticker_name, 
                        target_price = EXCLUDED.target_price;
                """, (current_user, code, name, price))

        print(f"✅ 종목 추가 완료: {name}({code})")

        # 2. 최신 리스트를 다시 조회해서 반환 (refresh용)
        # 기존에 만든 get_user_ticker_list 함수를 재사용하는 것이 효율적입니다.
        return True

    except Exception as e:
        print(f"❌ 종목 추가 실패: {e}")
        return False

def update_ticker_in_db(db_id, code, name, price):
    conn = get_connection(target_db)

    try:
        # 1. 데이터 삽입 및 트랜잭션 완료
        with conn: # with conn을 써야 자동으로 commit이 됩니다.
            with conn.cursor() as cur:
                # 올바른 INSERT 문법
                cur.execute("""
                    UPDATE tickers SET ticker_code = %s, ticker_name = %s, target_price = %s WHERE id = %s
                """, (code, name, price,db_id))

        print(f"✅ 종목 업데이트 완료: {name}:{code}:{price}")

        # 2. 최신 리스트를 다시 조회해서 반환 (refresh용)
        # 기존에 만든 get_user_ticker_list 함수를 재사용하는 것이 효율적입니다.
        return True

    except Exception as e:
        print(f"❌ 종목 업데이트 실패: {e}")
        return False

def delete_ticker_to_db(db_id):
    conn = get_connection(target_db)

    try:
        # 1. 데이터 삽입 및 트랜잭션 완료
        with conn:  # with conn을 써야 자동으로 commit이 됩니다.
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM tickers 
                    WHERE id = %s
                """, db_id)

        print(f"✅ 종목 삭제 완료: {db_id}")

        # 2. 최신 리스트를 다시 조회해서 반환 (refresh용)
        # 기존에 만든 get_user_ticker_list 함수를 재사용하는 것이 효율적입니다.
        return True

    except Exception as e:
        print(f"❌ 종목 삭제 실패: {e}")
        return False

def get_user_ticker_list(user_id):
    conn = get_connection(target_db)

    try:
        with conn.cursor() as cur:
            # %s를 사용하고 변수는 반드시 튜플 (user_id,) 형태로 전달해야 합니다.
            cur.execute(
                "SELECT id, ticker_code, ticker_name, target_price FROM tickers WHERE user_id = %s",
                (user_id,)
            )

            # 모든 행을 가져옵니다. (결과가 없으면 빈 리스트 [] 반환)
            results = cur.fetchall()

            # 결과 확인용 출력 (선택 사항)
            new_dict = {ticker_id: [code, name, price] for ticker_id, code, name, price in results}
            # 전역 변수 업데이트
            config.set_watch_list(new_dict)
            # 해당 유저의 주식 리스트를 목록을 보여주기
            return results

    except Exception as e:
        print(f"❌ 종목 리스트 조회 실패: {e}")
        return []  # 에러 발생 시 빈 리스트 반환

def execute_many_transactions(query, data_list):
    """여러 데이터를 안전하게 삽입"""
    conn = get_connection(target_db)
    try:
        with conn:
            with conn.cursor() as cur:
                # executemany는 내부적으로 루프를 돌며 효율적으로 처리합니다.
                cur.executemany(query, data_list)
        print(f"✅ 기본 종목 {len(data_list)}개 추가 완료!")
    except Exception as e:
        print(f"❌execute_many_transactions SQL 실행 실패: {e}")
