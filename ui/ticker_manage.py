import tkinter as tk
import config
from ui.ticker_search import TickerSearch
import services.ui_helper as helper


class TickerManage:
    def __init__(self, app, item_values=None, db_id=None):
        self.app = app
        self.root = app.root
        # item_values가 None이면 9개의 기본값을 가진 리스트 생성
        self.is_edit_mode = item_values is not None
        if item_values is None:
            # 순서: code, name, target, target_us, _, _, _, _, market
            self.item_values = ["", "", 0, 0, 0, 0, 0, 0, 0]
        else:
            self.item_values = item_values

        # 안전하게 언패킹
        (self.ticker_code, self.ticker_name, self.target_price,
         self.target_price_us, _, _, _, _, self.market_type) = self.item_values
        self.db_id = db_id
        self.tree = None
        self.init_ui()

    def init_ui(self):
        self.add_win = tk.Toplevel(self.root)
        self.add_win.title("새 종목 추가")
        self.add_win.geometry("300x450")
        self.add_win.iconbitmap(helper.SETTING_ICON_PATH)
        helper.center_window(self.add_win, 300, 450, self.root)

        # 시장 선택 레이블 및 버튼
        stock_frame = tk.Frame(self.add_win)
        tk.Label(stock_frame, text="시장 선택:", font=("Malgun Gothic", 9, "bold")).pack(pady=5)
        self.cur_stock = tk.IntVar(value=self.market_type)
        self.stock_type = self.cur_stock.get()
        self.stock_ko = tk.Radiobutton(stock_frame, text="국장", variable=self.cur_stock, value=0,
                                       font=("Arial", 10, "bold"), bg="#f0f0f0", command=self.on_stock_change).pack(
            side="left")
        self.stock_us = tk.Radiobutton(stock_frame, text="국장", variable=self.cur_stock, value=0,
                                       font=("Arial", 10, "bold"), bg="#f0f0f0", command=self.on_stock_change).pack(
            side="left")

        search_frame = tk.Frame(self.add_win)

        # 돋보기 버튼 (이미지가 있다면 image 옵션 사용, 없으면 텍스트로)

        tk.Label(search_frame, text="종목명:").pack(side='left', pady=5)

        search_frame.pack(pady=5)

        self.ent_name = tk.Entry(self.add_win)
        self.ent_name.insert(0, self.ticker_name)
        self.ent_name.pack(padx=5)
        self.ent_name.bind("<FocusIn>", lambda event: helper.set_korean_ime())
        self.ent_name.bind("<Return>", lambda e: self.open_search_window())

        btn_search = tk.Button(search_frame, text="검색", command=lambda: self.open_search_window())
        btn_search.pack(side="left")  # Entry 바로 오른쪽 배치

        tk.Label(self.add_win, text="종목 코드:").pack(pady=5)
        self.ent_code = tk.Entry(self.add_win)
        self.ent_code.insert(0, self.ticker_code)
        self.ent_code.pack(padx=5)
        self.ent_code.bind("<FocusIn>", lambda event: helper.set_korean_ime())

        # 실시간으로 표시될 라벨
        self.label_display = tk.Label(self.add_win, text="", fg="blue")
        self.label_display.pack(pady=5)

        self.price_var = tk.StringVar(value=self.target_price)
        # 3. Entry 생성 시 textvariable 연결
        self.ent_price = tk.Entry(self.add_win, textvariable=self.price_var)
        self.price_var.trace_add("write", self._update_display)  # 값 변화 감지 시작!
        self.ent_price.pack()
        self.ent_price.bind("<Return>",lambda event: self.save_new_ticker)
        self._update_display()

        tk.Button(self.add_win, text="저장", command=self.save_new_ticker, width=15, bg="#e1f5fe").pack(pady=25)

    def on_stock_change(self, stock_type=None):
        if stock_type:
            self.stock_type = stock_type
        else:
            self.stock_type = self.cur_stock.get()
        self._update_display()

    def save_new_ticker(self, event=None):
        import queries.select as select_db
        import queries.update as update_db
        import queries.insert as insert_db

        raw_code = self.ent_code.get().strip()
        clean_code = raw_code.split(".")[0]

        # 1. 검증: 코드가 DB에 없는 경우
        all_tickers = select_db.select_default_ticker_list(self.stock_type)
        if (clean_code,) not in all_tickers:
            helper.show_message_box(self.add_win, title="경고", msg="코드를 확인해 주세요.", mtype=1)
            return

        # 2. 검증: 빈 칸 확인
        name = self.ent_name.get().strip()
        price = self.ent_price.get().strip()
        if not (raw_code and name and price):
            helper.show_message_box(self.add_win, title="경고", msg="모든 정보를 입력해주세요.", mtype=1)
            return

        if self.is_edit_mode:
            update_db.update_ticker_in_db(self.db_id, raw_code, name, price, self.stock_type)
        else:
            insert_db.insert_ticker(config.CUR_USER_ID, raw_code, name, price, self.stock_type)

        self.app.refresh_tree()
        self.add_win.destroy()  # 저장이 완료된 직후에만 여기서 닫습니다.

    def open_search_window(self, event=None):
        default_search = self.ent_name.get().strip()
        TickerSearch(self, default_search)

    # 2. 변수가 변할 때 실행될 함수
    def _update_display(self, *args):
        val = self.price_var.get().replace(',', '')
        unit = helper.data_unit(self.stock_type)
        if val.isdigit():
            self.label_display.config(text=f"목표가: {int(val):,}{unit}")
        else:
            self.label_display.config(text=f"목표가: 0{unit}")
