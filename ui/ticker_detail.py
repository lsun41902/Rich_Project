import tkinter as tk
from datetime import timedelta, datetime
import services.ui_helper as helper
from matplotlib.ticker import FuncFormatter
import locale
import threading
from services.graph_manager import neo4j
import services.KRX as krx
import services.RSS as rss
from services.ai_model import ai_model
import services.alert as alert
import webbrowser
import textwrap
import pandas as pd

# 시스템에 따라 'ko_KR.UTF-8' 또는 'ko_KR'을 사용합니다.
try:
    locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')
except:
    locale.setlocale(locale.LC_TIME, 'ko_KR')


class CandleCart:
    def __init__(self, app, item_data):
        import matplotlib.font_manager as fm

        self.app = app
        self.root = app.root
        self.ticker_code, self.ticker_name, self.ticker_open_price, self.ticker_stock_type = item_data['Code'], item_data['Name'], item_data[
            'Open'], item_data['Stock_Type']

        font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        malgun_bold = [f for f in font_list if 'malgunbd' in f.lower()][0]
        self.font_prop = fm.FontProperties(fname="C:/Windows/Fonts/malgun.ttf", size=10)  # 폰트 속성 생성
        self.loading = helper.LoadingWindow(self.root)
        self.font_prop_bold = fm.FontProperties(fname=malgun_bold, size=10)  # 폰트 속성 생성

        # [수정] 차트 뼈대를 그릴 객체들 선언
        self.last_report_min = ""  # 정기 보고 중복 방지용
        self.ax = None
        self.canvas = None
        self.is_dragging = False
        self.has_ai_prediction = False
        self.press_data_x = 0  # 드래그 시작 시의 마우스 x좌표
        self.press_pixel_x = 0
        self.is_running = False
        self.dart_news = None
        self.ticker_news = None
        self.init_ui()
        self.loading.show_progress("DART 공시를 가져오는 중입니다...")
        thread = threading.Thread(target=self.load_data_async, daemon=True)
        thread.start()

    def load_data_async(self):
        from services.dart import dart
        self.dart_instance = dart
        self.root.after(0, self.loading.stop)
        self.original_df = self.get_date_range()  # 2년치 원본 데이터 저장
        self.full_df = self.original_df.copy()  # 현재 차트용 데이터
        self.last_mouse_idx = len(self.full_df) - 1
        self.root.after(0, self.update_ui)

    def update_ui(self):
        try:
            # 1. 루트 윈도우가 실존하는지 먼저 확인
            if not self.root.winfo_exists():
                return

            self.init_chart()  # 차트 뼈대 생성
            self.update_price()
            self.start_ai_info_loading()
        except (tk.TclError, AttributeError, RuntimeError) as e:
            print(e)

    def init_ui(self):
        from tkinter import ttk
        from tkinter import scrolledtext

        # 1. 새 창 설정
        self.chart_window = tk.Toplevel(self.root)
        self.chart_window.title(f"{self.ticker_name} 실시간 차트")
        self.chart_window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.chart_window.iconbitmap(helper.CHART_ICON_PATH)
        helper.center_window(self.chart_window, 1200, 800, self.root)

        top_frame = tk.Frame(self.chart_window)
        top_frame.pack(side="top", fill="x", pady=5)
        top_frame.grid_columnconfigure(0, weight=1)  # 왼쪽 빈 공간
        top_frame.grid_columnconfigure(1, weight=0)  # 종목명 (고정)
        top_frame.grid_columnconfigure(2, weight=0)  # 현재가 (고정)
        top_frame.grid_columnconfigure(3, weight=0)  # 진단 (고정)
        top_frame.grid_columnconfigure(4, weight=1)  # 오른쪽 빈 공간

        # 2. 종목명 레이블 (grid 사용)
        ticker_name_label = tk.Label(top_frame, text=f"{self.ticker_name}", font=("Arial", 14, "bold"))
        ticker_name_label.grid(row=0, column=1, padx=10)
        # 3. 실시간 금액 레이블 (grid 사용)
        self.price_label = tk.Label(top_frame, text="로딩 중...", font=("Arial", 14), fg="blue")
        self.price_label.grid(row=0, column=2, padx=10)
        # 4. 종목 진단
        analyze_ticker_btn = tk.Button(top_frame, text="진단", command=self.analyze_info)
        analyze_ticker_btn.grid(row=0, column=3, padx=10)

        # [핵심] 2. 레이아웃 프레임 분리
        # 상단 버튼 영역
        button_frame = tk.Frame(self.chart_window)
        button_frame.pack(side="top", fill="x", padx=5, pady=5)

        right_frame = tk.Frame(self.chart_window)
        right_frame.pack(side="bottom", fill="both", expand=True)

        # 하단 차트 영역 (이 영역을 draw_professional_chart가 사용)
        self.chart_frame = tk.Frame(right_frame)
        self.chart_frame.pack(side="left", fill="both", expand=True)

        self.ai_frame = tk.Frame(right_frame, width=400, bg="#f0f0f0", bd=2, relief="sunken")
        self.ai_frame.pack(side="right", fill="both")

        header_container = tk.Frame(self.ai_frame, bg="#f0f0f0")
        header_container.pack(fill="x", pady=10)

        self.view_mode = tk.IntVar(value=1)  # 0: 공시, 1: 뉴스

        tk.Radiobutton(header_container, text="공시", variable=self.view_mode, value=0,
                       font=("Arial", 10, "bold"), bg="#f0f0f0", command=self.on_mode_change).pack(side="left")

        tk.Radiobutton(header_container, text="뉴스", variable=self.view_mode, value=1,
                       font=("Arial", 10, "bold"), bg="#f0f0f0", command=self.on_mode_change).pack(side="left")

        # [핵심] 1. Treeview로 리스트 구현
        tree_container = tk.Frame(self.ai_frame)
        tree_container.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("date", "title", "rcp_no")  # rcp_no는 숨겨둘 열
        scrollbar_y = tk.Scrollbar(tree_container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=12,
                                 yscrollcommand=scrollbar_y.set)
        scrollbar_y.config(command=self.tree.yview)

        # 컬럼 설정
        self.tree.heading("date", text="날짜")
        self.tree.heading("title", text="제목")
        self.tree.column("date", width=40, anchor="center")
        self.tree.column("title", width=270, anchor="w")
        self.tree.column("rcp_no", width=0, stretch=tk.NO)  # 접수번호는 화면에서 숨김

        self.tree.pack(side="left", fill="both", expand=True)

        # [핵심] 2. 클릭 이벤트 연결
        self.tree.bind("<Double-1>", self.on_tree_click)  # 더블 클릭 시 실행

        tk.Label(self.ai_frame, text="📝 요약", font=("Arial", 10, "bold")).pack(pady=5)

        aigent_container = tk.Frame(self.ai_frame)
        aigent_container.pack(fill="both", expand=True)
        # 3. 상세 요약 텍스트 창
        self.ai_summary = scrolledtext.ScrolledText(aigent_container, wrap=tk.WORD, font=("Malgun Gothic", 10),
                                                    height=15)
        self.ai_summary.pack(padx=10, pady=10, fill="both", expand=True)

        # 4. 버튼 생성
        types = [("1주", 0), ("1달", 1), ("3달", 2), ("1년", 3)]
        for text, val in types:
            btn = tk.Button(button_frame, text=text, command=lambda v=val: self.on_draw_chart(v))
            btn.pack(side="left", padx=5)

        self.search_var = tk.StringVar()
        self.hint_text = "특정 키워드 분석 하기"
        self.ent_search = tk.Entry(header_container, textvariable=self.search_var, fg='gray')
        self.ent_search.insert(0, self.hint_text)
        self.ent_search.pack(side="left", pady=5)
        self.ent_search.bind("<Return>", self.analyze_price)
        self.ent_search.bind("<FocusIn>", self.on_focus_in)
        self.ent_search.bind("<FocusOut>", self.on_focus_out)

        analyze_btn = tk.Button(header_container, text="검색", command=self.analyze_price)
        analyze_btn.pack(side="left", padx=5)

        self.active_var = tk.BooleanVar(value=True)
        tk.Button(button_frame, text="초기화", command=self.reset_chart).pack(side="right", padx=5)
        tk.Button(button_frame, text="📝 가격 예측", command=self.get_ai_price).pack(side="right", padx=5)
        tk.Checkbutton(button_frame, text="상세 표시", variable=self.active_var, command=self.on_toggle).pack(side='right',
                                                                                                          padx=5)

        self.is_show_cur_info = True

    def analyze_info(self):
        # 2. 작업 완료 후 실행될 내부 함수 정의

        self.loading.show_progress(message=f"주가 변동 원인 분석중...")

        def analyze():
            # 실제 데이터 업데이트 작업 (무거운 작업)
            self.root.after(0, lambda: self.loading.show_progress("최신 뉴스 수집 중..."))
            news_list = rss.pull_request_news(self.ticker_name, 20)
            context = "\n".join([f"• {n['title']}" for n in news_list[:3]])
            if len(news_list) > 3:
                context += "\n..."
            self.root.after(0, lambda: self.loading.show_progress("GENAI 3.1 flash: 분석 중...\n"+context))
            result_msg = ai_model.get_ai_detail_briefing(self.ticker_name, news_list)

            self.root.after(0, lambda: self.finish_analysis(self.ticker_name, f"{result_msg}"))

        thread = threading.Thread(target=analyze, daemon=True)
        thread.start()

    def on_focus_in(self, event):
        helper.set_korean_ime()
        if self.ent_search.get() == self.hint_text:
            self.ent_search.delete(0, tk.END)
            self.ent_search.config(fg='black')

    def on_focus_out(self, event):
        if not self.ent_search.get():
            self.ent_search.insert(0, self.hint_text)
            self.ent_search.config(fg='grey')

    def analyze_price(self, event=None):
        # 2. 작업 완료 후 실행될 내부 함수 정의
        keyword = self.ent_search.get()
        if not keyword:
            self.loading.show_message("분석할 키워드를 입력해주세요!")
            return

        if not neo4j:
            self.loading.show_message("Neo4j 연결이 활성화되지 않았습니다.")
            return

        self.loading.show_progress(message=f"{keyword}(으)로 관련 기사가 등장 했을때\n주가 변화를 분석중...")

        def analyze():
            # 실제 데이터 업데이트 작업 (무거운 작업)
            self.ticker_news_thread()
            result_msg, news_links = neo4j.analyze_keyword_impact(self.ticker_code, keyword)
            detail_news = rss.pull_news_contents(news_links)
            if news_links:
                result2 = ai_model.get_ai_briefing(self.ticker_name, keyword, detail_news)
                result_msg += "\n----------------------------------------------------------------\n"
                self.root.after(0, lambda: self.finish_analysis(keyword, f"{result_msg}{result2}"))
            else:
                self.root.after(0, lambda: self.finish_analysis(keyword, f"{result_msg}"))

        thread = threading.Thread(target=analyze, daemon=True)
        thread.start()

    def finish_analysis(self, keyword, result):
        # 4. 로딩창을 닫고 결과 메시지 출력 (Main Thread 실행)
        self.stop_loading_process()
        self.loading.show_message_scroll(keyword, result)

    def on_mode_change(self):
        # 1. 현재 선택된 값 가져오기 (1: 공시, 2: 뉴스)
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.start_ai_info_loading()

    def on_close(self):
        self.is_running = False  # 스레드에게 중단 신호를 보냄

        if hasattr(self, 'loading') and self.loading:
            self.loading.stop()

        try:
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
            self.chart_window.destroy()
        except:
            pass
        self.chart_window.destroy()

    def on_toggle(self):
        # variable로 설정한 active_var의 현재 값을 가져와 전역 변수에 저장
        self.is_show_cur_info = bool(self.active_var.get())
        # 주석 박스 가시성 조절
        if hasattr(self, 'cursor_annotation'):
            self.cursor_annotation.set_visible(self.is_show_cur_info)

        self.canvas.draw_idle()

    def reset_chart(self):
        self.has_ai_prediction = False
        self.original_df = self.get_date_range()
        self.full_df = self.original_df.copy()
        if hasattr(self, 'ax'):
            total_len = len(self.full_df)
            self.ax.set_xlim(total_len - 30, total_len + 2)
        self.refresh_realtime_chart()

    def get_ai_price(self):
        def work():
            if self.is_running: return
            self.request_ai_price()
            # 4. [수정] GUI 차트 갱신 함수 호출
            self.refresh_realtime_chart()
            self.on_draw_chart(0)
            if hasattr(self, 'loading'):
                self.is_running = False
                self.loading.stop()
        thread = threading.Thread(target=work, daemon=True)
        thread.start()

    def get_default_neo4j_price(self):
        if not neo4j:
            import time
            start_time = time.time()
            helper.log_time("Neo4j가 없습니다.",start_time)
            return
        # 1. 로딩 창 띄우기

        # 2. 작업 완료 후 실행될 내부 함수 정의
        def run_and_stop():
            # 실제 데이터 업데이트 작업 (무거운 작업)
            neo4j.update_stock_data_smart(self, self.ticker_name, self.ticker_code,self.ticker_stock_type)

            # 3. 작업이 끝나면 메인 쓰레드에게 "로딩 창 닫아!"라고 전달
            # self.parent(메인 윈도우)의 after를 사용합니다.
            self.root.after(0, self.stop_loading_process)

        thread = threading.Thread(target=run_and_stop, daemon=True)
        thread.start()
        print(f"🚀 {self.ticker_name} 데이터 적재 쓰레드 시작")

    def stop_loading_process(self):
        # 로딩 창을 닫고 프로그레스바 중지
        if hasattr(self.loading, 'window'):
            self.loading.window.destroy()
            print("✅ 주가 데이터 업데이트 완료 및 로딩창 종료")

    def request_ai_price(self):
        try:
            self.is_running = True
            import pandas as pd
            self.full_df = self.original_df.copy()
            self.root.after(0, lambda: self.loading.show_progress(f"주가와 거래량을 근거로 향후 5일 예측 중..."))

            ai_price = ai_model.get_ai_prediction(self.full_df)
            self.root.after(0, lambda: self.loading.show_progress(f"RSS에서 최근 {self.ticker_name} 뉴스 검색중..."))
            news_list = rss.pull_request_news(self.ticker_name, 20)

            news_summary = "\n".join([news['title'] for news in news_list[:3]])
            self.root.after(0, lambda: self.loading.show_progress(f"{news_summary}..."))
            result_msg = ai_model.get_ai_detail_briefing(self.ticker_name, news_list)
            current_text = self.price_label.cget("text")

            self.root.after(0, lambda: self.loading.show_progress(f"LSTM으로 예측한 결과에\n최근 뉴스의 가산점을 더하는 중..."))
            ai_detail_predict_price = ai_model.get_ai_detail_predict(self.ticker_name, news_list, result_msg, ai_price,
                                                                     current_text)
            last_date = self.full_df.index[-1]
            predict_dates = [last_date + timedelta(days=i) for i in range(1, 6)]

            predict_data = []
            prev_price = self.full_df['Close'].iloc[-1]

            for pred_price in ai_detail_predict_price:
                clean_price = int(pred_price['price'])
                predict_data.append({
                    'Date': predict_dates.pop(0),
                    'Open': int(prev_price),
                    'High': clean_price if clean_price > prev_price else int(prev_price),  # 고가/저가 최소한의 형체 유지
                    'Low': int(prev_price) if clean_price > prev_price else clean_price,
                    'Close': clean_price,
                    'Change': 0,
                    'Volume': 0,
                    'reason': pred_price['reason']
                })
                prev_price = clean_price

            predict_df = pd.DataFrame(predict_data).set_index('Date')

            # 3. [수정] 클래스 변수인 self.full_df를 업데이트하여 모든 기능이 이 데이터를 쓰게 함
            # 원본을 백업해두고 싶다면 self.original_df = self.full_df.copy() 를 먼저 실행하세요.
            self.full_df = pd.concat([self.full_df, predict_df])
            self.full_df['reason'] = self.full_df['reason'].fillna("")
            self.has_ai_prediction = True
        except Exception as e:
            print(f"예측 실패: {e}")
            if hasattr(self, 'loading'):
                self.is_running = False
                self.loading.stop()
            self.loading.show_message("예측 실패!")

    def init_chart(self):
        import mplfinance as mpf
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.ticker import ScalarFormatter, FuncFormatter

        df = self.full_df.sort_index()
        mc = mpf.make_marketcolors(up='red', down='blue', edge='inherit', wick='inherit', volume='inherit',
                                   ohlc='inherit')

        # 스타일 설정 부분 수정
        self.s = mpf.make_mpf_style(base_mpl_style='fast',
                                    marketcolors=mc,
                                    gridstyle='--',
                                    rc={'font.family': 'Malgun Gothic', 'axes.unicode_minus': False})  # 윈도우 기준 '맑은 고딕'

        # [핵심] fig, ax를 self로 저장
        self.fig, self.axes = mpf.plot(df, type='candle', mav=(5, 20, 60), style=self.s,
                                       returnfig=True, figsize=(7, 5), tight_layout=True, volume=True,
                                       scale_padding=dict(left=1.2, right=1.2, top=1.2, bottom=1.2))
        self.ax = self.axes[0]
        self.ax.set_ylabel("주가 (KRW)")
        if len(self.axes) > 2:
            vol_ax = self.axes[2]
            vol_ax.set_ylabel("거래량")
            vol_ax.yaxis.set_major_formatter(FuncFormatter(helper.volume_formatter))

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        # Annotation 초기화
        self.cursor_annotation = self.ax.annotate("", xy=(0, 0), xytext=(15, 15),
                                                  textcoords="offset points", color="white", fontweight="bold",
                                                  bbox=dict(boxstyle="round", fc="w"),
                                                  arrowprops=dict(arrowstyle="->"))
        self.cursor_annotation.set_fontproperties(self.font_prop)

        # Annotation 초기화
        self.cursor_annotation_high = self.ax.annotate("", xy=(0, 0), xytext=(15, 15),
                                                       textcoords="offset points", color="white", fontweight="bold",
                                                       bbox=dict(boxstyle="round", fc="red", alpha=0.8),
                                                       arrowprops=dict(arrowstyle="->", color="red"))
        self.cursor_annotation_high.set_fontproperties(self.font_prop_bold)

        # Annotation 초기화
        self.cursor_annotation_low = self.ax.annotate("", xy=(0, 0), xytext=(15, 15),
                                                      textcoords="offset points", color="white", fontweight="bold",
                                                      bbox=dict(boxstyle="round", fc="blue", alpha=0.8),
                                                      arrowprops=dict(arrowstyle="->", color="blue"))
        self.cursor_annotation_low.set_fontproperties(self.font_prop_bold)

        self.cursor_annotation.set_visible(False)
        self.cursor_annotation_high.set_visible(True)
        self.cursor_annotation_low.set_visible(True)

        formatter = ScalarFormatter()
        formatter.set_scientific(False)
        formatter.set_useOffset(False)
        self.ax.yaxis.set_major_formatter(FuncFormatter(self.price_formatter))

        # 이벤트 연결 (이 시점에 self.ax가 존재하므로 안전함)
        self.ax.callbacks.connect('xlim_changed', lambda event: helper.limit_check_and_apply)
        self.canvas.mpl_connect('scroll_event', lambda event: helper.on_scroll(self, event))
        self.canvas.mpl_connect('button_press_event', lambda event: helper.on_press(self, event))
        self.canvas.mpl_connect('button_release_event', lambda event: helper.on_release(self, event))
        self.canvas.mpl_connect('motion_notify_event', lambda event: helper.on_motion(self, event))

        # 첫 화면(1주)으로 초기 범위 설정
        self.on_draw_chart(0)

    def start_ai_info_loading(self):
        if self.view_mode.get() == 0:
            threading.Thread(target=self.load_ai_data_thread, daemon=True).start()
        else:
            threading.Thread(target=self.ticker_news_thread, daemon=True).start()

    def load_ai_data_thread(self):
        try:
            self.tree.insert("", "end", values=("", "DART 공시 목록 로딩중...", ""))

            self.dart_news = self.dart_instance.get_ticker_news(self.ticker_code)

            # 데이터를 다 가져왔으면 UI 업데이트 함수 호출 (스케줄링)
            if hasattr(self, 'chart_window') and self.chart_window.winfo_exists():
                if self.view_mode.get() == 0:
                    self.chart_window.after(0, self.update_ai_ui)
            else:
                print("데이터 로드 완료 후 확인 결과: 차트 창이 이미 닫혔습니다.")

        except Exception as e:
            error_msg = f"데이터 로드 실패: {e}"

    def update_ai_ui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 2. 데이터가 문자열(에러 메시지 등)인 경우 처리
        if not hasattr(self, "dart_news") or self.dart_news is None:
            return

        lines = self.dart_news.split('\n')
        current_date = ""
        current_title = ""

        for line in lines:
            line = line.strip()

            # 날짜 찾기 (📅 이모지 기준)
            if "📅" in line:
                current_date = line.replace("📅", "").strip()

            # 제목 찾기 (📰 이모지 기준)
            elif "📰" in line:
                content = line.replace("📰", "").strip()
                if "|" in content:
                    current_title, rcp_no = content.split("|")
                else:
                    current_title, rcp_no = content, ""

                if current_date and current_title:
                    # [수정] 3번째 칸에 rcp_no를 정확히 삽입
                    self.tree.insert("", "end", values=(current_date, current_title, rcp_no))
                    current_title = ""

    def ticker_news_thread(self):
        try:
            self.tree.insert("", "end", values=("", "관련 뉴스 로딩중...", ""))

            self.ticker_news = rss.pull_request_news(self.ticker_name)
            neo4j.save_news_to_neo4j(self.ticker_news, self.ticker_code)
            # 데이터를 다 가져왔으면 UI 업데이트 함수 호출 (스케줄링)
            if hasattr(self, 'chart_window') and self.chart_window.winfo_exists():
                if self.view_mode.get() == 1:
                    self.chart_window.after(0, self.update_news_ui)
            else:
                print("데이터 로드 완료 후 확인 결과: 차트 창이 이미 닫혔습니다.")

        except Exception as e:
            error_msg = f"데이터 로드 실패: {e}"
            print(error_msg)

    def update_news_ui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not hasattr(self, "ticker_news") or not self.ticker_news:
            return

        # 2. 뉴스 리스트 순회
        for news in self.ticker_news:
            # news는 리스트 안의 딕셔너리입니다.
            date = news.get('pubDate', '')
            title = news.get('title', '')

            # 데이터가 있을 때만 트리뷰에 삽입
            if date and title:
                # values=(첫번째칸, 두번째칸, ...) 순서대로 들어갑니다.
                self.tree.insert("", "end", values=(date.split(' ')[0], title))

    def on_tree_click(self, event):
        # 1. 초기화 및 대기 메시지 표시
        self.ai_summary.config(state="normal", wrap="word")
        self.ai_summary.delete("1.0", tk.END)
        self.ai_summary.insert(tk.END, "🤖 AI 분석 요청 중입니다. 잠시만 기다려 주세요...", "header")  # 태그 적용 가능
        self.ai_summary.update_idletasks()  # 메시지 즉시 렌더링

        # 2. 데이터 가져오기
        try:
            selected_item = self.tree.selection()[0]
            if self.view_mode.get() == 0:
                values = self.tree.item(selected_item, "values")
                target_rcp_no = values[2]
                target_rcp_text = self.dart_instance.get_notice_content_clean(target_rcp_no)
                context = f"{values[1]}\nGENAI 3.1 flash가 공시 검토중..."

                # 1. 초기화 및 대기 메시지 표시
                self.ai_summary.config(state="normal", wrap="word")
                self.ai_summary.delete("1.0", tk.END)
                self.ai_summary.insert(tk.END, context, "header")  # 태그 적용 가능
                self.ai_summary.update_idletasks()  # 메시지 즉시 렌더링
                result = ai_model.get_ai_summary(target_rcp_text)
                self.update_summary_ui(result)
            else:
                selected_item = self.tree.selection()[0]
                index = self.tree.index(selected_item)
                cur_news = self.ticker_news[index]
                target_news_content = rss.pull_news_content(cur_news)
                context = f"{target_news_content[0]['title']}\nGENAI 3.1 flash가 뉴스 검토중..."

                # 1. 초기화 및 대기 메시지 표시
                self.ai_summary.config(state="normal", wrap="word")
                self.ai_summary.delete("1.0", tk.END)
                self.ai_summary.insert(tk.END, context, "header")  # 태그 적용 가능
                self.ai_summary.update_idletasks()  # 메시지 즉시 렌더링


                result = ai_model.get_ai_news_summary(target_news_content[0]['content'])
                self.update_summary_ui(result, target_news_content[0]['url'])


        except IndexError:
            pass  # 아이템 선택이 안 된 경우 무시
        except Exception as e:
            self.ai_summary.insert(tk.END, f"\n⚠️ 에러 발생: {e}")

    def open_url(self, event):
        # 클릭된 위치의 태그 범위를 찾아 URL을 추출합니다.
        index = self.ai_summary.index(f"@{event.x},{event.y}")
        tags = self.ai_summary.tag_names(index)

        # 우리가 임의로 저장할 'url_데이터' 태그를 찾아 실행합니다.
        for tag in tags:
            if tag.startswith("http"):
                webbrowser.open(tag)
                break

    def setup_text_tags(self):
        # 기존 태그들...
        self.ai_summary.tag_config("header", foreground="#007bff", font=("Malgun Gothic", 12, "bold"))

        # 평점 강조용 색상 태그 추가
        self.ai_summary.tag_config("good", foreground="#e74c3c", font=("Malgun Gothic", 12, "bold"))  # 호재 (빨강)
        self.ai_summary.tag_config("bad", foreground="#2980b9", font=("Malgun Gothic", 12, "bold"))  # 악재 (파랑)

        # ✨ 하이퍼링크 스타일 (진한 파란색 + 밑줄)
        self.ai_summary.tag_config("link", foreground="#0000EE", underline=True)

        # ✨ 마우스 이벤트 바인딩 (이 부분이 있어야 손가락 모양으로 바뀜)
        self.ai_summary.tag_bind("link", "<Enter>", lambda e: self.ai_summary.config(cursor="hand2"))
        self.ai_summary.tag_bind("link", "<Leave>", lambda e: self.ai_summary.config(cursor=""))

    def update_summary_ui(self, text, url=None):
        self.ai_summary.config(state="normal")
        self.ai_summary.delete("1.0", tk.END)
        self.setup_text_tags()

        lines = str(text).split('\n')

        for i, line in enumerate(lines):
            content = line.strip()
            if not content: continue

            if i == 0 or "✨" in content:
                # 1. 일단 제목 줄 전체를 넣습니다 (기본 파란색 header 태그)
                start_index = self.ai_summary.index(tk.INSERT)
                self.ai_summary.insert(tk.END, content + "\n", "header")
                end_index = self.ai_summary.index(tk.INSERT)

                # 2. 호재/악재 키워드에 따라 색칠 공부 시작
                if "호재" in content:
                    self.highlight_keyword(start_index, end_index, "[평점: 호재]", "good")
                elif "악재" in content:
                    self.highlight_keyword(start_index, end_index, "[평점: 악재]", "bad")

                if url:
                    # 링크 텍스트 삽입 시 "link" 태그를 바로 입힙니다.
                    link_start = self.ai_summary.index(tk.INSERT)
                    self.ai_summary.insert(tk.END, "🔗 [기사 원문 보기 (클릭)]\n\n", "link")
                    link_end = self.ai_summary.index(tk.INSERT)

                    # 클릭 이벤트 바인딩: 람다를 사용해 url을 직접 전달하면 open_url 함수를 따로 안 만들어도 됩니다.
                    self.ai_summary.tag_bind("link", "<Button-1>", lambda e: webbrowser.open(url))
            elif content.startswith("-"):
                self.ai_summary.insert(tk.END, content + "\n\n", "bold")
            else:
                self.ai_summary.insert(tk.END, content + "\n")

        self.ai_summary.config(state="disabled")

    def highlight_keyword(self, start, end, keyword, tag):
        """지정한 범위 내에서 키워드를 찾아 태그를 덧씌우는 함수"""
        pos = self.ai_summary.search(keyword, start, stopindex=end)
        if pos:
            # 키워드의 끝 위치 계산
            end_pos = f"{pos} + {len(keyword)}c"
            self.ai_summary.tag_add(tag, pos, end_pos)

    def price_formatter(self, x, pos):
        return f"{int(x):,}"

    def index_formatter(self, x, pos):
        return f"{int(x)}"

    def update_price(self):
        if helper.check_stock_open_close_time():
            self.get_request()
            # 1초 후 자기 자신을 다시 호출 (무한 루프)
            self.chart_window.after(10 * 1000, self.update_price)
        else:
            self.get_request()

    def get_request(self):
        try:
            # 실시간 데이터 가져오기 (직접 만드신 함수 활용)
            df = krx.pull_request_stock(self.ticker_code, days=5,stock_type=self.ticker_stock_type)
            if df is not None and not df.empty:
                realtime_price = df['Close'].iloc[-1]
                # 실시간 가격 업데이트
                # 1. 색상 결정 (로직에 따라)
                if realtime_price > self.ticker_open_price and self.ticker_open_price != 0:
                    new_color = "red"  # 상승 시 빨간색
                    prefix = "▲ "
                elif realtime_price < self.ticker_open_price and self.ticker_open_price != 0:
                    new_color = "blue"  # 하락 시 파란색
                    prefix = "▼ "
                else:
                    new_color = "black"  # 같을 경우 검은색
                    prefix = "  "

                # 2. full_df의 마지막 봉 데이터를 실시간 가격으로 업데이트
                # (고가/저가/종가를 현재가에 맞춰 갱신)
                ind = -6 if self.has_ai_prediction else -1

                last_idx = self.full_df.index[ind]
                self.full_df.at[last_idx, 'Close'] = realtime_price

                # 실시간 고가/저가 갱신 로직 (선택사항)
                if realtime_price > self.full_df.at[last_idx, 'High']:
                    self.full_df.at[last_idx, 'High'] = realtime_price
                if realtime_price < self.full_df.at[last_idx, 'Low']:
                    self.full_df.at[last_idx, 'Low'] = realtime_price
                unit = helper.data_unit(self.ticker_stock_type)
                # 2. Label 업데이트 (텍스트와 색상 동시 적용)
                self.price_label.config(
                    text=f"현재가: {prefix}{int(realtime_price):,}{unit}",
                    fg=new_color
                )
                self.refresh_realtime_chart()
                if alert.check_trading_signals(self.full_df, self.last_report_min, self.ticker_name):
                    now = datetime.now()
                    self.last_report_min = now.strftime("%H:%M")
        except Exception as e:
            print(f"업데이트 오류: {e}")

    def refresh_realtime_chart(self):
        import mplfinance as mpf

        if not hasattr(self, 'ax') or self.ax is None:
            return

        # 1. 현재 화면에 보이는 범위(X축)를 유지함
        cur_xlim = self.ax.get_xlim()
        self.ax.clear()
        if len(self.axes) > 2:  # 거래량 차트가 있다면
            self.axes[2].clear()

        mpf.plot(
            self.full_df,
            type='candle',
            mav=(5, 20, 60),
            ax=self.ax,
            volume=self.axes[2] if len(self.axes) > 2 else False,
            style=self.s,
        )

        ind = -6 if self.has_ai_prediction else -1

        if ind == -6:
            # 5. AI 구간임을 알리는 텍스트 추가 (선택 사항)
            self.ax.text(len(self.full_df) - 3, self.full_df['Close'].iloc[ind],
                         "AI Prediction", color='purple', fontweight='bold', ha='center')

        target_v_line = len(self.full_df) + (ind + 0.2)
        current_price = float(self.full_df['Close'].iloc[ind])

        print(current_price)

        # 4. X축 범위를 복구해서 화면이 튕기지 않게 함
        self.ax.set_xlim(cur_xlim)
        self.ax.set_ylabel("주가 (KRW)")
        if len(self.axes) > 2:
            vol_ax = self.axes[2]
            vol_ax.set_ylabel("거래량")
            vol_ax.yaxis.set_major_formatter(FuncFormatter(helper.volume_formatter))

        self.ax.axhline(
            y=current_price,
            color='black',
            linestyle='-',
            linewidth=1,
            zorder=3  # 봉 차트보다 위(또는 아래)에 그릴지 결정
        )

        self.ax.axvline(
            x=target_v_line,
            color='black',
            linestyle='-',
            linewidth=1,
            ymin=0, ymax=1  # 0(바닥)에서 1(천장)까지 꽉 채운다는 뜻
        )

        # 5. Y축은 현재 화면의 고가/저가에 맞게 자동 조정 (기존 함수 재활용)
        visible_min, visible_max = helper.calc_max_min_info_position(self)
        if visible_min and visible_max:
            self.ax.set_ylim(visible_min * 0.90, visible_max * 1.10)

            # [추가] 기억해둔 마우스 위치에 커서 주석 다시 그리기
            if self.last_mouse_idx is not None:
                idx = self.last_mouse_idx
                if 0 <= idx < len(self.full_df):
                    # 주석 객체 재생성 (ax.clear로 사라졌으므로)
                    self.cursor_annotation = self.ax.annotate("", xy=(0, 0), xytext=(15, 15),
                                                              textcoords="offset points", color="white",
                                                              fontweight="bold",
                                                              bbox=dict(boxstyle="round", fc="w"),
                                                              arrowprops=dict(arrowstyle="->"))

                    info = helper.calc_ticker_info_position(self, idx)
                    self.show_current_info(idx, info)

        self.ax.yaxis.set_major_formatter(FuncFormatter(self.price_formatter))
        # 6. 유휴 시간에 화면 갱신
        self.canvas.draw_idle()



    def on_draw_chart(self, date_type):
        total_len = len(self.full_df)

        # 0:1주(7), 1:1달(22), 2:3달(66), 3:1년(250)
        view_range = {0: 7, 1: 22, 2: 66, 3: 250}.get(date_type, total_len)

        start_idx = max(0, total_len - view_range)
        end_idx = total_len - 1

        # 캔들차트의 X축은 인덱스(0, 1, 2...)이므로 인덱스로 범위를 잡습니다.
        self.ax.set_xlim(start_idx - 1, end_idx + 1)
        helper.calc_max_min_info_position(self)

    def get_date_range(self):
        df = krx.pull_request_stock(self.ticker_code, days=730,stock_type=self.ticker_stock_type)
        self.get_default_neo4j_price()
        return df

    def draw_current_candle_data(self, event):
        # 1. 인덱스 계산 및 저장 (기존과 동일)
        x_idx = int(round(event.xdata))
        if 0 <= x_idx < len(self.full_df):
            self.last_mouse_idx = x_idx
            info = helper.calc_ticker_info_position(self,x_idx)
            self.show_current_info(x_idx, info)

    def show_current_info(self, x_idx, info):
        reason_val = info.get('reason', "")
        wrapped_reason = "\n"+textwrap.fill(str(reason_val), width=15) if reason_val and pd.notna(reason_val) else ""
        lines = [
            f"시가       {info['open']:>10,.0f}",
            f"종가       {info['close']:>10,.0f}",
            f"최고가     {info['high']:>10,.0f}",
            f"최저가     {info['low']:>10,.0f}",
            f"{info['sep']}",
            f"금일 대비  {info['rate_text']:>10}",
            f"전일 대비  {info['daily_change']:>10}",  # calc에서 만든 포맷팅 활용
            f"{info['sep']}",
            f"분석 결과: {wrapped_reason}"
        ]
        display_text = "\n".join(lines)
        if self.is_show_cur_info:
            self.cursor_annotation.set_text(display_text)
            self.cursor_annotation.xy = (x_idx, info['target_y'])
            self.cursor_annotation.set_color(info['text_color'])  # 글자색 변경
            self.cursor_annotation.get_bbox_patch().set_facecolor(info['bg_color'])  # 배경색 변경
            self.cursor_annotation.get_bbox_patch().set_edgecolor("black")  # 테두리도 배경색과 맞춤 (선택사항)
            self.cursor_annotation.set_position(info['offset'])  # 박스 위치 설정
            self.cursor_annotation.set_visible(True)
        else:
            self.cursor_annotation.set_visible(False)

