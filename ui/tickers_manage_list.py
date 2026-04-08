import tkinter as tk
from tkinter import ttk
import services.ui_helper as helper

class TickersManageList:
    def __init__(self,app):
        self.app = app
        self.root = app.root
        self.tree = None
        self.init_ui()

    def init_ui(self):
        import queries.select as select_db

        self.manager_ui = tk.Toplevel(self.root)
        self.manager_ui.title("종목 관리")
        self.manager_ui.iconbitmap(helper.SETTING_ICON_PATH)
        self.watchlist_data = None
        helper.center_window(self.manager_ui, 700, 500, self.root)

        # --- 1. 상단 레이아웃 ---
        self.header_frame = tk.Frame(self.manager_ui)
        self.header_frame.pack(fill="x", pady=10)
        tk.Label(self.header_frame, text="📋 내 감시 종목 리스트", font=("Malgun Gothic", 14, "bold")).pack()

        radio_frame = tk.Frame(self.manager_ui)
        radio_frame.pack(fill='x')
        self.stock_type = tk.IntVar(value=select_db.select_user_stock_type())
        self.cur_stock = self.stock_type.get()
        self.stock_type.trace_add("write", self.on_market_change)
        tk.Radiobutton(radio_frame, text="한국 주식", variable=self.stock_type, value=0).pack(side="left", padx=10)
        tk.Radiobutton(radio_frame, text="미국 주식", variable=self.stock_type, value=1).pack(side="left", padx=10)

        # --- 2. Treeview 및 스크롤바 컨테이너 ---
        # 표와 스크롤바를 묶어줄 프레임입니다.
        list_frame = tk.Frame(self.manager_ui)
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        columns = ("code", "name", "target","buy","amount","market")

        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        # 스크롤바 생성 및 연결 (하나로 통일)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 컬럼 설정
        self.tree.heading("code", text="종목코드", anchor="center")
        self.tree.heading("name", text="종목명", anchor="center")
        self.tree.heading("target", text="목표가", anchor="center")
        self.tree.heading("buy", text="구매가", anchor="center")
        self.tree.heading("amount", text="수량", anchor="center")
        self.tree.heading("market", text="시장", anchor="center")

        self.tree.column("code", width=120, anchor="w")
        self.tree.column("name", width=150, anchor="w")
        self.tree.column("target", width=150, anchor="w")
        self.tree.column("buy", width=150, anchor="w")
        self.tree.column("amount", width=80, anchor="w")
        self.tree.column("market", width=0, anchor="w")
        self.tree["displaycolumns"] = ("code", "name", "target", "buy", "amount")

        # 배치: 표는 왼쪽, 스크롤바는 오른쪽에 꽉 차게
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 초기 데이터 로드
        self.refresh_tree()

        # --- 4. 하단 버튼 영역 ---
        btn_frame = tk.Frame(self.manager_ui)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text=" ➕ 종목 추가 ", command=self.add_item_window, bg="#e1f5fe").pack(side="left", padx=10)
        tk.Button(btn_frame, text=" ➖ 선택 삭제 ", command=self.delete_item, bg="#ffebee").pack(side="left", padx=10)

        # 2. 바인딩
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # 2. 창이 닫힐 때까지 대기
        self.root.wait_window(self.manager_ui)

        # 3. 창이 닫히면 실행 (메인 화면 새로고침)
        self.app.watchlist = self.watchlist_data
        self.app.on_stock_change()
        self.app.my_list()

    def on_market_change(self, *args):
        # 사용자가 버튼을 누르면 이 함수가 자동으로 실행되어 값을 복사합니다.
        self.cur_stock = self.stock_type.get()
        print(f"마켓 변경 감지: {self.cur_stock}")

        # 만약 마켓이 바뀌자마자 쓰레드를 깨우고 싶다면?
        self.refresh_tree()

    # 1. 내부 함수로 정의 (app과 tree에 바로 접근 가능)
    def on_item_double_click(self,event):
        selection = self.tree.selection()
        if not selection: return

        db_id = int(selection[0])  # Treeview의 iid가 곧 db_id
        item_values = self.watchlist_data.get(db_id)
        # db_id를 함께 전달
        self.add_item_window(item_values, db_id=db_id)

    # --- 3. 데이터 로드 함수 (하나로 통합) ---
    def refresh_tree(self):
        import queries.select as select_db
        import config

        for item in self.tree.get_children():
            self.tree.delete(item)

        # DB 데이터 호출 (get_user_ticker_list는 전역 혹은 클래스 메서드여야 함)
        self.watchlist_data = select_db.select_user_ticker_list(config.CUR_USER_ID)

        if not self.watchlist_data:
            print("보여줄 종목이 없습니다.")
            return

        for db_id, info in self.watchlist_data.items():
            code, name, target_price, target_price_us, buy_price, buy_price_us, amount, dollar_price, stock_type = info
            formatted_target = f"{int(target_price):,}" if stock_type == 0 else f"{int(target_price_us):,}"
            formatted_buy_price = f"{int(buy_price):,}" if stock_type == 0 else f"{int(buy_price_us):,}"
            unit = helper.data_unit(stock_type)

            # 여기서 iid에 db_id를 심어줍니다
            if self.cur_stock == stock_type:
                self.tree.insert("", "end", iid=db_id, values=(code, name, formatted_target + unit, formatted_buy_price + unit, amount, stock_type))

    # [-] 삭제 로직
    def delete_item(self):
        import queries.delete as delete_db

        selected = self.tree.selection()
        if not selected: return

        db_id = selected[0]  # 선택된 행의 iid가 곧 db_id

        if helper.show_message_box(self.manager_ui,title="삭제 확인", msg="선택한 종목을 삭제할까요?", mtype=0):
            delete_db.delete_ticker_to_db(db_id)  # ID로 삭제
            self.refresh_tree()


    def add_item_window(self,item_values=None,db_id=None):
        from ui.ticker_manage import TickerManage
        TickerManage(self,item_values,db_id)