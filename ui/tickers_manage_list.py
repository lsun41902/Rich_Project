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
        self.manager_ui = tk.Toplevel(self.root)
        self.manager_ui.title("종목 관리")
        self.manager_ui.iconbitmap(helper.SETTING_ICON_PATH)

        helper.center_window(self.manager_ui, 700, 500, self.root)

        # --- 1. 상단 레이아웃 ---
        self.header_frame = tk.Frame(self.manager_ui)
        self.header_frame.pack(fill="x", pady=10)
        tk.Label(self.header_frame, text="📋 내 감시 종목 리스트", font=("Malgun Gothic", 14, "bold")).pack()

        # --- 2. Treeview 및 스크롤바 컨테이너 ---
        # 표와 스크롤바를 묶어줄 프레임입니다.
        list_frame = tk.Frame(self.manager_ui)
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        columns = ("code", "name", "target")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        # 스크롤바 생성 및 연결 (하나로 통일)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 컬럼 설정
        self.tree.heading("code", text="종목코드", anchor="center")
        self.tree.heading("name", text="종목명", anchor="center")
        self.tree.heading("target", text="목표가", anchor="center")

        self.tree.column("code", width=120, anchor="center")
        self.tree.column("name", width=200, anchor="center")
        self.tree.column("target", width=150, anchor="center")

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
        self.app.manual_refresh()

    # 1. 내부 함수로 정의 (app과 tree에 바로 접근 가능)
    def on_item_double_click(self,event):
        selection = self.tree.selection()
        if not selection: return

        db_id = selection[0]  # Treeview의 iid가 곧 db_id
        item_values = self.tree.item(db_id, 'values')

        # db_id를 함께 전달
        self.add_item_window(item_values, db_id=db_id)

    # --- 3. 데이터 로드 함수 (하나로 통합) ---
    def refresh_tree(self):
        import database.connection_SQL as db
        import config

        for item in self.tree.get_children():
            self.tree.delete(item)

        # DB 데이터 호출 (get_user_ticker_list는 전역 혹은 클래스 메서드여야 함)
        watchlist_data = db.get_user_ticker_list(config.CUR_USER_ID)

        if not watchlist_data:
            print("보여줄 종목이 없습니다.")
            return

        # config.WATCHLIST의 구조가 {db_id: [code, name, target]} 이라면
        for db_id, info in config.WATCHLIST.items():
            code, name, target = info
            formatted_target = f"{int(target):,}"
            unit = "원" if any(ex in code for ex in [".KS", ".KQ"]) else "$"

            # 여기서 iid에 db_id를 심어줍니다
            self.tree.insert("", "end", iid=db_id, values=(code, name, formatted_target + unit))

    # [-] 삭제 로직
    def delete_item(self):
        import database.connection_SQL as db

        selected = self.tree.selection()
        if not selected: return

        db_id = selected[0]  # 선택된 행의 iid가 곧 db_id

        if helper.show_message_box(self.manager_ui,title="삭제 확인", msg="선택한 종목을 삭제할까요?", mtype=0):
            db.delete_ticker_to_db(db_id)  # ID로 삭제
            self.refresh_tree()


    def add_item_window(self,item_values=None,db_id=None):
        from ui.ticker_manage import TickerManage
        TickerManage(self,item_values,db_id)