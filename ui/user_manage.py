import tkinter as tk
import services.ui_helper as helper

class UserManage:
    def __init__(self,app,item_values):
        self.app = app
        self.root = app.root
        self.data_list = item_values[0]

        self.open_user_discord()

    def open_user_discord(self):
        self.manage = tk.Toplevel(self.root)
        self.manage.title("유저 관리")
        self.manage.iconbitmap(helper.SETTING_ICON_PATH)
        helper.center_window(self.manage, 500,350, self.root)

        # 1. 라디오 버튼용 변수 (기본값: .KS)
        self.alert_var = tk.IntVar(value=self.data_list['types'])
        self.active_var = tk.BooleanVar(value=self.data_list['is_active'])

        default_name = self.data_list['name']
        default_webhook = self.data_list['webhook']
        default_genai_key = self.data_list['genai_key']

        # 시장 선택 레이블 및 버튼
        radio_frame = tk.Frame(self.manage)
        radio_frame.pack(side="top")

        alert_type = tk.Radiobutton(radio_frame, text="디스코드", variable=self.alert_var, value=0)
        alert_type.pack(side="left", padx=10)
        alert_type.pack_forget()

        # 2. 기존 입력 필드들
        tk.Label(self.manage, text="사용자").pack(pady=5)
        self.ent_name = tk.Entry(self.manage)
        self.ent_name.insert(0, default_name)
        self.ent_name.pack()
        self.ent_name.bind("<FocusIn>", lambda event: helper.set_korean_ime())

        alert_frame = tk.Frame(self.manage)
        alert_frame.pack()

        tk.Label(alert_frame, text="webhook").pack(pady=5,side='left')
        chk_active = tk.Checkbutton(alert_frame, text="알림 활성화", variable=self.active_var)
        chk_active.pack(pady=10,side='right')

        self.ent_webhook = tk.Entry(self.manage, width=50)
        self.ent_webhook.insert(0, default_webhook)
        self.ent_webhook.pack()

        model_key_frame = tk.Frame(self.manage)
        model_key_frame.pack()
        tk.Label(model_key_frame, text="GENAI API KEY").pack(pady=5,side='left')
        tk.Button(model_key_frame,text="신청",command=self.show_genai_key_webpage).pack(pady=5,side='right')

        self.ent_model_key = tk.Entry(self.manage, width=50)
        self.ent_model_key.insert(0, default_genai_key)
        self.ent_model_key.pack()

        tk.Button(self.manage, text="저장", command=self.save_new_ticker, width=15, bg="#e1f5fe").pack(pady=25)

    def show_genai_key_webpage(self):
        import webbrowser
        try:
            url = "https://aistudio.google.com/prompts/new_chat?hl=ko"
            webbrowser.open_new_tab(url)  # 새 탭에서 열기
        except Exception as e:
            print(f"웹페이지를 열 수 없습니다: {e}")

    def save_new_ticker(self):
        import queries.update as update_db
        name = self.ent_name.get().strip()
        webhook = self.ent_webhook.get().strip()
        types = self.alert_var.get()
        is_active = self.active_var.get()  # True 또는 False 반환
        market_type = self.data_list['market_type']
        genai_key = self.ent_model_key.get().strip()
        if name and webhook:
            update_db.update_user_webhook(0, name, webhook, types, is_active, market_type,genai_key)
            self.manage.destroy()
        else:
            helper.show_message_box(self.manage,title="경고", msg="모든 정보를 입력해주세요.", mtype=1)

