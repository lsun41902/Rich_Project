from datetime import datetime, timedelta
import FinanceDataReader as fdr
import pandas as pd

def pull_request_stock(raw_code,days=730,stock_type=None):
    try:
        real_symbol = raw_code.split('.')[0] if stock_type == 0 else raw_code
        start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_str = datetime.now().strftime('%Y-%m-%d')

        df = fdr.DataReader(real_symbol, start=start_str, end=end_str)
        pd.set_option('display.max_columns', None)  # 열 제한 해제, 확인용
        pd.set_option('display.expand_frame_repr', False)  # 한 줄에 다 나오게
        if 'Change' not in df.columns:
            df['Change'] = df['Close'].pct_change()
        print(df)
        return df
    except Exception as e:
        print(f"2년치 데이터 가져오기 오류: {e}")

from dto.gold_dto import GoldDTO
def pull_krx_gold(gold:GoldDTO,days=730):
    try:
        start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_str = datetime.now().strftime('%Y-%m-%d')
        symbol = gold.code if gold.type == 0 else f"{gold.code}"
        df = fdr.DataReader(symbol, start=start_str, end=end_str)
        try:
            if df is not None and not df.empty:
                # 4. 단위 통일 로직 (전체 컬럼에 일괄 적용)
                if gold.type == 0:
                    # 국제 선물: (USD/oz * 환율 / 31.1035) -> 1g 가격 -> (* 3.75) -> 1돈 가격
                    # ※ 주의: 과거 데이터 전체에 현재 환율을 적용하는 한계는 있음
                    exchange_rate = gold.today_usd
                    multiplier = (exchange_rate / 31.1035) * 3.75
                    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * multiplier
                else:
                    # 국내 종목: (지수 * 10) -> 1g 가격 -> (* 3.75) -> 1돈 가격
                    multiplier = 10 * 3.75
                    df[['Open', 'High', 'Low', 'Close']] = df[['Open', 'High', 'Low', 'Close']] * multiplier
            return df
        except Exception as e:
            print(f"📡 fdr 데이터 로드 오류 ({symbol}): {e}")
        return 0
    except Exception as e:
        print(f"업데이트 오류: {e}")

def pull_request_stock_NASDAQ():
    import FinanceDataReader as fdr
    # 1. 나스닥(NASDAQ) 종목 리스트
    df_nasdaq = fdr.StockListing('S&P500')
    import pandas as pd
    # 1. 컬럼 너비 제한 해제 (내용이 길어도 다 보여줌)
    pd.set_option('display.max_colwidth', None)

    # 2. 보여줄 최대 컬럼 수 설정 (컬럼이 많아도 안 잘림)
    pd.set_option('display.max_columns', None)

    # 3. 출력 화면 너비 설정 (한 줄에 길게 나오도록)
    pd.set_option('display.width', 1000)

    print(df_nasdaq[['Symbol', 'Name', 'Sector', 'Industry']].head(20))

def pull_usd_krw():
    import FinanceDataReader as fdr
    # 'USD/KRW' 심볼을 사용합니다.
    # 최근 2일치 데이터를 가져와서 가장 마지막(최신) 행을 선택합니다.
    df = fdr.DataReader('USD/KRW')

    if not df.empty:
        current_rate = df['Close'].iloc[-1]  # 가장 최근 종가
        change_p = df['Close'].pct_change(fill_method=None).iloc[-1] * 100  # 전일 대비 변동률
        return round(current_rate, 2), round(change_p, 2)
    return None, None


def pull_krx_top20(is_top_rising, stock_type):
    import pandas as pd
    try:
        # 1. 데이터 가져오기 시도
        df_krx = fdr.StockListing('KRX')

        if df_krx is None or df_krx.empty:
            print("⚠️ KRX로부터 데이터를 가져오지 못했습니다.")
            return pd.DataFrame()  # 빈 데이터프레임 반환

        cols = ['Close', 'Changes', 'ChagesRatio', 'Open', 'High', 'Low', 'Volume', 'Amount', 'Marcap']
        df_filtered = df_krx[df_krx['MarketId'].isin(['STK', 'KSQ'])].copy()
        for col in cols:
            # 데이터에 '-' 가 들어있거나 NaN인 경우 0으로 치환
            df_filtered[col] = pd.to_numeric(df_filtered[col].replace('-', '0'), errors='coerce').fillna(0)
        # 2. 정렬 및 상위 10개 추출
        if is_top_rising:
            # 내림차순(큰 숫자부터) 정렬 후 상위 추출
            result = df_filtered.sort_values(by='ChagesRatio', ascending=False).head(20)
        else:
            # 2. 급락주(하락률 큰 순)를 보고 싶을 때 (is_top_rising = False)
            # 오름차순(작은 숫자부터) 정렬 후 상위 추출
            result = df_filtered.sort_values(by='ChagesRatio', ascending=True).head(20)
        print("TOP20의 데이터를 가져왔습니다.")
        # pd.set_option('display.max_columns', None)  # 열 제한 해제, 확인용
        print(result)
        return result

    except Exception as e:
        print(f"❌ KRX 데이터 로딩 중 오류 발생: {e}")
        return pd.DataFrame()  # 에러 시 빈 데이터프레임 반환하여 GUI 유지
