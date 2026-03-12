import tkinter as tk
import config
from datetime import datetime,timedelta
import FinanceDataReader as fdr

from dateutil.relativedelta import relativedelta
import mplfinance as mpf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.dates as mdates
import matplotlib.font_manager as fm

def show_chart(self, item_data):
    ticker_code = item_data[0]

    # 1. 새 창 설정
    chart_window = tk.Toplevel(self.root)
    chart_window.title(f"{item_data[1]} 실시간 차트")
    chart_window.geometry("800x650")

    top_info_frame = tk.Frame(chart_window)
    top_info_frame.pack(side="top", fill="x", pady=5)

    top_info_frame.grid_columnconfigure(0, weight=1)  # 왼쪽 빈 공간
    top_info_frame.grid_columnconfigure(1, weight=0)  # 종목명 (고정)
    top_info_frame.grid_columnconfigure(2, weight=0)  # 현재가 (고정)
    top_info_frame.grid_columnconfigure(3, weight=1)  # 오른쪽 빈 공간

    # 2. 종목명 레이블 (grid 사용)
    ticker_name_label = tk.Label(top_info_frame, text=f"{item_data[1]}", font=("Arial", 14, "bold"))
    ticker_name_label.grid(row=0, column=1, padx=10)

    # 3. 실시간 금액 레이블 (grid 사용)
    price_label = tk.Label(top_info_frame, text="로딩 중...", font=("Arial", 14), fg="blue")
    price_label.grid(row=0, column=2, padx=10)

    # [핵심] 2. 레이아웃 프레임 분리
    # 상단 버튼 영역
    button_frame = tk.Frame(chart_window)
    button_frame.pack(side="top", fill="x", padx=5, pady=5)

    # 하단 차트 영역 (이 영역을 draw_professional_chart가 사용)
    chart_frame = tk.Frame(chart_window)
    chart_frame.pack(side="top", fill="both", expand=True)

    # df를 외부 범위(show_chart 함수 내부)에서 참조할 수 있게 선언 필요
    current_df = None

    def get_current_price_fdr(code):
        default_code, suffix = code.split('.')

        selected = config.MY_INFO[0]['market_type']

        # 오늘과 7일 전 날짜 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # 형식 변환
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # 넉넉한 기간으로 조회
        # 라디오 버튼 값에 따라 소스 접두어 설정
        ticker = code.split('.')
        print(ticker)
        if selected == 0:  # Naver
            symbol = f"NAVER:{ticker[0]}"
        elif selected == 1:  # KRX
            symbol = ticker[0]
        elif selected == 2:  # Yahoo
            symbol = f"YAHOO:{default_code}.{suffix}"  # 야후는 .KS 접미사 필요
        else:
            symbol = code
        try:
            df = fdr.DataReader(symbol, start=start_str, end=end_str)
            return df
        except Exception as e:
            print(f"📡 fdr 데이터 로드 오류 ({symbol}): {e}")
        return 0

    def update_price():
        nonlocal current_df, price_label  # 상위 함수의 변수를 수정하겠다고 선언

        try:
            # 실시간 데이터 가져오기 (직접 만드신 함수 활용)
            data = get_current_price_fdr(ticker_code)
            if data is not None and not data.empty:
                current_df = data
                realtime_price = current_df['Close'].iloc[-1]
                # 실시간 가격 업데이트
                price_label.config(text=f"현재가: {realtime_price:,}원")

                # 필요하다면 여기서 캔들 차트를 갱신하는 canvas.draw_idle() 호출
        except Exception as e:
            print(f"업데이트 오류: {e}")

        # 1초 후 자기 자신을 다시 호출 (무한 루프)
        chart_window.after(1000, update_price)

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

        ax = axes[0]
        # 캔버스 배치
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        # 폰트 경로 설정 (Windows 기준 '맑은 고딕')
        # 만약 맥이라면 font_path = "/Library/Fonts/AppleGothic.ttf" 로 변경
        font_path = "C:/Windows/Fonts/malgun.ttf"
        font_prop = fm.FontProperties(fname=font_path, size=10)  # 폰트 속성 생성

        # 1. 캔들 차트의 데이터(close)와 날짜를 접근하기 쉽게 준비
        cursor_annotation = ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                        textcoords="offset points",
                                        bbox=dict(boxstyle="round", fc="w"),
                                        arrowprops=dict(arrowstyle="->"))
        cursor_annotation.set_visible(False)




        def on_mouse_move(event):
            if not event.inaxes == ax:
                cursor_annotation.set_visible(False)
                canvas.draw_idle()
                return

            # 마우스 x좌표에 가장 가까운 인덱스 찾기
            x_idx = int(round(event.xdata))
            if 0 <= x_idx < len(df):
                # 해당 인덱스의 종가(Close) 가져오기
                close_price = df['Close'].iloc[x_idx]
                date_str = df.index[x_idx].strftime('%Y-%m-%d')
                cursor_annotation.set_fontproperties(font_prop)
                # 텍스트 및 위치 업데이트
                cursor_annotation.set_text(f"가격: {close_price:,}")
                cursor_annotation.xy = (x_idx, close_price)
                cursor_annotation.set_visible(True)
                canvas.draw_idle()

        def limit_check_and_apply(ax):
            # 1. 모든 날짜 데이터를 숫자로 변환 (비교의 기준을 float로 통일)
            # df.index는 이미 정렬되어 있으므로 처음과 끝을 바로 숫자로 변환
            df_indices = mdates.date2num(df.index)
            min_limit = df_indices.min()
            max_limit = df_indices.max()

            # 2. 현재 축 범위 (숫자값)
            cur_min, cur_max = ax.get_xlim()

            # 3. 현재 보이는 캔들 개수 확인 (숫자 범위 내에 있는 데이터 개수)
            # 데이터 자체가 아닌 '숫자'로 범위를 필터링
            visible_count = len([val for val in df_indices if cur_min <= val <= cur_max])

            # 4. 제한 적용 로직
            # 캔들이 너무 적으면 확대 방지
            if visible_count < 5:
                return

            # 범위를 벗어나면 강제 조정
            needs_redraw = False
            new_min, new_max = cur_min, cur_max

            if cur_min < min_limit:
                new_min = min_limit
                needs_redraw = True
            if cur_max > max_limit:
                new_max = max_limit
                needs_redraw = True

            if needs_redraw:
                ax.set_xlim(new_min, new_max)
                canvas.draw_idle()

        # 축 범위가 변할 때마다 호출
        ax.callbacks.connect('xlim_changed', limit_check_and_apply)

        # 휠 이벤트 연결 (이제 휠 줌도 축 범위 변경을 유발하므로 자동으로 위의 함수가 작동함)
        def on_scroll(event):
            if event.inaxes != ax: return
            base_scale = 1.2
            scale = 1 / base_scale if event.button == 'up' else base_scale

            cur_xlim = ax.get_xlim()
            xdata = event.xdata
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale
            relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])

            ax.set_xlim(xdata - new_width * (1 - relx), xdata + new_width * relx)
            canvas.draw_idle()

        fig.canvas.mpl_connect('scroll_event', on_scroll)
        fig.canvas.mpl_connect('motion_notify_event', on_mouse_move)

        # 툴바 배치 (줌/이동 가능)
        toolbar = NavigationToolbar2Tk(canvas, chart_frame)
        toolbar.update()
        toolbar.pack(side="bottom", fill="x")
        toolbar.pan()

    # 4. 버튼 생성
    types = [("1주", 0), ("1달", 1), ("3달", 2), ("1년", 3)]
    for text, val in types:
        btn = tk.Button(button_frame, text=text, command=lambda v=val: on_button_click(v))
        btn.pack(side="left", padx=5)


    # 5. 초기 호출 (기본값 년/3)
    on_button_click(0)
    # 차트 창이 열릴 때 업데이트 시작
    update_price()
