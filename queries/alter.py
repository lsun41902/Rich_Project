import database.connection_SQL as sql_db

def migrate_user_table(check_table,check_columns,new_table):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cursor = conn.cursor()
                # 1. 현재 테이블에 buy_price 있는지 확인
                cursor.execute(f"PRAGMA table_info({check_table})")
                columns = [col[1] for col in cursor.fetchall()]

                if check_columns not in columns:
                    print("🔄 구버전 테이블 감지: 구조 재편성 시작...")

                    # 임시 테이블 생성 (원하는 순서대로)
                    create_query, insert_query = update_user_table()
                    cursor.execute(create_query)
                    cursor.execute(insert_query)

                    # 기존 테이블 삭제 및 새 테이블 이름 변경
                    cursor.execute(f"DROP TABLE {check_table}")
                    cursor.execute(f"ALTER TABLE {new_table} RENAME TO {check_table}")

                    print("✅ 테이블 구조 업데이트 완료 (users)")
    except Exception as e:
        sql_db.print_error(f"DB 연결 실패:{e}")

def update_user_table():
    msg =["""
                                   CREATE TABLE users_new
                                   (
                                       id          INTEGER PRIMARY KEY AUTOINCREMENT,
                                       user_name   VARCHAR(50) NOT NULL,
                                       webhook     TEXT      DEFAULT '',
                                       genai_key   TEXT      DEFAULT '',
                                       types       INTEGER   DEFAULT 0,
                                       is_active   BOOLEAN   DEFAULT TRUE,
                                       stock_type INTEGER   DEFAULT 0,
                                       recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )
                                   """,
          """
          INSERT INTO users_new (id, user_name, webhook, types, is_active, stock_type, recorded_at)
          SELECT id, user_name, webhook, types, is_active, stock_type, recorded_at
          FROM users
          """
          ]
    return msg


def migrate_tickers_table(check_table,check_columns,new_table):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cursor = conn.cursor()
                # 1. 현재 테이블에 genai_key가 있는지 확인
                cursor.execute(f"PRAGMA table_info({check_table})")
                columns = [col[1] for col in cursor.fetchall()]

                if check_columns not in columns:
                    print("🔄 구버전 테이블 감지: 구조 재편성 시작...")

                    # 임시 테이블 생성 (원하는 순서대로)
                    create_query, insert_query = update_ticker_table()
                    cursor.execute(create_query)
                    cursor.execute(insert_query)

                    # 기존 테이블 삭제 및 새 테이블 이름 변경
                    cursor.execute(f"DROP TABLE {check_table}")
                    cursor.execute(f"ALTER TABLE {new_table} RENAME TO {check_table}")

                    print("✅ 테이블 구조 업데이트 완료 (tickers)")
    except Exception as e:
        sql_db.print_error(f"DB 연결 실패:{e}")

def update_ticker_table():
    msg =["""
                                   CREATE TABLE IF NOT EXISTS tickers_new (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER NOT NULL,
                                    ticker_code VARCHAR(20) DEFAULT '',
                                    ticker_name VARCHAR(50) DEFAULT '',
                                    target_price NUMERIC(15, 2) DEFAULT 0,
                                    target_price_us NUMERIC(15, 2) DEFAULT 0,
                                    buy_price NUMERIC(15, 2) DEFAULT 0,
                                    buy_price_us NUMERIC(15, 2) DEFAULT 0,
                                    amount NUMERIC(15, 2) DEFAULT 0,
                                    dollar_price NUMERIC(15, 2) DEFAULT 0,
                                    stock_type NUMERIC(15, 2) DEFAULT 0,
                                    is_active BOOLEAN DEFAULT TRUE,
                                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                                    UNIQUE (user_id, ticker_code) -- ON CONFLICT 처리를 위해 필수
                                )
                                   """,
          """
          INSERT INTO tickers_new (
            id, user_id, ticker_code, ticker_name, target_price, 
            target_price_us, buy_price, buy_price_us, amount, dollar_price, stock_type, is_active, recorded_at
        )
        SELECT 
            id, user_id, ticker_code, ticker_name, target_price, 
            0, 0, 0, 0, 0, 0, is_active, recorded_at  -- 없는 값들을 0과 'KRX'로 채움
        FROM tickers
          """
          ]
    return msg