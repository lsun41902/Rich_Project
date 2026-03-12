import tkinter as tk
from tkinter import ttk, messagebox
import database.connection as db
import config

def open_user_mgmt_logic(app):
    manager_ui = tk.Toplevel(app.root)
    manager_ui.title("종목 관리")
    manager_ui.geometry("700x550")

    # --- 1. 상단 레이아웃 ---
    header_frame = tk.Frame(manager_ui)
    header_frame.pack(fill="x", pady=10)
    tk.Label(header_frame, text="📋 내 감시 종목 리스트", font=("Malgun Gothic", 14, "bold")).pack()

    # --- 2. Treeview 및 스크롤바 컨테이너 ---
    # 표와 스크롤바를 묶어줄 프레임입니다.
    list_frame = tk.Frame(manager_ui)
    list_frame.pack(pady=10, padx=20, fill="both", expand=True)

    columns = ("code", "name", "target")
    tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

    # 스크롤바 생성 및 연결 (하나로 통일)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)

    # 컬럼 설정
    tree.heading("code", text="종목코드", anchor="center")
    tree.heading("name", text="종목명", anchor="center")
    tree.heading("target", text="목표가", anchor="center")

    tree.column("code", width=120, anchor="center")
    tree.column("name", width=200, anchor="center")
    tree.column("target", width=150, anchor="center")

    # 배치: 표는 왼쪽, 스크롤바는 오른쪽에 꽉 차게
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # 1. 내부 함수로 정의 (app과 tree에 바로 접근 가능)
    def on_item_double_click(event):
        selection = tree.selection()
        if not selection: return

        db_id = selection[0]  # Treeview의 iid가 곧 db_id
        item_values = tree.item(db_id, 'values')

        # db_id를 함께 전달
        add_item_window(item_values, db_id=db_id)




    # --- 3. 데이터 로드 함수 (하나로 통합) ---
    def refresh_tree():
        for item in tree.get_children():
            tree.delete(item)

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
            tree.insert("", "end", iid=db_id, values=(code, name, formatted_target + unit))

    # 초기 데이터 로드
    refresh_tree()

    # --- 4. 하단 버튼 영역 ---
    btn_frame = tk.Frame(manager_ui)
    btn_frame.pack(pady=20)

    # [+] 추가 창 로직
    def add_item_window(item_values=None,db_id=None):
        is_edit_mode = item_values is not None
        default_code = ""
        default_name = ""
        default_price = ""

        add_win = tk.Toplevel(manager_ui)
        add_win.title("새 종목 추가")
        add_win.geometry("300x450")

        # 1. 라디오 버튼용 변수 (기본값: .KS)
        market_var = tk.StringVar(value=".KS")
        price_var = tk.StringVar(value=default_price)

        # 2. 수정 모드일 경우 기존 데이터 파싱
        if is_edit_mode:
            full_code = item_values[0]  # '005930.KS'
            default_name = item_values[1]
            # 숫자만 추출 (쉼표와 '원' 제거)
            default_price = item_values[2].replace(',', '').replace('원', '').replace('$', '')

            if '.' in full_code:
                default_code, suffix = full_code.split('.')
                market_var.set("." + suffix)
            else:
                default_code = full_code

        # 시장 선택 레이블 및 버튼
        tk.Label(add_win, text="시장 선택:", font=("Malgun Gothic", 9, "bold")).pack(pady=5)
        radio_frame = tk.Frame(add_win)
        radio_frame.pack()

        tk.Radiobutton(radio_frame, text="코스피 (.KS)", variable=market_var, value=".KS").pack(side="left", padx=10)
        tk.Radiobutton(radio_frame, text="코스닥 (.KQ)", variable=market_var, value=".KQ").pack(side="left", padx=10)

        # 2. 기존 입력 필드들
        tk.Label(add_win, text="종목 코드 (숫자만):").pack(pady=5)
        ent_code = tk.Entry(add_win)
        ent_code.insert(0,default_code)
        ent_code.pack()

        tk.Label(add_win, text="종목명:").pack(pady=5)
        ent_name = tk.Entry(add_win)
        ent_name.insert(0,default_name)
        ent_name.pack()

        # 실시간으로 표시될 라벨
        label_display = tk.Label(add_win, text="목표가:0원", fg="blue")
        label_display.pack(pady=5)

        # 2. 변수가 변할 때 실행될 함수
        def update_display(*args):
            val = price_var.get().replace(',', '')
            if val.isdigit():
                label_display.config(text=f"목표가:{int(val):,}원")
            else:
                label_display.config(text="목표가:0원")

        # 3. Entry 생성 시 textvariable 연결
        ent_price = tk.Entry(add_win, textvariable=price_var)
        price_var.trace_add("write", update_display)  # 값 변화 감지 시작!
        ent_price.pack()


        # 3. 저장 로직 수정
        def save_new_ticker():
            raw_code = ent_code.get().strip()
            name = ent_name.get().strip()
            price = ent_price.get().strip()
            suffix = market_var.get()  # 선택된 .KS 또는 .KQ 가져오기
            full_code = f"{raw_code}{suffix}"

            if raw_code and name and price:
                if is_edit_mode:
                    # DB 업데이트 함수 호출 (기존 코드를 기준으로 정보 수정)
                    db.update_ticker_in_db(db_id, full_code, name, price)
                else:
                    # DB 신규 저장 함수 호출
                    db.insert_ticker_to_db(config.CUR_USER_ID, full_code, name, price)

                refresh_tree()  # 목록 새로고침
                add_win.destroy()
            else:
                show_message_box("경고", "모든 정보를 입력해주세요.",type=1)

        tk.Button(add_win, text="저장", command=save_new_ticker, width=15, bg="#e1f5fe").pack(pady=25)

    # [-] 삭제 로직
    def delete_item():
        selected = tree.selection()
        if not selected: return

        db_id = selected[0]  # 선택된 행의 iid가 곧 db_id

        if show_message_box("삭제 확인", "선택한 종목을 삭제할까요?", type=0):
            db.delete_ticker_to_db(db_id)  # ID로 삭제
            refresh_tree()

    def show_message_box(title, message,type=0):
        if type == 0:
            return messagebox.askyesno(title, message, parent=manager_ui)
        elif type == 1:
            return messagebox.showwarning(title, message, parent=manager_ui)
        else:
            return messagebox.askyesno(title, message, parent=manager_ui)

    tk.Button(btn_frame, text=" ➕ 종목 추가 ", command=add_item_window, bg="#e1f5fe").pack(side="left", padx=10)
    tk.Button(btn_frame, text=" ➖ 선택 삭제 ", command=delete_item, bg="#ffebee").pack(side="left", padx=10)

    # 2. 바인딩
    tree.bind("<Double-1>", on_item_double_click)

    # 2. 창이 닫힐 때까지 대기
    app.root.wait_window(manager_ui)

    # 3. 창이 닫히면 실행 (메인 화면 새로고침)
    app.manual_refresh()


