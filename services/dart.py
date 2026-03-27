import os
import datetime
import re

class Dart_Info():
    def __init__(self):
        from dotenv import load_dotenv
        import OpenDartReader
        import config
        # 1. .env 파일의 환경 변수를 시스템으로 로드
        load_dotenv()
        # 2. os.getenv를 사용하여 키 가져오기
        dart_api_key = os.getenv("DART_API_KEY")
        google_api_key = config.MY_INFO[0]['genai_key']
        self.dart = None
        self.all_corp_codes = []
        self.model_genai = None

        # AI 설정
        if google_api_key:
            from google import genai
            from google.genai import types
            self.client = genai.Client(api_key=google_api_key)
            # 모델을 미리 생성해두면 호출 속도가 빨라집니다.
            # 모델명 앞에 'models/'를 명시적으로 붙여주는 것이 가장 안전합니다.
            model_candidates = [
                "gemini-2.5-flash-lite",
                "gemini-2.0-flash",
                "gemini-3-flash-preview",
                "gemini-1.5-flash"  # 가장 보수적이고 안전한 선택지
            ]
            self.my_config = types.GenerateContentConfig(
                temperature=0.2,  # 좀 더 일관된 답변을 위해 낮게 설정
                top_p=0.95,
                max_output_tokens=1000,
                # 응답을 항상 특정 타입으로 받고 싶을 때 response_mime_type 등 설정 가능
            )
            for model_name in model_candidates:
                try:
                    # 모델 생성 및 호출
                    self.model_genai = model_name
                    break
                except Exception as e:
                    # 429 에러(Quota Exceeded) 등이 발생하면 다음 모델로 넘어감
                    print(f"⚠️ {model_name} 실패: {e}. 다음 모델로 전환합니다.")
                    continue

        # 데이터 불러오기 예시
        if dart_api_key:
            self.dart = OpenDartReader(dart_api_key)
            self.all_corp_codes = self.dart.corp_codes
            print("✅ DART API 키가 성공적으로 로드되었습니다.")
        else:
            print("❌ API 키를 찾을 수 없습니다. .env 파일을 확인해주세요.")

    def get_corp_code(self, target_ticker):
        result = self.all_corp_codes[self.all_corp_codes['stock_code'] == target_ticker]
        if not result.empty:
            return result.iloc[0]['corp_code']  # 8자리 고유번호 반환
        return None

    def get_ticker_news(self, ticker):
        import time
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

    def get_detail_news(self, rcp_no):
        try:
            content = self.dart.document(rcp_no)
            clean_text = re.sub(r'<[^>]*>', '', content)
            clean_text = re.sub(r'\n\s*\n', '\n', clean_text).strip()
            return self.get_ai_summary(clean_text)
        except Exception as e:
            print(f"본문 로드 실패: {e}")
            import config
            if not config.MY_INFO[0]['genai_key']:
                return "구글 AI STUDIO KEY를 등록후 사용해 주세요."
            else:
                return "문서 읽기 실패"

    def get_ai_summary(self, raw_text):

        truncated_text = raw_text[:5000]

        prompt = f"""
                    당신은 전문 주식 분석가입니다. 아래의 DART 공시 원문을 읽고 투자자가 꼭 알아야 할 핵심을 요약하세요.
            
                    [출력 형식 및 지침]
                    1. 첫 줄은 반드시 다음 형식을 엄격히 지킬 것: ✨ AI 공시 요약 분석 결과 [평점: 호재/악재/중립 중 택1]
                    2. 요약 내용은 3~5개의 리스트 항목으로 작성할 것.
                    3. 전문 용어 대신 초보 투자자도 이해할 수 있는 쉬운 용어를 사용할 것.
                    4. 각 리스트 항목은 반드시 '-'로 시작하고, 항목이 끝날 때마다 줄바꿈을 두 번(\\n\\n) 하여 가독성을 높일 것.
                    5. 마지막에 별도의 추가 멘트나 평점을 중복해서 적지 말 것.
            
                    [참고 사항]
                    - 제공된 공시 원문을 최우선으로 분석하되, 해당 기업의 최근 시장 흐름과 뉴스 맥락을 반영하여 판단할 것.
            
                    원문:
                    {truncated_text}
                    """

        response = self.client.models.generate_content(model=self.model_genai,contents=prompt,config=self.my_config)
        return f"{response.text}"

    def get_ai_news_summary(self, raw_text):

        truncated_text = raw_text[:5000]

        prompt = f"""
                    당신은 경제 분석가입니다. 아래의 뉴스 원문을 읽고 투자자가 꼭 알아야 할 핵심을 요약하세요.

                    [출력 형식 및 지침]
                    1. 첫 줄은 반드시 다음 형식을 엄격히 지킬 것: ✨ AI 공시 요약 분석 결과 [평점: 호재/악재/중립 중 택1]
                    2. 요약 내용은 3~5개의 리스트 항목으로 작성할 것.
                    3. 전문 용어 대신 초보 투자자도 이해할 수 있는 쉬운 용어를 사용할 것.
                    4. 각 리스트 항목은 반드시 '-'로 시작하고, 항목이 끝날 때마다 줄바꿈을 두 번(\\n\\n) 하여 가독성을 높일 것.
                    5. 마지막에 별도의 추가 멘트나 평점을 중복해서 적지 말 것.

                    [참고 사항]
                    - 제공된 공시 원문을 최우선으로 분석하되, 해당 기업의 최근 시장 흐름과 뉴스 맥락을 반영하여 판단할 것.

                    원문:
                    {truncated_text}
                    """

        response = self.client.models.generate_content(model=self.model_genai, contents=prompt, config=self.my_config)
        return f"{response.text}"

    # 3. 데이터셋 생성 (60일 보고 5일 예측)
    def create_dataset(self, dataset, look_back=60, forecast=5):
        import numpy as np
        X, y = [], []
        for i in range(len(dataset) - look_back - forecast + 1):
            # 과거 60일치 (가격, 거래량) -> Feature
            X.append(dataset[i: i + look_back, :])
            # 향후 5일치 (가격만) -> Label (0번 컬럼이 Close라고 가정)
            y.append(dataset[i + look_back: i + look_back + forecast, 0])

        return np.array(X), np.array(y)

    def build_lstm_model(self, x_shape):
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import LSTM, Dense, Dropout

        model = Sequential([
            # input_shape=(60, 2) -> (과거일수, 피처수)
            LSTM(units=64, return_sequences=True, input_shape=(x_shape[1], x_shape[2])),
            Dropout(0.2),
            LSTM(units=64, return_sequences=False),
            Dropout(0.2),
            Dense(units=32, activation='relu'),
            Dense(units=5)  # 최종 출력: 향후 5일치 가격
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def get_ai_prediction(self, df):
        import numpy as np
        from sklearn.preprocessing import MinMaxScaler
        # 1. 데이터 추출 (가격, 거래량)
        raw_data = df[['Close', 'Volume']].values

        # 2. 스케일링 (각 컬럼별 0~1 사이로)
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(raw_data)

        # 3. 학습 데이터 생성 (과거 60일 추세 -> 미래 5일 가격)
        X, y = self.create_dataset(scaled_data, look_back=60, forecast=5)

        # 4. 모델 생성 및 학습
        model = self.build_lstm_model(X.shape)
        model.fit(X, y, epochs=25, batch_size=32, verbose=0)

        # 5. 최신 데이터를 기반으로 예측 시도
        # 가장 최근 60일의 (가격, 거래량) 흐름을 입력
        last_window = scaled_data[-60:].reshape(1, 60, 2)
        predicted_scaled = model.predict(last_window)  # 결과: (1, 5) 형태

        # 6. 역스케일링 (수정된 버전)
        dummy = np.zeros((5, 2))
        dummy[:, 0] = predicted_scaled[0]  # 예측된 5일치 종가

        # [핵심] 마지막 거래량(Volume) 값을 더미의 1번 컬럼에 채워줍니다.
        # 0으로 두는 것보다 실제 마지막 거래량 값을 넣어주는 것이 훨씬 안정적입니다.
        last_volume = scaled_data[-1, 1]
        dummy[:, 1] = last_volume

        # 역스케일링 실행
        final_prediction = scaler.inverse_transform(dummy)[:, 0]

        return final_prediction.tolist()


    def check_deployment_status(self):
        status_report = []

        # 2. 텐서플로 로드 및 작동 테스트
        try:
            import tensorflow as tf
            status_report.append(f"🤖 TF 버전: {tf.__version__}")

            # 간단한 연산 테스트 (실제 엔진 작동 확인)
            v = tf.constant([1.0, 2.0])
            v_sum = tf.reduce_sum(v).numpy()
            status_report.append(f"⚡ TF 연산 테스트: {'✅ 성공' if v_sum == 3.0 else '❌ 실패'}")

        except ImportError:
            status_report.append("❌ TF 로드 실패: 라이브러리가 누락되었습니다.")
        except Exception as e:
            status_report.append(f"⚠️ TF 실행 오류: {str(e)[:50]}...")

        # 3. 결과 메세지 박스로 출력
        final_msg = "\n".join(status_report)
        return final_msg

    def clear_memory(self):
        try:
            import tensorflow as tf
            # 1. 케라스 내부 그래프/세션 초기화
            tf.keras.backend.clear_session()

            print("✅ 메모리 정리 완료")
        except Exception as e:
            print(f"⚠️ 메모리 정리 중 오류: {e}")

