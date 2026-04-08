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
import time

# --- [GUI 클래스] ---
class StockApp:
    def __init__(self, root, watchlist):  # main에서 watchlist를 받아옴
        start_time = time.time()
        import queries.select as select_db
        version = "1.3.0"
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
        self.last_selected_id = None
        self.check_down_us_ticker_list = False

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
        helper.log_time("ui 생성 시작", start_time)

        # --- 상단 레이아웃 ---
        time_frame = tk.Frame(root)
        time_frame.pack(fill='x',padx=5,pady=5)

        self.mode_label = tk.Label(time_frame, text=f"갱신:({config.TEN}초 주기)", fg="blue")
        self.mode_label.pack(side='left')

        self.cur_time = tk.Label(time_frame, text=f"00시 00분 00초", fg="black")
        self.cur_time.pack(side='right')

        # --- 버튼 프레임 ---
        self.button_frame = tk.Frame(root, pady=10)
        self.button_frame.pack()

        self.refresh_btn = tk.Button(self.button_frame, text="🔄 즉시 갱신", command=self.refresh_data, width=12)
        self.refresh_btn.pack(side="left", padx=5)

        self.ticker_btn = tk.Button(self.button_frame, text="📊 종목 관리", command=self.open_user_mgmt, width=12)
        self.ticker_btn.pack(side="left", padx=5)

        self.user_btn = tk.Button(self.button_frame, text="👤 사용자 관리", command=self.open_user_manage, width=12)
        self.user_btn.pack(side="left", padx=5)

        # 시장 선택 레이블 및 버튼
        radio_frame = tk.Frame(root)
        radio_frame.pack(fill='x')
        self.stock_type = tk.IntVar(value=select_db.select_user_stock_type())
        self.cur_stock = self.stock_type.get()
        self.stock_type.trace_add("write",self.on_stock_change)
        tk.Radiobutton(radio_frame, text="한국 주식", variable=self.stock_type, value=0).pack(side="left", padx=10)
        tk.Radiobutton(radio_frame, text="미국 주식", variable=self.stock_type, value=1).pack(side="left", padx=10)
        tk.Button(radio_frame,text="🏅 금 시세", command=self.show_gold_detail).pack(side="left",padx=5)
        tk.Button(radio_frame, text="💸 달러 시세", command=self.show_dollar_detail).pack(side="left", padx=5)

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
        self.refresh_data()
        helper.log_time("ui 생성 완료", start_time)

        self.loading.show_progress("데이터 가져오는 중...\n잠시만 기다려 주세요...")
        threading.Thread(target=self.down_us_ticker_list, daemon=True).start()

        self.get_time()

    def down_us_ticker_list(self):
        import queries.select as select_db
        import queries.insert as insert_db
        import queries.update as update_db
        import services.US as us
        us_ver = select_db.select_stock_ver()
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if  us_ver and us_ver['us_ver'] != today:
            df = us.save_us_stock_list()
            insert_db.insert_stock_us(df)
            update_db.update_stock_version_us(today)
            self.check_down_us_ticker_list = True
        else:
            self.check_down_us_ticker_list = True


    def set_tree_view_type(self,new_type):
        self.tree_type = new_type

    def fetch_and_update(self, view_type):
        self.set_tree_view_type(view_type)  # 타입 설정 (0, 1, 2)
        self.stock_type.set(0)

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
        df = krx.pull_krx_top20(asc,self.cur_stock)
        return df


    def show_gold_detail(self):
        from ui.ticker_gold import GoldCart
        GoldCart(self)

    def show_dollar_detail(self):
        from ui.ticker_dollar import DollarCart
        DollarCart(self)


    # 4. 콜백 함수 정의 (클래스 내부에 추가)
    def on_stock_change(self, *args):
        # 사용자가 버튼을 누르면 이 함수가 자동으로 실행되어 값을 복사합니다.
        if not self.check_down_us_ticker_list:
            self.loading.show_progress(message="미국 주식 목록을 받아오는 중입니다.\n잠시만 기다려 주세요...")
            self.root.after(500, self.on_stock_change)
            return
        else:
            self.cur_stock = self.stock_type.get()
            print(f"마켓 변경 감지: {self.cur_stock}")
            import queries.update as update_db
            update_db.update_user_market_type(0,self.cur_stock)
            config.update_webhook(stock_type=self.cur_stock)
            # 만약 마켓이 바뀌자마자 쓰레드를 깨우고 싶다면?
            self.loading.show_progress("데이터 가져오는 중...\n잠시만 기다려 주세요...")
            self.refresh_data()

    def on_finish_out(self):
        os._exit(0)

    def show_detail(self, event):
        # 1. 트리뷰에서 선택된 아이템의 ID 가져오기
        selected_item = self.tree.focus()
        if not selected_item:
            return

        item_data = self.tree.item(selected_item)
        ticker_name = item_data['values'][0]  # 트리뷰 첫 번째 컬럼값

        stock_data = self.ticker[self.ticker['Name'] == ticker_name].iloc[0]

        # 4. 차트 호출 (item_data를 통째로 넘기거나 종목명만 넘김)
        from ui.ticker_detail import CandleCart
        CandleCart(self, stock_data)

    def open_user_manage(self):
        from ui.user_manage import UserManage
        UserManage(self, config.MY_INFO)

    def get_time(self):
        self.cur_time.config(text=f"⏰ {self.get_current_hour_kr()}", fg="black")
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
        try:
            if tree_view_type == 0:
                for i, row in df.iterrows():
                    code, name, target_price, target_price_us, buy_price, buy_price_us, amount, dollar_price, stock_type = row['Code'], row['Name'],row['Target_Price'],row['Target_Price_US'],row['Buy_Price'],row['Buy_Price_US'],row['Amount'],row['Dollar_Price'], row['Stock_Type']
                    price = row['Close']
                    open_p = row['Open']
                    user_price = f"{int(float(target_price)):,}" if stock_type == 0 else f"{int(float(target_price_us)):,}"
                    unit = helper.data_unit(stock_type)

                    is_open = helper.check_market_open(stock_type, now)

                    if is_open:
                        if price > open_p and open_p != 0:
                            tag, display = 'up', f"▲ {int(float(price)):,}"
                        elif price < open_p and open_p != 0:
                            tag, display = 'down', f"▼ {int(float(price)):,}"
                        else:
                            tag, display = 'none', f"  {int(float(price)):,}"
                    else:
                        tag, display = 'none', f"  {int(float(price)):,}"

                    diff = price - open_p
                    today_change = f"+{int(diff):,}" if diff > 0 else f"{int(diff):,}"
                    today_change_f = (diff / open_p * 100) if open_p != 0 else 0.0

                    applied_tags = [tag]
                    if code == self.selected_ticker:
                        applied_tags.append('selected')

                    if self.cur_stock == stock_type:
                        self.tree.insert("", "end",
                                         values=(name, f"{int(float(open_p)):,}{unit}", f"{display}{unit}",
                                                 f"{today_change}{unit}({today_change_f:+.1f}%)",
                                                 f"{user_price}{unit}"),
                                         tags=tuple(applied_tags))
            else:
                for i, row in df.iterrows():
                    code, name = row['Code'], row['Name']
                    price, open_p = row['Close'], row['Open']
                    unit = helper.data_unit(0)
                    # 1. 기준을 '시가'가 아닌 '전일 대비 변동폭(Changes)'으로 변경
                    change_amt = row['Changes']  # 전일 대비 얼마 올랐나?
                    print(name,change_amt)
                    raw_ratio = row['ChagesRatio']  # 전일 대비 몇 % 올랐나?
                    try:
                        today_change_f = float(raw_ratio)
                    except (ValueError, TypeError):
                        today_change_f = 0.0  # 변환 실패 시 0으로 처리

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

        except Exception as e:
            print(f"UI갱신 에러: {e}")
        finally:
            if hasattr(self, 'loading') and self.loading:
                self.loading.stop()

    def stop_ui_update(self):
        # 외부에서 종료하고 싶을 때
        if self.ui_update_id is not None:
            self.root.after_cancel(self.ui_update_id)
            self.ui_update_id = None

    def refresh_data(self):
        # 1. 기존 쓰레드가 있고, 현재 실행 중인지 확인
        if hasattr(self, 'market_thread') and self.market_thread.is_alive():
            # 장시간 중이라 쓰레드가 있을 때
            print("기존 쓰레드 중단 및 재시작 이벤트 송신")
            self.interrupt_event.set()
        else:
            # 장시간이 종료되어 쓰레드가 없을 때
            print("새로운 쓰레드 생성 및 시작")
            self.market_thread = threading.Thread(target=self.data_market, daemon=True)
            self.market_thread.start()

    def open_user_mgmt(self):  # 이름을 살짝 바꿔주면 더 명확합니다.
        from ui.tickers_manage_list import TickersManageList
        TickersManageList(self)

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            current_selected_id = selected[0]
            if current_selected_id == self.last_selected_id:
                return
            self.last_selected_id = current_selected_id
            item = self.tree.item(current_selected_id)
            name = item['values'][0]
            for info in self.watchlist.values():
                if info[1] == name:
                    self.selected_ticker = info[0]
                    break
            self.update_interval = config.ONE
            self.mode_label.config(text=f"🔥 갱신: {name} ({config.ONE}초 주기)", fg="red")
            self.refresh_data()

    def on_esc(self, event):
        self.update_interval = config.TEN
        self.selected_ticker = None
        self.mode_label.config(text=f"갱신: 일반 ({config.TEN}초 주기)", fg="blue")
        self.refresh_data()

    def data_market(self):
        if helper.check_stock_open_close_time():
            while True:
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
                    code, name, target_price, target_price_us, buy_price, buy_price_us, amount, dollar_price, stock_type = info
                    df_5 = krx.pull_request_stock(code, days=5, stock_type=stock_type)

                    if not df_5.empty:
                        # 2. 마지막 줄(오늘 데이터)을 가져옴
                        last_row = df_5.iloc[-1].copy()

                        # 3. 데이터프레임에는 없는 'Name'이나 'Code'를 수동으로 추가
                        last_row['Name'] = name
                        last_row['Code'] = code
                        last_row['Target_Price'] = target_price
                        last_row['Target_Price_US'] = target_price_us
                        last_row['Buy_Price'] = buy_price
                        last_row['Buy_Price_US'] = buy_price_us
                        last_row['Amount'] = amount
                        last_row['Dollar_Price'] = dollar_price
                        last_row['Stock_Type'] = stock_type

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
            stock_type = row['Stock_Type']
            target_val = float(row['Target_Price']) if stock_type == 0 else float(row['Target_Price_US'])
            current_val = float(row['Close'])

            if stock_type == 0 and "09:00" <= current_time_str <= "15:20":
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
            elif stock_type == 1 and ("23:30" <= current_time_str <= "23:59" or "00:00" <= current_time_str <= "06:00"):
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
                title = "🚀 국장 시작 보고" if current_time_str == "09:00" else "🚀 국장 마감 보고"
                alert.send_stock_open_close_alim(title, df)
                self.last_report_min = current_time_str  # 이번 분에는 더 이상 안 보냄


        # 3. 정기 보고 로직 (중복 방지 추가)
        if current_time_str in ["22:30", "05:00"]:
            if self.last_report_min != current_time_str:
                title = "🚀 미장 시작 보고" if current_time_str == "22:30" else "🚀 미장 마감 보고"
                alert.send_stock_open_close_alim(title, df)
                self.last_report_min = current_time_str  # 이번 분에는 더 이상 안 보냄

