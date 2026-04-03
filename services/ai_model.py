from pydantic import BaseModel
import re
import json
from typing import List
from google.api_core import exceptions
# 1. 받을 데이터 구조 정의
class DailyPredict(BaseModel):
    date: str
    price: int
    sentiment_score: float
    reason: str

class StockPredictList(BaseModel):
    predictions: List[DailyPredict]

class AIModel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIModel, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        import config
        from dotenv import load_dotenv

        # 1. .env 파일의 환경 변수를 시스템으로 로드
        load_dotenv()
        google_api_key = config.MY_INFO[0]['genai_key']
        # AI 설정
        if google_api_key:
            from google import genai
            from google.genai import types
            self.client = genai.Client(api_key=google_api_key)
            # for model in self.client.models.list():
            #     print(f"정확한 모델 ID: {model.name}")
            # 모델을 미리 생성해두면 호출 속도가 빨라집니다.
            # 모델명 앞에 'models/'를 명시적으로 붙여주는 것이 가장 안전합니다.
            model_candidates = [
                "models/gemini-3.1-flash-lite-preview",  # 1순위: 찾으셨던 500회 모델 (정확한 ID)
                "models/gemini-3-flash-preview",  # 2순위: 차세대 플래시 모델
                "models/gemini-2.0-flash-lite",  # 3순위: 가볍고 빠른 라이트 버전
                "models/gemini-2.5-flash-lite",  # 4순위: 아까 20회 제한 걸렸던 모델 (백업용)
                "models/gemma-3-4b-it"  # 5순위: 하루 14,400회 가능한 무한 동력 모델
            ]
            self.my_config = types.GenerateContentConfig(
                temperature=0.2,  # 좀 더 일관된 답변을 위해 낮게 설정
                top_p=0.95,
                max_output_tokens=1000,
                # 응답을 항상 특정 타입으로 받고 싶을 때 response_mime_type 등 설정 가능
            )
            self.my_config_json = types.GenerateContentConfig(
                temperature=0.2,  # 좀 더 일관된 답변을 위해 낮게 설정
                top_p=0.95,
                max_output_tokens=1000,
                response_mime_type="application/json",
                response_json_schema=StockPredictList.model_json_schema()
                # 응답을 항상 특정 타입으로 받고 싶을 때 response_mime_type 등 설정 가능
            )
            for model_name in model_candidates:
                try:
                    # 모델 생성 및 호출
                    self.model_genai = model_name
                    self._initialized = True
                    break
                except Exception as e:
                    # 429 에러(Quota Exceeded) 등이 발생하면 다음 모델로 넘어감
                    print(f"⚠️ {model_name} 실패: {e}. 다음 모델로 전환합니다.")
                    continue



    def get_ai_summary(self, raw_text):
        try:

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

            response = self.client.models.generate_content(model=self.model_genai, contents=prompt, config=self.my_config)
            return f"{response.text}"
        except exceptions.ResourceExhausted as e:
            print(f"⚠️ 할당량 초과!")
        except Exception as e:
            print(f"AI의 뉴스 분석 오류{e}")

    def get_ai_news_summary(self, raw_text):
        try:

            truncated_text = raw_text[:5000]

            prompt = f"""
                        당신은 경제 분석가입니다. 아래의 뉴스 원문을 읽고 투자자가 꼭 알아야 할 핵심을 요약하세요.
    
                        [출력 형식 및 지침]
                        1. 첫 줄은 반드시 다음 형식을 엄격히 지킬 것: ✨ AI 요약 분석 결과 [평점: 호재/악재/중립 중 택1]
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
        except exceptions.ResourceExhausted as e:
            print(f"⚠️ 할당량 초과!")
        except Exception as e:
            print(f"AI의 뉴스 분석 오류{e}")

    def get_ai_briefing(self,ticker_name, keyword, news_list):
        try:
            # news_list는 위 Cypher 쿼리 결과물
            context = "\n\n".join([f"{n['title']}: {n['content']}" for n in news_list])

            prompt = f"""
            당신은 전문 주식 분석가입니다. 
            제공된 뉴스 데이터를 바탕으로 '{ticker_name}'와 '{keyword}'에 대한 **분석 리포트**를 작성하세요.
    
            [뉴스 데이터]
            {context}
    
            [구성 예시]
            📢 종합 분석 한 줄 평
            ----------------------------------------------------------------
            [▲] 긍정적 요인
            1. 내용...
            [▼] 부정적 요인
            1. 내용...
            ----------------------------------------------------------------
            💡 투자 유의
    
            [요청사항]
            - 전문적이면서도 투자자가 한눈에 직관적으로 이해할 수 있는 톤을 유지하세요.
            - 마크다운 기호(#, |) 보다는 이모지와 줄바꿈을 활용해 '가독성' 위주로 작성하세요.
            - 각 섹션 시작 전후에 '----------------------------------------------------------------' 구분선을 넣어주세요.
            """

            # Gemini API 호출 (예시)
            response = self.client.models.generate_content(model=self.model_genai, contents=prompt, config=self.my_config)
            return response.text
        except exceptions.ResourceExhausted as e:
            print(f"⚠️ 할당량 초과!")
        except Exception as e:
            print(f"AI의 뉴스 분석 오류{e}")


    def get_ai_detail_briefing(self,ticker_name, news_list):
        try:

            # news_list는 위 Cypher 쿼리 결과물
            context = "\n\n".join([f"{n['title']}" for n in news_list])

            prompt = f"""
            지금 '{ticker_name}' 의 주가가 엄청난 변화를 일으키고 있어! 지금 뉴스를 바탕으로 무슨 일이 있었는지 알려줘.
            제공된 뉴스 데이터를 바탕으로 '{ticker_name}'에 대한 **분석 리포트**를 150자 이내로 작성해.
    
            [뉴스 타이틀]
            {context}
    
            [구성 예시]
            📢 종합 분석 한 줄 평
            ----------------------------------------------------------------
            [✅] 호재 or [⚠️]악재 (둘중 현재 상황에 크게 반영된 결과 하나만 설명하기)
            변동 요인
            1. 내용...
            2. 영향...
            3. 시장이 민감하게 반응한 이유...
            ----------------------------------------------------------------
            💡 투자 유의
    
            [요청사항]
            - 전문적이면서도 투자자가 한눈에 직관적으로 이해할 수 있는 톤을 유지하세요.
            - 마크다운 기호(#, |) 보다는 이모지와 줄바꿈을 활용해 '가독성' 위주로 작성하세요.
            - 각 섹션 시작 전후에 '----------------------------------------------------------------' 구분선을 넣어주세요.
            """

            # Gemini API 호출 (예시)
            response = self.client.models.generate_content(model=self.model_genai, contents=prompt, config=self.my_config)
            return response.text
        except exceptions.ResourceExhausted as e:
            print(f"⚠️ 할당량 초과!")
        except Exception as e:
            print(f"AI의 뉴스 분석 오류{e}")

    def get_ai_detail_predict(self,ticker_name, news_list, news_detail, predict_price, cur_price):
        # news_list는 위 Cypher 쿼리 결과물
        context = "\n\n".join([f"{n['title']}" for n in news_list])
        predict_price_text = ",".join([f"{int(price)}KRW" for price in predict_price])
        prompt = f"""
        당신은 금융 분석 전문가입니다. 제공된 뉴스의 감성(Sentiment)과 LSTM 예측가를 결합하여 최종 가격을 예측하세요.
        
        [분석 대상]
        - 종목명/현재 주가: {ticker_name} / {cur_price} KRW
        - 뉴스 상황: {context}
        - 뉴스 분석: {news_detail}
        - 기초 예측가(LSTM 5일치): {predict_price_text}
        
        [수행 지침]
        1. **뉴스 우선 원칙**: LSTM 예측값이 상승하더라도, 뉴스 분석 결과가 '악재'라면 반드시 현재가보다 낮은 가격으로 하향 조정하세요. 반대로 '호재'라면 상향 조정하세요.
        2. 한국 주식 시장의 상하한가(±30%) 제한을 준수하세요.
        3. **감성 점수(Sentiment_Score) 적용**: 
           - -1.0(치명적 악재) ~ +1.0(초강력 호재) 사이로 측정하세요.
           - 점수가 음수(-)라면 LSTM 가격에서 해당 비율만큼 강하게 차감하고, 현재가보다 낮게 책정하는 것을 검토하세요.
        4. 결과는 반드시 아래 JSON 형식으로만 응답하고, 어떠한 설명이나 마크다운 태그도 포함하지 마세요.
        5. 결과는 반드시 **5개의 예측 객체를 포함한 JSON 리스트** 형식으로만 응답하세요.
        6. **논리적 일관성**: 악재인데 가격이 오르거나, 호재인데 가격이 내리는 '논리적 모순'이 발생하지 않도록 최종 점검하세요.
        
        [응답 형식]
        반드시 아래 구조의 JSON 리스트만 반환하세요. 마크다운 태그(```json)나 설명은 절대 금지합니다.
        
        JSON Schema:
        {{
            "predictions": [
                {{
                    "date": "YYYY-MM-DD",
                    "price": 0,
                    "sentiment_score": 0.0,
                    "reason": "해당 날짜의 분석 근거 20자 내외"
                }}
            ]
        }}
        """

        # Gemini API 호출 (예시)
        try:
            response = self.client.models.generate_content(model=self.model_genai, contents=prompt,
                                                           config=self.my_config_json)
            print(response.text)
            clean_json = re.sub(r"```json|```", "", response.text).strip()
            data = json.loads(clean_json)

            # predictions 키 안에 있는 리스트를 가져옴
            prediction_list = data.get("predictions", [])

            # 예: 5일치 가격만 리스트로 추출
            return prediction_list  # [72500, 73100, 72800, 74000, 75200] 형태
        except exceptions.ResourceExhausted as e:
            print(f"⚠️ 할당량 초과!")
        except Exception as e:
            print(f"5일치 데이터 파싱 실패: {e}")
            return []

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
ai_model = AIModel()