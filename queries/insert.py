import database.connection_SQL as sql_db


# 한국 주식 정보 저장
def insert_ticker(current_user, code, name, price, stock_type):
    try:
        target_col = "target_price" if stock_type == 0 else "target_price_us"
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                query = f"""INSERT INTO tickers (user_id, ticker_code, ticker_name, {target_col}, market_type)
                                VALUES (?, ?, ?, ?, ?)
                                """

                params = (current_user, code, name, price, stock_type)
                cur.execute(query, params)
                cur.close()
                sql_db.print_ok(f"종목 추가 완료: {name}({code})")
                return True
    except Exception as e:
        sql_db.print_error(f"종목 추가 실패:{e}")
        return False


def insert_stock_us(df):
    # 1. 쿼리문 준비
    query = """
        INSERT OR REPLACE INTO default_tickers_US 
        (symbol, name_en, name_ko, industry, market_type) 
        VALUES (?, ?, ?, ?, ?)
    """

    # 2. DataFrame에서 필요한 컬럼만 추출하여 리스트(튜플 묶음)로 변환
    # 컬럼 순서가 VALUES (?, ?, ?, ?, ?)와 일치해야 합니다.
    data_list = df[['Symbol', 'Name', 'Name_Ko', 'Industry', 'Exchange']].values.tolist()

    # 3. 미리 만들어둔 공용 함수 호출
    sql_db.execute_many_transactions(query, data_list)
