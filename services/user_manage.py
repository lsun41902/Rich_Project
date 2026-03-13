import tkinter as tk
from tkinter import messagebox
import database.connection_SQL as db


def open_user_discord(app, item_values):
    data_list = item_values[0]
    add_win = tk.Toplevel(app.root)
    add_win.title("유저 관리")
    add_win.geometry("500x350")

    # 1. 라디오 버튼용 변수 (기본값: .KS)
    market_var = tk.IntVar(value=data_list['types'])
    active_var = tk.BooleanVar(value=data_list['is_active'])

    default_name = data_list['name']
    default_webhook = data_list['webhook']

    # 시장 선택 레이블 및 버튼
    radio_frame = tk.Frame(add_win)
    radio_frame.pack()

    tk.Radiobutton(radio_frame, text="디스코드", variable=market_var, value=0).pack(side="left", padx=10)

    # 2. 기존 입력 필드들
    tk.Label(add_win, text="사용자").pack(pady=5)
    ent_name = tk.Entry(add_win)
    ent_name.insert(0, default_name)
    ent_name.pack()

    tk.Label(add_win, text="webhook").pack(pady=15)
    ent_webhook = tk.Entry(add_win, width=50)
    ent_webhook.insert(0, default_webhook)
    ent_webhook.pack()

    chk_active = tk.Checkbutton(add_win, text="알림 활성화", variable=active_var)
    chk_active.pack(pady=10)

    # 3. 저장 로직 수정
    def save_new_ticker():
        name = ent_name.get().strip()
        webhook = ent_webhook.get().strip()
        types = market_var.get()
        is_active = active_var.get()  # True 또는 False 반환
        market_type = data_list['market_type']

        if name and webhook:
            db.update_user_webhook(0, name, webhook, types, is_active, market_type)
            add_win.destroy()
        else:
            show_message_box("경고", "모든 정보를 입력해주세요.", type=1)

    def show_message_box(title, message, type=0):
        if type == 0:
            return messagebox.askyesno(title, message, parent=add_win)
        elif type == 1:
            return messagebox.showwarning(title, message, parent=add_win)
        else:
            return messagebox.askyesno(title, message, parent=add_win)

    tk.Button(add_win, text="저장", command=save_new_ticker, width=15, bg="#e1f5fe").pack(pady=25)
