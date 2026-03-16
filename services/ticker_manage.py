import tkinter as tk
from tkinter import messagebox
import database.connection_SQL as db
import config
from services.ticker_search import TickerSearch
from services.ui_helper import center_window,set_korean_ime, show_message_box

class TickerManage:
    def __init__(self,app, item_values=None,db_id=None):
        self.app = app
        self.root = app.root
        self.item_values = item_values
        self.db_id = db_id
        self.tree = None
        self.init_ui()

    def init_ui(self):
        is_edit_mode = self.item_values is not None
        default_code = ""
        default_name = ""
        default_price = ""

        add_win = tk.Toplevel(self.root)
        add_win.title("새 종목 추가")
        add_win.geometry("300x450")
        center_window(add_win,300,450,self.root)

        # 1. 라디오 버튼용 변수 (기본값: .KS)
        self.market_var = tk.StringVar(value=".KS")

        # 2. 수정 모드일 경우 기존 데이터 파싱
        if is_edit_mode:
            full_code = self.item_values[0]  # '005930.KS'
            default_name = self.item_values[1]
            # 숫자만 추출 (쉼표와 '원' 제거)
            default_price = self.item_values[2].replace(',', '').replace('원', '').replace('$', '')

            if '.' in full_code:
                default_code, suffix = full_code.split('.')
                self.market_var.set("." + suffix)
            else:
                default_code = full_code
        self.price_var = tk.StringVar(value=default_price)

        # 시장 선택 레이블 및 버튼
        tk.Label(add_win, text="시장 선택:", font=("Malgun Gothic", 9, "bold")).pack(pady=5)
        radio_frame = tk.Frame(add_win)
        radio_frame.pack()

        tk.Radiobutton(radio_frame, text="코스피 (.KS)", variable=self.market_var, value=".KS").pack(side="left", padx=10)
        tk.Radiobutton(radio_frame, text="코스닥 (.KQ)", variable=self.market_var, value=".KQ").pack(side="left", padx=10)
        radio_frame.pack_forget()

        search_frame = tk.Frame(add_win)

        # 돋보기 버튼 (이미지가 있다면 image 옵션 사용, 없으면 텍스트로)

        tk.Label(search_frame, text="종목명:").pack(side='left',pady=5)

        search_frame.pack(pady=5)

        self.ent_name = tk.Entry(add_win)
        self.ent_name.insert(0, default_name)
        self.ent_name.pack(padx=5)
        self.ent_name.bind("<FocusIn>", lambda event: set_korean_ime())
        self.ent_name.bind("<Return>", lambda e: self.open_search_window())

        btn_search = tk.Button(search_frame, text="검색", command=lambda: self.open_search_window())
        btn_search.pack(side="left")  # Entry 바로 오른쪽 배치

        tk.Label(add_win, text="종목 코드 (숫자만):").pack(pady=5)
        self.ent_code = tk.Entry(add_win)
        self.ent_code.insert(0, default_code)
        self.ent_code.pack(padx=5)
        self.ent_code.bind("<FocusIn>", lambda event: set_korean_ime())


        # 실시간으로 표시될 라벨
        self.label_display = tk.Label(add_win, text="목표가: 0원", fg="blue")
        self.label_display.pack(pady=5)


        # 3. Entry 생성 시 textvariable 연결
        ent_price = tk.Entry(add_win, textvariable=self.price_var)
        self.price_var.trace_add("write", self.update_display)  # 값 변화 감지 시작!
        ent_price.pack()
        self.update_display()

        # 3. 저장 로직 수정
        def save_new_ticker():
            raw_code = self.ent_code.get().strip()

            # 1. 검증: 코드가 DB에 없는 경우
            all_tickers = db.get_default_ticker_list()
            code_list = [ticker[0] for ticker in all_tickers]
            if raw_code not in code_list:
                show_message_box("경고", "코드를 확인해 주세요.", mtype=1)
                return  # 여기서 멈춰야 합니다! 뒤의 코드가 실행되지 않게 하세요.

            # 2. 검증: 빈 칸 확인
            name = self.ent_name.get().strip()
            price = ent_price.get().strip()
            if not (raw_code and name and price):
                show_message_box("경고", "모든 정보를 입력해주세요.", mtype=1)
                return  # 여기서 멈추세요!

            # 3. 저장 로직 (모든 검증 통과 후)
            suffix = self.market_var.get()
            full_code = f"{raw_code}{suffix}"

            if is_edit_mode:
                db.update_ticker_in_db(self.db_id, full_code, name, price)
            else:
                db.insert_ticker_to_db(config.CUR_USER_ID, full_code, name, price)

            self.app.refresh_tree()
            add_win.destroy()  # 저장이 완료된 직후에만 여기서 닫습니다.

        tk.Button(add_win, text="저장", command=save_new_ticker, width=15, bg="#e1f5fe").pack(pady=25)

    def open_search_window(self,event=None):
        default_search = self.ent_code.get().strip()
        TickerSearch(self, default_search)

    # 2. 변수가 변할 때 실행될 함수
    def update_display(self,*args):
        val = self.price_var.get().replace(',', '')
        if val.isdigit():
            self.label_display.config(text=f"목표가: {int(val):,}원")
        else:
            self.label_display.config(text="목표가: 0원")
