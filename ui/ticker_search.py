import tkinter as tk
import services.ui_helper as helper


class TickerSearch:
    def __init__(self, parent_window, default_search):
        self.app = parent_window
        self.root = parent_window.root
        self.default_search = default_search
        self.init()

    def init(self):
        self.results = []
        self.search_win = tk.Toplevel()
        self.search_win.title("주식 검색")
        self.search_win.iconbitmap(helper.SETTING_ICON_PATH)

        helper.center_window(self.search_win, 300, 300, self.app.root)

        # 검색 입력창
        self.search_var = tk.StringVar()
        self.ent_search = tk.Entry(self.search_win, textvariable=self.search_var)
        self.ent_search.insert(0, self.default_search)
        self.ent_search.pack(pady=10)

        self.search_var.trace_add("write", self.on_text_changed)

        # 추천 리스트를 보여줄 Listbox
        self.listbox = tk.Listbox(self.search_win)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind('<Double-Button-1>', self.select_stock)

        self.search_timer = None

        # 입력창 내용이 바뀔 때마다 update_list 실행
        self.ent_search.bind("<KeyRelease>", self.update_list)
        self.ent_search.bind("<Return>", self.perform_search)
        self.ent_search.bind("<FocusIn>", lambda e: helper.set_korean_ime())

        self.perform_search()  # 시작하자마자 전체 리스트 보여주기

    # 3. 변수 값이 바뀔 때마다 감지
    def on_text_changed(self, *args):
        # 예약된 타이머가 있다면 취소
        if self.search_timer is not None:
            self.search_win.after_cancel(self.search_timer)

        # 새로운 타이머 설정
        self.search_timer = self.search_win.after(300, self.perform_search)

    def update_list(self, event=None):
        if self.search_timer:
            self.search_win.after_cancel(self.search_timer)

        # 0.3초(300ms)는 한글 조합이 끝날 시간을 벌어줍니다.
        self.search_timer = self.search_win.after(300, self.perform_search)

    def perform_search(self, event=None):
        import database.connection_SQL as db

        search_term = self.ent_search.get()
        self.results = db.get_like_default_ticker_list(search_term)

        # 화면 업데이트
        self.listbox.delete(0, tk.END)
        for code, name, market_type in self.results:
            self.listbox.insert(tk.END, f"{name}")

    # 선택 버튼
    def select_stock(self, event):
        selection_indices = self.listbox.curselection()
        if not selection_indices:  # 선택된 항목이 없으면 리턴
            return

        selection = self.results[selection_indices[0]]
        code, name, market_type = selection
        market_type = ".KS" if "KOSPI" in market_type else ".KQ"

        self.app.ent_name.delete(0, tk.END)
        self.app.ent_name.insert(0, name)

        self.app.ent_code.delete(0, tk.END)
        self.app.ent_code.insert(0, code)

        self.app.market_var.set(market_type)

        self.search_win.destroy()
