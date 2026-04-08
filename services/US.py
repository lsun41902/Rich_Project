import FinanceDataReader as fdr

def save_us_stock_list():
    import pandas as pd
    # 1. 미국 3대 거래소 목록 가져오기
    print("미국 시장 데이터 수집 중...")
    df_nasdaq = fdr.StockListing('NASDAQ')
    df_nyse = fdr.StockListing('NYSE')
    df_amex = fdr.StockListing('AMEX')

    # 2. 데이터 합치기 및 거래소 구분 컬럼 추가 (선택사항)
    df_nasdaq['Exchange'] = 'NASDAQ'
    df_nyse['Exchange'] = 'NYSE'
    df_amex['Exchange'] = 'AMEX'
    df_amex['Name_Ko'] = ''

    df_us = pd.concat([df_nasdaq, df_nyse, df_amex], ignore_index=True)
    pd.set_option('display.max_columns', None)  # 열 제한 해제, 확인용
    pd.set_option('display.expand_frame_repr', False)  # 한 줄에 다 나오게

    print(f"✅ 저장 완료:\n{df_us.tail(10)}")
    return df_us