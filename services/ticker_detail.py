import tkinter as tk
import config
from datetime import datetime
import FinanceDataReader as fdr

from dateutil.relativedelta import relativedelta
import mplfinance as mpf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


def show_chart(self, item_data):
    ticker_code = item_data[0]

    # 1. 새 창 설정
    chart_window = tk.Toplevel(self.root)
    chart_window.title(f"{item_data[1]} 실시간 차트")
    chart_window.geometry("800x650")

    # [핵심] 2. 레이아웃 프레임 분리
    # 상단 버튼 영역
    button_frame = tk.Frame(chart_window)
    button_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

    # 하단 차트 영역 (이 영역을 draw_professional_chart가 사용)
    chart_frame = tk.Frame(chart_window)
    chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # 3. 버튼 클릭 시 호출될 통합 데이터 로딩 함수
    def on_button_click(day_type):
        # 0:일, 1:주, 2:월, 3:년
        start_str, end_str = get_date_range(day_type)

        # 기존 로직: 심볼 변환 후 데이터 로드
        default_code, suffix = ticker_code.split('.')
        selected = config.MY_INFO[0]['market_type']

        # 심볼 생성 로직
        if selected == 0:
            symbol = f"NAVER:{ticker_code.split('.')[0]}"
        elif selected == 1:
            symbol = ticker_code.split('.')[0]
        elif selected == 2:
            symbol = f"YAHOO:{default_code}.{suffix}"
        else:
            symbol = ticker_code

        try:
            df = fdr.DataReader(symbol, start=start_str, end=end_str)
            # 차트 프레임에 그리기
            draw_professional_chart(df, chart_frame)
        except Exception as e:
            print(f"데이터 로드 오류: {e}")

    def get_date_range(day_type):
        end_date = datetime.now()

        if day_type == 1:  # 주 (최근 1주일치 데이터를 보여주고 싶을 때)
            start_date = end_date - relativedelta(days=30)
        elif day_type == 2:  # 월 (최근 3개월치 흐름을 보고 싶을 때)
            start_date = end_date - relativedelta(months=3)
        elif day_type == 3:  # 년 (최근 1년치 흐름을 보고 싶을 때)
            start_date = end_date - relativedelta(years=1)
        else: # 일
            start_date = end_date - relativedelta(days=7)  # 기본값 하루

        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        print(f"시작일:{start_str}, 종료일:{end_str}")
        return start_str, end_str

    def draw_professional_chart(df, chart_frame):
        # 기존 차트 제거
        for widget in chart_frame.winfo_children():
            widget.destroy()

        # 데이터 전처리
        df.index = pd.to_datetime(df.index)
        df.index.name = 'Date'
        df = df.sort_index()

        mc = mpf.make_marketcolors(up='red', down='blue', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        fig, axes = mpf.plot(df, type='candle', mav=(5, 20, 60), style=s,
                             returnfig=True, figsize=(7, 5),
                             datetime_format='%Y-%m-%d', tight_layout=False)

        fig.subplots_adjust(bottom=0.25)

        # 캔버스 배치
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 툴바 배치 (줌/이동 가능)
        toolbar = NavigationToolbar2Tk(canvas, chart_frame)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    # 4. 버튼 생성
    types = [("1주", 0), ("1달", 1), ("3달", 2), ("1년", 3)]
    for text, val in types:
        btn = tk.Button(button_frame, text=text, command=lambda v=val: on_button_click(v))
        btn.pack(side=tk.LEFT, padx=5)

    # 5. 초기 호출 (기본값 년/3)
    on_button_click(0)
