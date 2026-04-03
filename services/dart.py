import os
import datetime
from bs4 import BeautifulSoup

class DartInfo:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DartInfo, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return

        from dotenv import load_dotenv
        import OpenDartReader
        import dart_fss as dfss
        # 1. .env 파일의 환경 변수를 시스템으로 로드
        load_dotenv()
        # 2. os.getenv를 사용하여 키 가져오기
        dart_api_key = os.getenv("DART_API_KEY")
        self.dart = None
        self.all_corp_codes = []
        self.model_genai = None

        # 데이터 불러오기 예시
        if dart_api_key:
            self.dart = OpenDartReader(dart_api_key)
            self.all_corp_codes = self.dart.corp_codes
            dfss.set_api_key(api_key=dart_api_key)
            print("✅ DART API 키가 성공적으로 로드되었습니다.")
        else:
            print("❌ API 키를 찾을 수 없습니다. .env 파일을 확인해주세요.")

    def get_corp_code(self, target_ticker):
        result = self.all_corp_codes[self.all_corp_codes['stock_code'] == target_ticker]
        if not result.empty:
            return result.iloc[0]['corp_code']  # 8자리 고유번호 반환
        return None

    def get_notice_content_clean(self, rcp_no):
        xml_text = self.dart.document(rcp_no)  # 아까 받으신 그 XML

        # BeautifulSoup으로 태그 제거
        soup = BeautifulSoup(xml_text, 'xml')  # XML 파서 사용
        clean_text = soup.get_text(separator="\n", strip=True)

        return clean_text

    def get_ticker_news(self, ticker):
        try:
            code = ticker.split('.')[0] if '.' in ticker else ticker
            corp_code = self.get_corp_code(code)
            if not corp_code:
                return "⚠️ DART 고유번호를 찾을 수 없는 종목입니다."

            # 오늘부터 3개월 전까지의 공시 검색
            end_date = datetime.date.today().strftime('%Y%m%d')
            start_date = (datetime.date.today() - datetime.timedelta(days=90)).strftime('%Y%m%d')

            # DART API 호출: 최근 공시 목록 가져오기
            disclosures = self.dart.list(corp_code, start=start_date, end=end_date)

            if disclosures is None or disclosures.empty:
                return f"ℹ️ 최근 3개월간 '{ticker}'의 주요 공시가 없습니다."

            # 텍스트 창에 보여줄 내용 구성
            report_text = f"[{ticker}] 최근 주요 공시 (최신순)\n"
            report_text += "=" * 40 + "\n\n"

            # 상위 10개 공시만 표시
            for i, row in disclosures.head(10).iterrows():
                # 컬럼명이 다를 수 있으므로 안전하게 가져오기
                raw_date = row.get('rcept_dt', '')
                date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                title = row.get('report_nm', '')
                rcp_no = row.get('rcept_no', '')  # 표에서 직접 꺼냄

                formatted_entry = f"📅 {date}\n   📰 {title}|{rcp_no}\n\n"
                report_text += formatted_entry

            report_text += "=" * 40 + "\n"
            report_text += "* 본 내용은 DART의 원문 데이터를 기반으로 합니다.\n* 상세 내용은 DART 사이트에서 확인하세요."

            return report_text
        except Exception as e:
            return f"⚠️ DART 데이터를 가져오는 중 오류가 발생했습니다.\n오류 내용: {e}"

dart = DartInfo()