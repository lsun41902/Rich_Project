import tkinter as tk
import config
from datetime import datetime, timedelta
import FinanceDataReader as fdr

from dateutil.relativedelta import relativedelta
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import ScalarFormatter
import matplotlib.font_manager as fm
from services.ui_helper import center_window, check_stock_open_close_time, pull_request_stock
from matplotlib.ticker import FuncFormatter
import locale

# 시스템에 따라 'ko_KR.UTF-8' 또는 'ko_KR'을 사용합니다.
try:
    locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')
except:
    locale.setlocale(locale.LC_TIME, 'ko_KR')


class CandleCart:
    def __init__(self, app, item_data):
        self.app = app
        self.root = app.root
        self.item_data = item_data
        self.open_price = item_data[2]

        font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        malgun_bold = [f for f in font_list if 'malgunbd' in f.lower()][0]
        self.font_prop = fm.FontProperties(fname="C:/Windows/Fonts/malgun.ttf", size=10)  # 폰트 속성 생성

        self.font_prop_bold = fm.FontProperties(fname=malgun_bold, size=10)  # 폰트 속성 생성

        self.full_df = self.get_date_range()
        # [수정] 차트 뼈대를 그릴 객체들 선언

        self.ax = None
        self.canvas = None
        self.is_dragging = False
        self.press_data_x = 0  # 드래그 시작 시의 마우스 x좌표
        self.press_pixel_x = 0

        self.init_ui()
        self.init_chart()  # 차트 뼈대 생성
        self.update_price()

    def init_ui(self):
        # 1. 새 창 설정
        self.chart_window = tk.Toplevel(self.root)
        self.chart_window.title(f"{self.item_data[1]} 실시간 차트")
        center_window(self.chart_window, 800, 600, self.root)

        top_info_frame = tk.Frame(self.chart_window)
        top_info_frame.pack(side="top", fill="x", pady=5)

        top_info_frame.grid_columnconfigure(0, weight=1)  # 왼쪽 빈 공간
        top_info_frame.grid_columnconfigure(1, weight=0)  # 종목명 (고정)
        top_info_frame.grid_columnconfigure(2, weight=0)  # 현재가 (고정)
        top_info_frame.grid_columnconfigure(3, weight=1)  # 오른쪽 빈 공간
        # 2. 종목명 레이블 (grid 사용)
        ticker_name_label = tk.Label(top_info_frame, text=f"{self.item_data[1]}", font=("Arial", 14, "bold"))
        ticker_name_label.grid(row=0, column=1, padx=10)
        # 3. 실시간 금액 레이블 (grid 사용)
        self.price_label = tk.Label(top_info_frame, text="로딩 중...", font=("Arial", 14), fg="blue")
        self.price_label.grid(row=0, column=2, padx=10)
        # [핵심] 2. 레이아웃 프레임 분리
        # 상단 버튼 영역
        button_frame = tk.Frame(self.chart_window)
        button_frame.pack(side="top", fill="x", padx=5, pady=5)

        # 하단 차트 영역 (이 영역을 draw_professional_chart가 사용)
        self.chart_frame = tk.Frame(self.chart_window)
        self.chart_frame.pack(side="top", fill="both", expand=True)

        # 4. 버튼 생성
        types = [("1주", 0), ("1달", 1), ("3달", 2), ("1년", 3)]
        for text, val in types:
            btn = tk.Button(button_frame, text=text, command=lambda v=val: self.on_draw_chart(v))
            btn.pack(side="left", padx=5)

    def init_chart(self):
        df = self.full_df.sort_index()
        mc = mpf.make_marketcolors(up='red', down='blue', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # [핵심] fig, ax를 self로 저장
        fig, axes = mpf.plot(df, type='candle', mav=(5, 20, 60), style=s,
                                  returnfig=True, figsize=(7, 5))
        self.ax = axes[0]

        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        # Annotation 초기화
        self.cursor_annotation = self.ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                                  textcoords="offset points",
                                                  bbox=dict(boxstyle="round", fc="w"),
                                                  arrowprops=dict(arrowstyle="->"))
        self.cursor_annotation.set_fontproperties(self.font_prop)

        # Annotation 초기화
        self.cursor_annotation_high = self.ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                                  textcoords="offset points",color="white",fontweight="bold",
                                                  bbox=dict(boxstyle="round", fc="red",alpha=0.8),
                                                  arrowprops=dict(arrowstyle="->",color="red"))
        self.cursor_annotation_high.set_fontproperties(self.font_prop_bold)

        # Annotation 초기화
        self.cursor_annotation_low = self.ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                                  textcoords="offset points",color="white",fontweight="bold",
                                                  bbox=dict(boxstyle="round",  fc="blue",alpha=0.8),
                                                  arrowprops=dict(arrowstyle="->",color="blue"))
        self.cursor_annotation_low.set_fontproperties(self.font_prop_bold)

        self.cursor_annotation.set_visible(False)
        self.cursor_annotation_high.set_visible(True)
        self.cursor_annotation_low.set_visible(True)

        formatter = ScalarFormatter()
        formatter.set_scientific(False)
        formatter.set_useOffset(False)
        self.ax.yaxis.set_major_formatter(FuncFormatter(self.price_formatter))
        fig.tight_layout()

        # 이벤트 연결 (이 시점에 self.ax가 존재하므로 안전함)
        self.ax.callbacks.connect('xlim_changed', self.limit_check_and_apply)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)

        # 첫 화면(1주)으로 초기 범위 설정
        self.on_draw_chart(0)

    def price_formatter(self, x, pos):
        return f"{int(x):,}"

    def index_formatter(self, x, pos):
        return f"{int(x)}"

    def get_current_price_fdr(self, code):
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

    def update_price(self):
        if check_stock_open_close_time():
            self.get_request()
            # 1초 후 자기 자신을 다시 호출 (무한 루프)
            self.chart_window.after(1000, self.update_price)
        else:
            self.get_request()

    def get_request(self):
        try:
            # 실시간 데이터 가져오기 (직접 만드신 함수 활용)
            df = pull_request_stock(self.item_data[0])
            if df is not None and not df.empty:
                realtime_price = df['Close'].iloc[-1]
                # 실시간 가격 업데이트
                # 1. 색상 결정 (로직에 따라)
                if realtime_price > self.open_price and self.open_price != 0:
                    new_color = "red"  # 상승 시 빨간색
                    prefix = "▲ "
                elif realtime_price < self.open_price and self.open_price != 0:
                    new_color = "blue"  # 하락 시 파란색
                    prefix = "▼ "
                else:
                    new_color = "black"  # 같을 경우 검은색
                    prefix = "  "

                # 2. Label 업데이트 (텍스트와 색상 동시 적용)
                self.price_label.config(
                    text=f"현재가: {prefix}{realtime_price:,}원",
                    fg=new_color
                )
        except Exception as e:
            print(f"업데이트 오류: {e}")


    def on_draw_chart(self, date_type):
        total_len = len(self.full_df)

        # 0:1주(7), 1:1달(22), 2:3달(66), 3:1년(250)
        view_range = {0: 7, 1: 22, 2: 66, 3: 250}.get(date_type, total_len)

        start_idx = max(0, total_len - view_range)
        end_idx = total_len - 1

        # 캔들차트의 X축은 인덱스(0, 1, 2...)이므로 인덱스로 범위를 잡습니다.
        self.ax.set_xlim(start_idx - 0.5, end_idx + 0.5)
        visible_min, visible_max = self.get_visible_max_price()  # 직접 만드신 함수
        self.ax.set_ylim(visible_min * 0.98, visible_max * 1.02)
        self.canvas.draw_idle()

    def get_date_range(self):
        symbol = f"NAVER:{self.item_data[0].split('.')[0]}"
        start_str = (datetime.now() - relativedelta(years=2)).strftime('%Y-%m-%d')
        end_str = datetime.now().strftime('%Y-%m-%d')
        print(f"시작일:{start_str}, 종료일:{end_str}")
        df = fdr.DataReader(symbol, start=start_str, end=end_str)
        print(df.head())
        return df

    # 휠 이벤트 연결 (이제 휠 줌도 축 범위 변경을 유발하므로 자동으로 위의 함수가 작동함)
    def on_scroll(self, event):
        if event.inaxes != self.ax: return
        base_scale = 1.2
        scale = 1 / base_scale if event.button == 'up' else base_scale

        # 1. 현재 축 범위 가져오기
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        # 2. 마우스 위치 기준 잡기
        xdata, ydata = event.xdata, event.ydata

        # 3. 새로운 범위 계산 (X와 Y 동일하게 적용)
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

        # 4. 축 업데이트
        self.ax.set_xlim(xdata - new_width * (1 - relx), xdata + new_width * relx)
        visible_min, visible_max = self.get_visible_max_price()  # 직접 만드신 함수
        self.ax.set_ylim(visible_min * 0.98, visible_max * 1.02)

        self.canvas.draw_idle()

    def get_visible_max_price(self):
        # 1. 현재 화면의 X축 범위 가져오기
        cur_min, cur_max = self.ax.get_xlim()

        # 2. 범위를 정수로 변환 (인덱스처럼 사용)
        start_idx = max(0, int(round(cur_min)))
        end_idx = min(len(self.full_df) - 1, int(round(cur_max)))

        # 3. 해당 범위 내의 데이터 슬라이싱
        visible_data = self.full_df.iloc[start_idx: end_idx + 1]

        # 4. 'High' 컬럼에서 최댓값 찾기
        if not visible_data.empty:
            max_price = visible_data['High'].max()
            min_price = visible_data['Low'].min()

            real_max_idx = start_idx + visible_data.index.get_loc(visible_data['High'].idxmax())
            real_min_idx = start_idx + visible_data.index.get_loc(visible_data['Low'].idxmin())

            self.cursor_annotation_high.set_text(f"가격: {max_price:,}")
            self.cursor_annotation_high.xy = (real_max_idx,max_price)

            self.cursor_annotation_low.set_text(f"가격: {min_price:,}")
            self.cursor_annotation_low.xy = (real_min_idx, min_price)

            return min_price, max_price
        return None

    def on_press(self, event):
        if event.inaxes == self.ax:
            self.is_dragging = True
            self.press_data_x = event.xdata  # 시작 지점 저장
            self.press_pixel_x = event.x

    def on_release(self, event):
        self.is_dragging = False

    def on_motion(self, event):
        if not event.inaxes == self.ax:
            self.cursor_annotation.set_visible(False)
            self.canvas.draw_idle()
            return

        if self.is_dragging:
            # 1. 이동한 픽셀 거리 계산
            dx_pixel = event.x - self.press_pixel_x

            # 2. 픽셀 변화량을 데이터 단위로 환산
            data_range = self.ax.get_xlim()[1] - self.ax.get_xlim()[0]
            width_pixel = self.canvas.get_tk_widget().winfo_width()
            data_shift = (dx_pixel / width_pixel) * data_range

            # 3. 데이터 좌표가 마우스를 따라오도록 이동
            # 클릭 시점의 데이터 좌표(press_data_x)를 현재 마우스 위치(data_shift 보정)에 배치
            target_center = self.press_data_x - data_shift

            # 현재 화면의 너비를 유지하며 이동
            half_width = data_range / 2
            self.ax.set_xlim(target_center - half_width, target_center + half_width)
            visible_min, visible_max = self.get_visible_max_price()  # 직접 만드신 함수
            self.ax.set_ylim(visible_min * 0.98, visible_max * 1.02)

        # 마우스 x좌표에 가장 가까운 인덱스 찾기
        x_idx = int(round(event.xdata))
        if 0 <= x_idx < len(self.full_df):
            # 해당 인덱스의 종가(Close) 가져오기
            close_price = self.full_df['Close'].iloc[x_idx]
            self.cursor_annotation.set_text(f"가격: {close_price:,}")
            self.cursor_annotation.xy = (x_idx, close_price)
            self.cursor_annotation.set_visible(True)
        self.canvas.draw_idle()

    def limit_check_and_apply(self, *args):
        # 1. 인덱스 기반 경계값 설정
        total_len = len(self.full_df)
        min_limit = -0.5
        max_limit = total_len - 0.5

        # 2. 현재 축 범위 가져오기
        cur_min, cur_max = self.ax.get_xlim()

        # 3. 제한 적용 로직 (인덱스 기준)
        needs_redraw = False
        new_min, new_max = cur_min, cur_max

        if cur_min < min_limit:
            new_min = min_limit
            needs_redraw = True
        if cur_max > max_limit:
            new_max = max_limit
            needs_redraw = True

        if needs_redraw:
            self.ax.set_xlim(new_min, new_max)
            self.canvas.draw_idle()

