import database.connection_SQL as sql_db

def delete_ticker_to_db(db_id):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                sql = "DELETE FROM tickers WHERE id = ?"
                cur.execute(sql, (db_id,))
                cur.close()
                sql_db.print_ok(f"종목 삭제 완료:{db_id}")
                return True
    except Exception as e:
        sql_db.print_error(f"종목 삭제 실패:{e}")
        return False

# 미국 주식 목록 초기화
def default_save_US_ticker_list(df):
    try:
        with sql_db.get_connection() as conn:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM default_ticker_us")
                conn.commit()  # 반드시 커밋을 해줘야 반영됩니다.
                print("미국 티커 리스트 갱신 완료!")
    except Exception as e:
        sql_db.print_error(f"default_save_US_ticker_list 저장 실패: {e}")