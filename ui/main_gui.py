import tkinter as tk
from tkinter import ttk
import config
import os
import services.KRX as krx
import services.ui_helper as helper
import pandas as pd
import threading
import services.alert as alert
from datetime import datetime


# --- [GUI 클래스] ---
class StockApp:
    def __init__(self, root, watchlist):  # main에서 watchlist를 받아옴
        import database.connection_SQL as db
        version = "1.2.0"
        self.root = root
        self.root.title(f"주가 모니터 & 알리미 ver:{version}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_finish_out)
        self.root.iconbitmap(helper.MAIN_ICON_PATH)

        helper.center_window(self.root, 700, 550, None)
        self.loading = helper.LoadingWindow(self.root)
        self.already_alerted = set()  # 상태 유지를 위해 생성자에 위치
        self.last_report_min = ""  # 정기 보고 중복 방지용
        self.timer_id = None
        self.ui_update_id = None
        self.watchlist = watchlist
        self.update_interval = config.TEN
        self.selected_ticker = None

        # 딕셔너리 컴프리헨션으로 초기화
        new_data = [
            {
                'Code': item[0],
                'Name': item[1],
                'Target_Price': item[2],
                'Close': 0,  # 초기값
                'Open': 0,  # 초기값
                'ChangesRatio': 0.0,  # 초기값
                'Changes': 0.0  # 초기값
            }
            for item in self.watchlist.values()
        ]
        self.ticker = pd.DataFrame(new_data)

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

        # 시장 선택 레이블 및 버튼
        radio_frame = tk.Frame(root)
        radio_frame.pack(fill='x')
        self.cur_market = tk.IntVar(value=db.get_user_market_type())
        self.market_type = self.cur_market.get()
        self.cur_market.trace_add("write",self._on_market_change)
        tk.Radiobutton(radio_frame, text="KRX", variable=self.cur_market, value=0).pack(side="left", padx=10)
        tk.Button(radio_frame,text="🏅 금 시세", command=self.show_gold_detail).pack(side="left",padx=5)

        self.set_tree_view_type(0)
        tk.Button(radio_frame,text="-TOP 20", command=lambda: self.low_top20()).pack(side="right",padx=5)
        tk.Button(radio_frame,text="+TOP 20", command=lambda: self.high_top20()).pack(side="right",padx=5)
        tk.Button(radio_frame, text="내 종목", command=lambda: self.my_list()).pack(side="right", padx=5)

        # --- 표(Treeview) 설정 ---
        self.tree = ttk.Treeview(root, columns=("name", "open", "current","change", "target"), show="headings", height=12)
        self.tree.heading("name", text="종목명")
        self.tree.heading("open", text="시가")
        self.tree.heading("current", text="현재가")
        self.tree.heading("change", text="금일 대비")
        self.tree.heading("target", text="목표가")

        for col in ("name", "open", "current","change", "target"):
            self.tree.column(col, width=140, anchor="w")
        self.tree.pack(fill='both',padx=5, pady=5,expand=True)

        # --- 이벤트 및 쓰레드 ---
        self.interrupt_event = threading.Event()
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-Button-1>", self.show_detail)
        self.tree.tag_configure('up', foreground='red')
        self.tree.tag_configure('down', foreground='blue')
        self.tree.tag_configure('selected', background='#e1f5fe')
        self.root.bind("<Escape>", self.on_esc)

        # 데이터 수집 쓰레드 실행

        threading.Thread(target=self.data_market, daemon=True).start()
        self.get_time()

    def set_tree_view_type(self,new_type):
        self.tree_type = new_type

    def fetch_and_update(self, view_type):
        self.set_tree_view_type(view_type)  # 타입 설정 (0, 1, 2)

        def worker():
            try:
                self.ticker = self.get_request()
                if self.ticker is not None:
                    self.root.after(0, lambda: self.update_ui_loop(view_type, self.ticker))
            except Exception as e:
                print(f"데이터 로딩 중 오류 발생 (Type {view_type}): {e}")

        threading.Thread(target=worker, daemon=True).start()

    # 2. 개별 버튼 연결 함수 (간결해짐)
    def my_list(self):
        self.loading.show_progress("데이터 가져오는 중...\n잠시만 기다려 주세요...")
        self.fetch_and_update(0)

    def high_top20(self):
        self.loading.show_progress("데이터 가져오는 중...\n잠시만 기다려 주세요...")
        self.fetch_and_update(1)

    def low_top20(self):
        self.loading.show_progress("데이터 가져오는 중...\n잠시만 기다려 주세요...")
        self.fetch_and_update(2)

    def show_krx_top10(self,asc=True):
        df = krx.pull_krx_top20(asc)
        return df


    def show_gold_detail(self):
        from ui.ticker_gold import GoldCart
        GoldCart(self)

    # 4. 콜백 함수 정의 (클래스 내부에 추가)
    def _on_market_change(self, *args):
        # 사용자가 버튼을 누르면 이 함수가 자동으로 실행되어 값을 복사합니다.
        self.market_type = self.cur_market.get()
        print(f"마켓 변경 감지: {self.market_type}")

        # 만약 마켓이 바뀌자마자 쓰레드를 깨우고 싶다면?
        if hasattr(self, 'interrupt_event'):
            self.interrupt_event.set()

    def on_finish_out(self):
        os._exit(0)

    def show_detail(self, event):
        # 1. 트리뷰에서 선택된 아이템의 ID 가져오기
        selected_item = self.tree.focus()
        if not selected_item:
            return
        from ui.ticker_detail import CandleCart

        # 2. 인덱스 번호 추출
        idx = self.tree.index(selected_item)

        # 3. 데이터 추출 (두 가지 방법 중 선택)
        # 방법 A: 리스트로 변환하여 인덱싱 (추천)
        watchlist_list = list(self.watchlist.values())
        ticker_info = watchlist_list[idx]  # [종목코드, 종목명] 등의 튜플/리스트 반환

        # 방법 B: 트리뷰에 이미 출력된 값에서 직접 가져오기 (가장 확실함)
        item_data = self.tree.item(selected_item)
        ticker_name = item_data['values'][0]  # 트리뷰 첫 번째 컬럼값

        ticker_code = ticker_info[0]
        if self.tree_type == 0:
            stock_data = self.ticker[self.ticker['Code'] == ticker_code].iloc[0]
        else:
            stock_data = self.ticker[self.ticker['Name'] == ticker_name].iloc[0]

        # {키: 값} 구조로 된 딕셔너리를 새로 만들어서 넘깁니다.
        item_data = stock_data

        # 4. 차트 호출 (item_data를 통째로 넘기거나 종목명만 넘김)
        CandleCart(self, item_data)

    def open_user_manage(self):
        from ui.user_manage import UserManage
        UserManage(self, config.MY_INFO)

    def get_time(self):
        self.cur_time.config(text=f"⏰ 현재 시각: {self.get_current_hour_kr()}", fg="black")
        self.timer_id = self.root.after(1000, self.get_time)

    def get_current_hour_kr(self):
        import pytz

        # 1. 한국 시간대 설정
        tz_kr = pytz.timezone('Asia/Seoul')

        # 2. 현재 시간 가져오기
        now = datetime.now(tz_kr)

        # 3. "21시" 형식으로 포맷팅
        # %H는 24시간 형식(00~23), %I는 12시간 형식(01~12)입니다.
        formatted_time = f"{now.hour}시 {now.minute}분 {now.second}초"

        return formatted_time

    def update_ui_loop(self, tree_view_type, df):
        print("리스트를 갱신합니다")
        from datetime import datetime
        now = datetime.now()
        # 만약 이미 예약된 작업이 있다면 취소 (중복 실행 방지)
        if self.ui_update_id is not None:
            self.root.after_cancel(self.ui_update_id)

        for item in self.tree.get_children():
            self.tree.delete(item)

        if tree_view_type == 0:
            for i, row in df.iterrows():
                code, name, target = row['Code'], row['Name'],row['Target_Price']
                price = row['Close']
                open_p = row['Open']
                unit = helper.data_unit(0)

                if (now.hour == 9 and now.minute >= 0) or (9 < now.hour < 15) or (now.hour == 15 and now.minute <= 20):
                    # 가격 변동에 따른 색상 태그 설정
                    if price > open_p and open_p != 0:
                        tag, display = 'up', f"▲ {int(float(price)):,}"
                    elif price < open_p and open_p != 0:
                        tag, display = 'down', f"▼ {int(float(price)):,}"
                    else:
                        tag, display = 'none', f"  {int(float(price)):,}"
                else:
                    tag, display = 'none', f"  {int(float(price)):,}"

                diff = price - open_p
                today_change = f"+{diff:,}" if diff > 0 else f"{diff:,}"
                today_change_f = (diff / open_p * 100) if open_p != 0 else 0.0

                applied_tags = [tag]
                if code == self.selected_ticker:
                    applied_tags.append('selected')

                self.tree.insert("", "end",
                                 values=(name, f"{int(float(open_p)):,}{unit}", f"{display}{unit}",
                                         f"{today_change}{unit}({today_change_f:+.1f}%)",
                                         f"{int(float(target)):,}{unit}"),
                                 tags=tuple(applied_tags))
        else:

            unit = helper.data_unit(0)
            for i, row in df.iterrows():
                code, name = row['Code'], row['Name']
                price, open_p = row['Close'], row['Open']

                # 1. 기준을 '시가'가 아닌 '전일 대비 변동폭(Changes)'으로 변경
                change_amt = row['Changes']  # 전일 대비 얼마 올랐나?
                today_change_f = row['ChagesRatio']  # 전일 대비 몇 % 올랐나?

                # 2. 색상 및 화살표 로직 수정
                if change_amt > 0:
                    tag, display = 'up', f"▲ {int(float(price)):,}"
                elif change_amt < 0:
                    tag, display = 'down', f"▼ {int(float(price)):,}"
                else:
                    tag, display = 'none', f"  {int(float(price)):,}"

                # 3. 등락액 표시 (이미 기호가 포함된 경우가 많으니 체크 필요)
                today_change = f"+{int(change_amt):,}" if change_amt > 0 else f"{int(change_amt):,}"

                applied_tags = [tag]
                if code == self.selected_ticker:
                    applied_tags.append('selected')

                self.tree.insert("", "end",
                                 values=(name, f"{int(float(open_p)):,}{unit}", f"{display}{unit}",
                                         f"{today_change}{unit}({today_change_f:+.1f}%)", 0),
                                 tags=tuple(applied_tags))
        if hasattr(self, 'loading') and self.loading:
            self.loading.stop()

    def stop_ui_update(self):
        # 외부에서 종료하고 싶을 때
        if self.ui_update_id is not None:
            self.root.after_cancel(self.ui_update_id)
            self.ui_update_id = None

    def manual_refresh(self):
        self.interrupt_event.set()

    def open_user_mgmt(self):  # 이름을 살짝 바꿔주면 더 명확합니다.
        from ui.tickers_manage_list import TickersManageList
        TickersManageList(self)

    def on_select(self, event):
        self.interrupt_event.set()
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            name = item['values'][0]
            for info in self.watchlist.values():
                if info[1] == name:
                    self.selected_ticker = info[0]
                    break
            self.update_interval = config.ONE
            self.mode_label.config(text=f"🔥 집중 모드: {name} ({config.ONE}초 주기)", fg="purple")

    def on_esc(self, event):
        self.update_interval = config.TEN
        self.selected_ticker = None
        self.mode_label.config(text=f"현재 모드: 일반 ({config.TEN}초 주기)", fg="blue")
        self.manual_refresh()

    def data_market(self):
        if helper.check_stock_open_close_time():
            while self.market_type == 0:
                self.ticker = self.get_request()
                self.root.after(0, lambda :self.update_ui_loop(self.tree_type,self.ticker))
                # 대기 상태 (이벤트 발생 시 즉시 깨어남)
                is_interrupted = self.interrupt_event.wait(timeout=self.update_interval)
                if is_interrupted:
                    self.interrupt_event.clear()
        else:
            self.ticker = self.get_request()
            self.root.after(0, lambda: self.update_ui_loop(self.tree_type, self.ticker))

    def get_request(self):
        df = None
        try:
            if self.tree_type == 0:
                rows = []
                for info in self.watchlist.values():
                    code, name, target = info
                    df_5 = krx.pull_request_stock(code, days=5)

                    if not df_5.empty:
                        # 2. 마지막 줄(오늘 데이터)을 가져옴
                        last_row = df_5.iloc[-1].copy()

                        # 3. 데이터프레임에는 없는 'Name'이나 'Code'를 수동으로 추가
                        last_row['Name'] = name
                        last_row['Code'] = code
                        last_row['Target_Price'] = target

                        rows.append(last_row)  # 리스트에 추가

                    # 4. 반복문이 끝난 후 리스트를 통째로 데이터프레임으로 변환
                df = pd.DataFrame(rows)
                if config.MY_INFO[0].get('is_active', False):
                    self.check_alert(df)
            elif self.tree_type == 1:
                df = self.show_krx_top10(True)
            elif self.tree_type == 2:
                df = self.show_krx_top10(False)
            return df
        except Exception as e:
            print(f"오류 발생: {e}")
            return df

    def check_alert(self, df):
        if df is None or df.empty:
            return

        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        unit = helper.data_unit(0)

        # df를 한 줄씩 돌면서 체크 (이게 가장 정확합니다)
        for _, row in df.iterrows():
            code = row['Code']
            name = row['Name']
            target_val = float(row['Target_Price'])
            current_val = float(row['Close'])

            # 목표가 도달 체크
            if current_val >= target_val:
                if code not in self.already_alerted:
                    msg = f"종목: {name}({code})\n현재가: **{int(current_val):,}{unit}** (목표: {int(target_val):,}{unit})"
                    alert.send_stock_alim("🎯 목표가 달성!", msg)
                    self.already_alerted.add(code)
            else:
                # 목표가 아래로 내려가면 다시 알림 가능 상태로 복구
                if code in self.already_alerted:
                    self.already_alerted.remove(code)

        # 3. 정기 보고 로직 (중복 방지 추가)
        if current_time_str in ["09:00", "15:20"]:
            if self.last_report_min != current_time_str:
                title = "🚀 장 시작 보고" if current_time_str == "09:00" else "🚀 장 마감 보고"
                alert.send_stock_open_close_alim(title, df)
                self.last_report_min = current_time_str  # 이번 분에는 더 이상 안 보냄






