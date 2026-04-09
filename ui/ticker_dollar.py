import tkinter as tk
from services.ai_model import ai_model
import services.ui_helper as helper
from matplotlib.ticker import FuncFormatter
import locale
import threading
import services.KRX as krx
import services.RSS as rss
# 시스템에 따라 'ko_KR.UTF-8' 또는 'ko_KR'을 사용합니다.
try:
    locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')
except:
    locale.setlocale(locale.LC_TIME, 'ko_KR')

class DollarCart:
    def __init__(self, app):
        import matplotlib.font_manager as fm
        self.app = app
        self.root = app.root
        font_list = fm.findSystemFonts(fontpaths=None, fontext='ttf')
        malgun_bold = [f for f in font_list if 'malgunbd' in f.lower()][0]
        self.font_prop = fm.FontProperties(fname="C:/Windows/Fonts/malgun.ttf", size=10)  # 폰트 속성 생성
        self.font_prop_bold = fm.FontProperties(fname=malgun_bold, size=10)  # 폰트 속성 생성
        self.loading = helper.LoadingWindow(self.root)

        self.ax = None
        self.canvas = None
        self.is_dragging = False
        self.has_ai_prediction = False
        self.press_data_x = 0  # 드래그 시작 시의 마우스 x좌표
        self.press_pixel_x = 0
        self.is_running = False
        self.news = None
        self.init_ui()
        # # 4. 무거운 작업은 스레드로 시작
        self.loading.show_progress("달러의 정보를 가져오는 중 입니다...\n잠시만 기다려주세요...")
        thread = threading.Thread(target=self.load_data_async, daemon=True)
        thread.start()

    def stop_loading_process(self):
        # 로딩 창을 닫고 프로그레스바 중지
        if hasattr(self.loading, 'window'):
            self.loading.progress.stop()
            self.loading.window.destroy()
            print("✅ 주가 데이터 업데이트 완료 및 로딩창 종료")

    def load_data_async(self):
        """백그라운드에서 데이터를 가져오는 함수 (Worker Thread)"""
        try:
            # 무거운 작업들 수행
            from services.dart import dart
            self.dart_instance = dart
            self.original_df = self.get_date_range()
            self.full_df = self.original_df.copy()
            self.gold_open_price = self.original_df["Open"].iloc[-1]
            self.last_mouse_idx = len(self.full_df) - 1

            # UI 업데이트는 반드시 메인 스레드에서! (Android의 runOnUiThread)
            self.root.after(0, self.on_data_loaded)
        except Exception as e:
            print(f"데이터 로드 중 오류 발생: {e}")

    def on_data_loaded(self):
        """데이터 로드가 끝난 후 UI를 갱신 (Main Thread)"""
        try:
            # 1. 루트 윈도우가 실존하는지 먼저 확인
            if not self.root.winfo_exists():
                return
            self.stop_loading_process()
            # 2. 실제 UI 업데이트 로직 수행
            # 이 내부에서 위젯이 파괴되어 에러가 나더라도 except에서 잡힙니다.
            self.init_chart()
            self.update_price()
            self.get_news_loading()

        except (tk.TclError, AttributeError, RuntimeError) as e:
            # 창이 닫히는 도중에 발생하는 모든 UI 관련 에러를 무시합니다.
            print(f"UI 업데이트 중단 (창이 이미 닫힘): {e}")

    def init_ui(self):
        from tkinter import ttk
        from tkinter import scrolledtext

        # 1. 새 창 설정
        self.chart_window = tk.Toplevel(self.root)
        self.chart_window.title("달러 실시간 차트")
        self.chart_window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.chart_window.iconbitmap(helper.CHART_ICON_PATH)
        helper.center_window(self.chart_window, 1200, 800, self.root)

        top_frame = tk.Frame(self.chart_window)
        top_frame.pack(side="top", fill="x", pady=5)
        top_frame.grid_columnconfigure(0, weight=1)  # 왼쪽 빈 공간
        top_frame.grid_columnconfigure(1, weight=0)  # 종목명 (고정)
        top_frame.grid_columnconfigure(2, weight=0)  # 현재가 (고정)
        top_frame.grid_columnconfigure(3, weight=1)  # 오른쪽 빈 공간

        # 2. 종목명 레이블 (grid 사용)
        self.ticker_name_label = tk.Label(top_frame, text="1달러", font=("Arial", 14, "bold"))
        self.ticker_name_label.grid(row=0, column=1, padx=10)
        # 3. 실시간 금액 레이블 (grid 사용)
        self.price_label = tk.Label(top_frame, text="로딩 중...", font=("Arial", 14), fg="blue")
        self.price_label.grid(row=0, column=2, padx=10)
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

        self.ai_title = tk.Label(self.ai_frame, text="관련 뉴스", font=("Arial", 14, "bold"), bg="#f0f0f0")
        self.ai_title.pack(pady=5)

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
        self.tree.heading("title", text="공시 제목")
        self.tree.column("date", width=40, anchor="center")
        self.tree.column("title", width=270, anchor="w")
        self.tree.column("rcp_no", width=0, stretch=tk.NO)  # 접수번호는 화면에서 숨김

        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<Double-1>", self.on_tree_click)  # 더블 클릭 시 실행


        tk.Label(self.ai_frame, text="📝 선택한 뉴스 요약", font=("Arial", 10, "bold")).pack(pady=5)

        # 3. 상세 요약 텍스트 창
        self.news_summary = scrolledtext.ScrolledText(self.ai_frame, wrap=tk.WORD, font=("Malgun Gothic", 10), height=15)
        self.news_summary.pack(padx=10, pady=10, fill="both", expand=True)

        # 4. 버튼 생성
        types = [("1주", 0), ("1달", 1), ("3달", 2), ("1년", 3)]
        for text, val in types:
            btn = tk.Button(button_frame, text=text, command=lambda v=val: self.on_draw_chart(v))
            btn.pack(side="left", padx=5)

        reset_btn = tk.Button(button_frame, text="초기화", command=self.reset_chart)
        reset_btn.pack(side="right", padx=5)

        self.active_var = tk.BooleanVar(value=True)
        tk.Checkbutton(button_frame, text="상세 표시", variable=self.active_var, command=self.on_toggle).pack(side='right',padx=5)
        self.is_show_cur_info = True

    def get_news_loading(self):
        thread = threading.Thread(target=self.news_thread, daemon=True)
        thread.start()

    def news_thread(self):
        """실제 데이터를 가져오는 작업 (백그라운드 스레드)"""
        try:
            self.tree.insert("", "end", values=("", "관련 뉴스 로딩중...", ""))

            self.news = rss.pull_request_news("달러 시세")

            # 데이터를 다 가져왔으면 UI 업데이트 함수 호출 (스케줄링)
            if hasattr(self, 'chart_window') and self.chart_window.winfo_exists():
                self.chart_window.after(0, self.update_news_ui)
            else:
                print("데이터 로드 완료 후 확인 결과: 차트 창이 이미 닫혔습니다.")

        except Exception as e:
            error_msg = f"데이터 로드 실패: {e}"

    def check_trading_signals(self, df):
        # 1. 골든크로스 체크
        ma5 = df['Close'].rolling(window=5).mean()
        ma20 = df['Close'].rolling(window=20).mean()

        if ma5.iloc[-2] < ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]:
            import services.alert as alert
            unit = helper.data_unit(0)
            alert.send_stock_alim("🚀 골든크로스 발생! 매수 타이밍 검토 필요.",f"{self.gold.name} : {int(df['Close'].iloc[-1]):,}{unit}")

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
                                       returnfig=True, figsize=(7, 5), tight_layout=True, volume=False,
                                       scale_padding=dict(left=1.2, right=1.2, top=1.2, bottom=1.2))

        self.ax = self.axes[0]
        self.ax.set_ylabel("1달러 (KRW)")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

        # Annotation 초기화
        self.cursor_annotation = self.ax.annotate("", xy=(0, 0), xytext=(15, 15), zorder=10,
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

    def update_news_ui(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not hasattr(self, "news") or not self.news:
            return

        # 2. 뉴스 리스트 순회
        for news in self.news:
            # news는 리스트 안의 딕셔너리입니다.
            date = news.get('pubDate', '')
            title = news.get('title', '')

            # 데이터가 있을 때만 트리뷰에 삽입
            if date and title:
                # values=(첫번째칸, 두번째칸, ...) 순서대로 들어갑니다.
                self.tree.insert("", "end", values=(date.split(' ')[0], title))

    def on_tree_click(self, event):
        # 1. 초기화 및 대기 메시지 표시
        self.news_summary.config(state="normal")
        self.news_summary.delete("1.0", tk.END)
        self.news_summary.insert(tk.END, "🤖 AI 분석 요청 중입니다. 잠시만 기다려 주세요...", "header")  # 태그 적용 가능
        self.news_summary.update_idletasks()  # 메시지 즉시 렌더링

        # 2. 데이터 가져오기
        try:
            selected_item = self.tree.selection()[0]
            index = self.tree.index(selected_item)
            # AI 요약 결과 받아오기
            cur_news = self.news[index]
            target_news_content = rss.pull_news_content(cur_news)
            result = ai_model.get_ai_news_summary(target_news_content)

            # 3. [핵심] UI 업데이트 함수 하나로 모든 강조 처리를 끝냅니다.
            self.update_summary_ui(result)

        except IndexError:
            pass  # 아이템 선택이 안 된 경우 무시
        except Exception as e:
            self.news_summary.insert(tk.END, f"\n⚠️ 에러 발생: {e}")

    def setup_text_tags(self):
        # 기존 태그들...
        self.news_summary.tag_config("header", foreground="#007bff", font=("Malgun Gothic", 12, "bold"))

        # 평점 강조용 색상 태그 추가
        self.news_summary.tag_config("good", foreground="#e74c3c", font=("Malgun Gothic", 12, "bold"))  # 호재 (빨강)
        self.news_summary.tag_config("bad", foreground="#2980b9", font=("Malgun Gothic", 12, "bold"))  # 악재 (파랑)

    def update_summary_ui(self, text):
        self.news_summary.config(state="normal")
        self.news_summary.delete("1.0", tk.END)
        self.setup_text_tags()

        lines = str(text).split('\n')

        for i, line in enumerate(lines):
            content = line.strip()
            if not content: continue

            if i == 0 or "✨" in content:
                # 1. 일단 제목 줄 전체를 넣습니다 (기본 파란색 header 태그)
                start_index = self.news_summary.index(tk.INSERT)
                self.news_summary.insert(tk.END, content + "\n\n", "header")
                end_index = self.news_summary.index(tk.INSERT)

                # 2. 호재/악재 키워드에 따라 색칠 공부 시작
                if "호재" in content:
                    self.highlight_keyword(start_index, end_index, "[평점: 호재]", "good")
                elif "악재" in content:
                    self.highlight_keyword(start_index, end_index, "[평점: 악재]", "bad")

            elif content.startswith("-"):
                self.news_summary.insert(tk.END, content + "\n\n", "bold")
            else:
                self.news_summary.insert(tk.END, content + "\n")

        self.news_summary.config(state="disabled")

    def highlight_keyword(self, start, end, keyword, tag):
        """지정한 범위 내에서 키워드를 찾아 태그를 덧씌우는 함수"""
        pos = self.news_summary.search(keyword, start, stopindex=end)
        if pos:
            # 키워드의 끝 위치 계산
            end_pos = f"{pos} + {len(keyword)}c"
            self.news_summary.tag_add(tag, pos, end_pos)

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
            df = krx.pull_dollar_krw(days=7)
            print(len(df))

            if df is not None and not df.empty:
                realtime_price = df['Close'].iloc[-1]
                # 실시간 가격 업데이트
                # 1. 색상 결정 (로직에 따라)
                if realtime_price > self.gold_open_price and self.gold_open_price != 0:
                    new_color = "red"  # 상승 시 빨간색
                    prefix = "▲ "
                elif realtime_price < self.gold_open_price and self.gold_open_price != 0:
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

                # 2. Label 업데이트 (텍스트와 색상 동시 적용)
                self.price_label.config(
                    text=f"현재가: {prefix}{int(realtime_price):,}원",
                    fg=new_color
                )
                self.refresh_realtime_chart()
                self.check_trading_signals(self.full_df)
        except Exception as e:
            print(f"업데이트 오류: {e}")

    def refresh_realtime_chart(self):
        import mplfinance as mpf

        if not hasattr(self, 'ax') or self.ax is None:
            return

        # 1. 현재 화면에 보이는 범위(X축)를 유지함
        cur_xlim = self.ax.get_xlim()
        self.ax.clear()

        mpf.plot(
            self.full_df,
            type='candle',
            mav=(5, 20, 60),
            ax=self.ax,
            volume=False,
            style=self.s,
        )

        ind = -6 if self.has_ai_prediction else -1

        target_v_line = len(self.full_df) + (ind + 0.2)
        current_price = float(self.full_df['Close'].iloc[ind])

        print(current_price)

        # 4. X축 범위를 복구해서 화면이 튕기지 않게 함
        self.ax.set_xlim(cur_xlim)
        self.ax.set_ylabel("1달러 (KRW)")
        if len(self.axes) > 2:
            vol_ax = self.axes[2]
            vol_ax.set_ylabel("거래량")
            vol_ax.yaxis.set_major_formatter(FuncFormatter(helper.volume_formatter))
        self.ax.yaxis.set_major_formatter(FuncFormatter(self.price_formatter))

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
                    self.cursor_annotation = self.ax.annotate("", xy=(0, 0), xytext=(15, 15), zorder=10,
                                                              textcoords="offset points", color="white",
                                                              fontweight="bold",
                                                              bbox=dict(boxstyle="round", fc="w"),
                                                              arrowprops=dict(arrowstyle="->"))

                    info = helper.calc_ticker_info_position(self, idx)
                    self.show_current_info(idx, info)


        # 6. 유휴 시간에 화면 갱신
        self.canvas.draw_idle()


    def on_draw_chart(self, date_type):
        total_len = len(self.full_df)

        # 0:1주(7), 1:1달(22), 2:3달(66), 3:1년(250)
        view_range = {0: 7, 1: 22, 2: 66, 3: 250}.get(date_type, total_len)

        start_idx = max(0, total_len - view_range)
        end_idx = total_len - 1

        self.ax.set_xlim(start_idx - 1, end_idx + 1)
        helper.calc_max_min_info_position(self)

    def get_date_range(self):
        # 2년치 로드
        df = krx.pull_dollar_krw(days=365)
        print(len(df))
        return df

    def draw_current_candle_data(self, event):
        # 1. 인덱스 계산 및 저장 (기존과 동일)
        x_idx = int(round(event.xdata))
        if 0 <= x_idx < len(self.full_df):
            self.last_mouse_idx = x_idx
            info = helper.calc_ticker_info_position(self, x_idx)
            self.show_current_info(x_idx, info)

    def show_current_info(self, x_idx, info):
        lines = [
            f"시가       {info['open']:>10,.0f}",
            f"종가       {info['close']:>10,.0f}",
            f"최고가     {info['high']:>10,.0f}",
            f"최저가     {info['low']:>10,.0f}",
            f"{info['sep']}",
            f"금일 대비  {info['rate_text']:>10}",
            f"전일 대비  {info['daily_change']:>10}"  # calc에서 만든 포맷팅 활용
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


