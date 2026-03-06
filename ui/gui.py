import tkinter as tk
from tkinter import ttk
import threading  # 추가 누락됨
import yfinance as yf
import config
from datetime import datetime
import pytz # 시간대 설정을 위해 설치 필요 (pip install pytz)
from services.tickers_manage import open_user_mgmt_logic
from services.user_manage import open_user_discord

# --- [GUI 클래스] ---
class StockApp:
    def __init__(self, root, watchlist):  # main에서 watchlist를 받아옴
        self.root = root
        self.root.title("주가 모니터 & 알리미")
        self.root.geometry("700x550")  # 버튼 공간을 위해 높이 약간 조절

        self.timer_id = None
        self.ui_update_id = None


        self.watchlist = watchlist
        self.update_interval = config.TEN
        self.selected_ticker = None

        # 딕셔너리 컴프리헨션으로 초기화
        self.stock_info = {info[0]: {'price': 0, 'open': 0} for info in self.watchlist.values()}

        # --- 상단 레이아웃 ---
        self.label = tk.Label(root, text="📈 실시간 주가 모니터링", font=("맑은 고딕", 16, "bold"), pady=10)
        self.label.pack()

        self.mode_label = tk.Label(root, text=f"현재 모드: 일반 ({config.TEN}초 주기)", fg="blue")
        self.mode_label.pack()

        self.cur_time = tk.Label(root, text=f"현재 시간:00시 00분 00초", fg="black")
        self.cur_time.pack()

        # --- 버튼 프레임 ---
        self.button_frame = tk.Frame(root, pady=10)
        self.button_frame.pack()

        self.refresh_btn = tk.Button(self.button_frame, text="🔄 즉시 갱신", command=self.manual_refresh, width=12)
        self.refresh_btn.pack(side="left", padx=5)

        self.ticker_btn = tk.Button(self.button_frame, text="📊 종목 관리", command=self.open_user_mgmt, width=12)
        self.ticker_btn.pack(side="left", padx=5)

        self.user_btn = tk.Button(self.button_frame, text="👤 사용자 관리", command=self.open_user_manage, width=12)
        self.user_btn.pack(side="left", padx=5)

        # --- 표(Treeview) 설정 ---
        self.tree = ttk.Treeview(root, columns=("name", "open", "current", "target"), show="headings", height=12)
        self.tree.heading("name", text="종목명")
        self.tree.heading("open", text="시작가")
        self.tree.heading("current", text="현재가")
        self.tree.heading("target", text="목표가")

        for col in ("name", "open", "current", "target"):
            self.tree.column(col, width=140, anchor="center")
        self.tree.pack(padx=20, pady=10)

        # --- 이벤트 및 쓰레드 ---
        self.interrupt_event = threading.Event()
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.root.bind("<Escape>", self.on_esc)

        # 데이터 수집 쓰레드 실행
        threading.Thread(target=self.data_fetch_loop, daemon=True).start()
        self.get_time()
        # UI 갱신 루프 시작
        self.update_ui_loop()

    def open_user_manage(self):
        open_user_discord(self, config.MY_INFO)

    def get_time(self):
        self.cur_time.config(text=f"⏰ 현재 시각: {self.get_current_hour_kr()}", fg="black")
        self.timer_id = self.root.after(1000 , self.get_time)

    def get_current_hour_kr(self):
        # 1. 한국 시간대 설정
        tz_kr = pytz.timezone('Asia/Seoul')

        # 2. 현재 시간 가져오기
        now = datetime.now(tz_kr)

        # 3. "21시" 형식으로 포맷팅
        # %H는 24시간 형식(00~23), %I는 12시간 형식(01~12)입니다.
        formatted_time = now.strftime("%H시 %M분 %S초")

        return formatted_time

    def data_fetch_loop_cur(self):
        for info in self.watchlist.values():
            code, name, target = info
            try:
                stock = yf.Ticker(code)
                # 1. 현재가는 계속 업데이트
                self.stock_info[code]['price'] = stock.fast_info.last_price

                # 2. 시작가는 0일 때만 (최초 1회) 가져오기
                if self.stock_info[code]['open'] == 0:
                    # history 사용이 더 정확함
                    # 오늘 날짜를 YYYY-MM-DD 형식으로 가져옵니다.
                    today = datetime.now().strftime('%Y-%m-%d')
                    hist = stock.history(start=today)
                    if not hist.empty:
                        self.stock_info[code]['open'] = hist['Open'].iloc[0]
            except Exception as e:
                print(f"📡 데이터 수집 오류 ({code}): {e}")

    def data_fetch_loop(self):
        """네트워크 통신 전담 쓰레드"""
        while True:
            for info in self.watchlist.values():
                code, name, target = info
                try:
                    stock = yf.Ticker(code)
                    # 1. 현재가는 계속 업데이트
                    self.stock_info[code]['price'] = stock.fast_info.last_price

                    # 2. 시작가는 0일 때만 (최초 1회) 가져오기
                    if self.stock_info[code]['open'] == 0:
                        # history 사용이 더 정확함
                        # 오늘 날짜를 YYYY-MM-DD 형식으로 가져옵니다.
                        today = datetime.now().strftime('%Y-%m-%d')
                        hist = stock.history(start=today)
                        if not hist.empty:
                            self.stock_info[code]['open'] = hist['Open'].iloc[0]
                except Exception as e:
                    print(f"📡 데이터 수집 오류 ({code}): {e}")

            # 대기 상태 (이벤트 발생 시 즉시 깨어남)
            is_interrupted = self.interrupt_event.wait(timeout=self.update_interval)
            if is_interrupted:
                self.interrupt_event.clear()


    def update_ui_loop(self):
        #만약 이미 예약된 작업이 있다면 취소 (중복 실행 방지)
        if self.ui_update_id is not None:
            self.root.after_cancel(self.ui_update_id)

        # """UI 갱신만 담당"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        for info in self.watchlist.values():
            code, name, target = info
            price = self.stock_info[code]['price']
            open_p = self.stock_info[code]['open']
            unit = "원" if ".KS" in code or ".KQ" in code else "$"

            # 가격 변동에 따른 색상 태그 설정
            if price > open_p and open_p != 0:
                tag, display = 'up', f"▲ {int(float(price)):,}"
            elif price < open_p and open_p != 0:
                tag, display = 'down', f"▼ {int(float(price)):,}"
            else:
                tag, display = 'none', f"  {int(float(price)):,}"

            applied_tags = [tag]
            if code == self.selected_ticker:
                applied_tags.append('selected')

            self.tree.insert("", tk.END,
                             values=(name, f"{int(float(open_p)):,}{unit}", f"{display}{unit}", f"{int(float(target)):,}{unit}"),
                             tags=tuple(applied_tags))

        self.tree.tag_configure('up', foreground='red')
        self.tree.tag_configure('down', foreground='blue')
        self.tree.tag_configure('selected', background='#e1f5fe')

        # 다음 갱신 예약
        self.ui_update_id = self.root.after(1000 if self.update_interval <= 1 else 5000, self.update_ui_loop)

    def stop_ui_update(self):
        # 외부에서 종료하고 싶을 때
        if self.ui_update_id is not None:
            self.root.after_cancel(self.ui_update_id)
            self.ui_update_id = None

    def manual_refresh(self):
        self.interrupt_event.set()
        self.watchlist = config.WATCHLIST

        # 1. 현재 watchlist에 존재하는 모든 종목코드 집합을 미리 만듭니다.
        # (info[0]이 종목코드입니다)
        current_codes = {info[0] for info in self.watchlist.values()}

        # 2. stock_info에만 있는(삭제된) 종목코드들을 찾습니다.
        tickers_to_remove = [t for t in self.stock_info if t not in current_codes]

        # 3. 삭제
        for t in tickers_to_remove:
            del self.stock_info[t]

        # 4. 추가된 종목이 있다면 stock_info에 초기값 세팅 (없으면 패스)
        for code in current_codes:
            if code not in self.stock_info:
                self.stock_info[code] = {'price': 0, 'open': 0}

        self.update_ui_loop()

    def open_user_mgmt(self):  # 이름을 살짝 바꿔주면 더 명확합니다.
        open_user_mgmt_logic(self)

    def on_select(self,event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            name = item['values'][1]
            for info in self.watchlist.values():
                if info[1] == name:
                    self.selected_ticker = info[0]
                    break
            self.update_interval = config.ONE
            self.mode_label.config(text=f"🔥 집중 모드: {name} ({config.ONE}초 주기)", fg="purple")
            # self.manual_refresh()

    def on_esc(self,event):
        self.update_interval = config.TEN
        self.selected_ticker = None
        self.mode_label.config(text=f"현재 모드: 일반 ({config.TEN}초 주기)", fg="blue")
        self.manual_refresh()
