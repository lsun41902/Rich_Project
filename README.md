📈 AI-Powered Real-time Stock Analyzer
LSTM 딥러닝과 Gemini AI를 결합한 실시간 주식 차트 및 공시 분석 도구입니다.

이 프로젝트는 mplfinance를 활용한 전문적인 캔들 차트 시각화와 더불어, 과거 데이터를 학습한 AI의 가격 예측 및 최신 DART 공시 요약 기능을 제공하여 투자 의사결정을 돕습니다.

🚀 주요 기능 (Key Features)
1. 실시간 전문 캔들 차트
인터랙티브 차트: 마우스 휠 줌(Zoom), 드래그 이동(Pan)을 지원하며 구간별 최적의 Y축 범위를 자동 조정합니다.

상세 정보 표시: 마우스 오버 시 시가, 종가, 고가, 저가 및 변동률을 툴팁으로 즉시 확인 가능합니다.

실시간 시세 연동: 일정 주기마다 최신 주가를 받아와 차트를 갱신합니다.

2. AI 가격 예측 (LSTM 기반)
기술적 분석: 과거 60일간의 종가와 거래량 데이터를 LSTM 모델이 학습하여 향후 5일간의 주가 흐름을 예측합니다.

시각화: 예측된 미래 가격 데이터를 차트상에 'AI Prediction' 구간으로 표시합니다.

3. DART 공시 & AI 뉴스 요약
공시 자동 로딩: Open DART API를 통해 해당 종목의 최신 공시 목록을 실시간으로 가져옵니다.

AI 감성 분석: Gemini AI를 활용하여 선택한 공시의 내용을 분석하고, 호재/악재 여부를 판단하여 핵심 내용을 요약합니다.

4. 보안 및 환경 설정
API 키 암호화: 사용자의 API Key(GenAI 등)를 OS 고유 식별자 기반으로 암호화하여 안전하게 관리합니다.

크로스 플랫폼 대응: Windows와 macOS에서 동일하게 동작하는 암호화 로직을 채택했습니다.

🛠 기술 스택 (Tech Stack)
| **분류** | **기술** |
| --- | --- |
| **Language** | Python 3.10+ |
| **GUI** | Tkinter |
| **Analysis** | TensorFlow (Keras), Scikit-learn, Pandas, NumPy |
| **Visualization** | Matplotlib, mplfinance |
| **AI/LLM** | Google Gemini API (Generative AI) |
| **Data** | Open DART API, FinanceDataReader |
