def center_window(window, width, height, parent=None):
    # parent가 None이면 화면 정중앙
    if parent is None:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
    else:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")


def set_korean_ime():
    import ctypes
    from ctypes import wintypes
    import pyautogui
    # 1. 현재 포커스된 창의 핸들 가져오기
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    # 2. 입력기 컨텍스트(IMC) 가져오기
    himc = ctypes.windll.imm32.ImmGetContext(hwnd)

    if himc:
        # 3. 현재 변환 상태 가져오기
        # dwConversion: 1이면 한글, 0이면 영어
        dwConversion = ctypes.wintypes.DWORD()
        dwSentence = ctypes.wintypes.DWORD()
        ctypes.windll.imm32.ImmGetConversionStatus(himc, ctypes.byref(dwConversion), ctypes.byref(dwSentence))

        # 4. 상태 확인 (dwConversion.value가 0이면 영어 모드임)
        if dwConversion.value == 0:
            print("현재 영어 모드입니다. 한글로 전환합니다.")
            pyautogui.press('hangul')
        else:
            print("이미 한글 모드입니다.")

        # 5. 컨텍스트 해제 (메모리 관리)
        ctypes.windll.imm32.ImmReleaseContext(hwnd, himc)


def show_message_box(parent, title, msg, mtype=0):
    from tkinter import messagebox

    if mtype == 0:
        return messagebox.askyesno(title, msg, parent=parent)
    elif mtype == 1:
        return messagebox.showwarning(title, msg, parent=parent)
    else:
        return messagebox.askyesno(title, msg, parent=parent)


def check_stock_open_close_time():
    from datetime import datetime, timedelta
    now = datetime.now()
    if (now.hour == 9 and now.minute >= 0) or (9 < now.hour < 15) or (now.hour == 15 and now.minute <= 20):
        return True
    else:
        return False

def volume_formatter(x, pos):
    """숫자 크기에 따라 단위를 붙여주는 함수"""
    if x >= 1e9:  # 10억 이상
        return f'{x * 1e-9:,.1f}B'
    elif x >= 1e6:  # 100만 이상
        return f'{x * 1e-6:,.1f}M'
    elif x >= 1e3:  # 1,000 이상
        return f'{x * 1e-3:,.0f}K'
    else:
        return f'{x:,.0f}'


def date_formatter(date):
    from datetime import datetime, timedelta
    # 1. 문자열을 날짜 객체로 변환 (Parse)
    dt_obj = datetime.strptime(str(date), "%Y%m%d")

    # 2. 원하는 형식의 문자열로 변환 (Format)
    return dt_obj.strftime("%Y/%m/%d")

def data_unit(stock_type):
    unit = "원" if stock_type == 0 else "$"
    return unit

def get_crypto_key():
    import base64
    import hashlib
    import subprocess
    import platform
    os_type = platform.system()
    unique_id = ""
    try:
        if os_type == "Windows":
            # 윈도우: 메인보드 UUID
            cmd = 'wmic csproduct get uuid'
            unique_id = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        elif os_type == "Darwin":  # Mac OS
            # Mac: 하드웨어 UUID 추출 명령어
            cmd = "ioreg -rd1 -c IOPlatformExpertDevice | grep -E '(UUID)'"
            output = subprocess.check_output(cmd, shell=True).decode()
            unique_id = output.split('"')[-2]
        else:
            unique_id = platform.node()  # 기타 (Linux 등)
    except:
        unique_id = platform.node()

    # UUID를 SHA256으로 해싱하여 32바이트 규격 생성
    key_hash = hashlib.sha256(unique_id.encode()).digest()
    # Fernet 규격(Base64)으로 변환
    return base64.urlsafe_b64encode(key_hash)


def encrypt_key(raw_api_key):
    # os키를 이용해 암호화 하기
    from cryptography.fernet import Fernet
    if not raw_api_key: return ""
    f = Fernet(get_crypto_key())
    return f.encrypt(raw_api_key.encode()).decode()


def decrypt_key(encrypted_api_key):
    # os키를 이용해 복호화 하기
    from cryptography.fernet import Fernet
    if not encrypted_api_key: return ""
    try:
        f = Fernet(get_crypto_key())
        return f.decrypt(encrypted_api_key.encode()).decode()
    except:
        # 복호화 실패 시(이미 평문이거나 기기가 바뀐 경우) 원본 반환
        return encrypted_api_key


class LoadingWindow:

    def __init__(self, parent):
        self.parent = parent
        self.x = parent.winfo_x() + (parent.winfo_width() // 2) - 150
        self.y = parent.winfo_y() + (parent.winfo_height() // 2) - 50

    def show_message(self, message):
        import tkinter as tk
        self.window = tk.Toplevel(self.parent)
        self.window.title("분석")
        center_window(self.window, 300, 300, self.parent)
        label = tk.Label(self.window, text=message)
        label.pack(pady=10)

    def show_message_scroll(self,title, message):
        import tkinter as tk
        from tkinter import scrolledtext
        self.parent.update_idletasks()
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"{title} 분석 결과")
        center_window(self.window, 500, 500, self.parent)
        s_text = scrolledtext.ScrolledText(self.window, wrap=tk.WORD, font=("Malgun Gothic", 10),height=15)
        s_text.insert(tk.END,message)
        s_text.pack(padx=10, pady=10, fill="both", expand=True)

    def show_progress(self, message="분석중..."):
        import tkinter as tk
        from tkinter import ttk
        if hasattr(self, 'window') and self.window and self.window.winfo_exists():
            # 창이 이미 있다면 메시지만 업데이트하고 함수 종료
            self.label.config(text=message)
            if len(message) > 20:
                center_window(self.window, 500, 100, self.parent)
            else:
                center_window(self.window, 500, 100, self.parent)
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("분석")
        center_window(self.window, 500, 100, self.parent)

        # 창 닫기 버튼 무효화 (작업 중 강제 종료 방지)
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)

        self.label = tk.Label(self.window, text=message)
        self.label.pack(pady=10)

        # 결정되지 않은(Indeterminate) 모드의 프로그레스바
        self.progress = ttk.Progressbar(self.window, mode='indeterminate', length=200)
        self.progress.pack(pady=5)
        self.progress.start(10)  # 10ms 간격으로 움직임

    def stop(self):
        try:
            # 1. 프로그레스 바가 메모리에 있고, 실제 화면상에도 존재하는지 확인
            if hasattr(self, 'progress') and self.progress.winfo_exists():
                self.progress.stop()

            # 2. 로딩 창(Toplevel)이 실제로 존재하는지 확인 후 닫기
            if hasattr(self, 'window') and self.window.winfo_exists():
                self.window.destroy()

        except Exception as e:
            pass


MAIN_ICON_PATH = ''
CHART_ICON_PATH = ''
SETTING_ICON_PATH = ''


def set_icons():
    global MAIN_ICON_PATH, CHART_ICON_PATH, SETTING_ICON_PATH
    import os
    import sys

    # 1. 아이콘이 들어있는 폴더와 파일명 정의
    icon_folder = 'icons'
    main_name = 'main.ico'
    chart_name = 'chart.ico'
    setting_name = 'setting.ico'

    # 2. 베이스 경로 결정 (빌드 환경 vs 개발 환경)
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    # 3. 폴더명까지 포함하여 최종 절대 경로 생성
    MAIN_ICON_PATH = os.path.join(base_path, icon_folder, main_name)
    CHART_ICON_PATH = os.path.join(base_path, icon_folder, chart_name)
    SETTING_ICON_PATH = os.path.join(base_path, icon_folder, setting_name)


def log_time(message, start_time):
    import time
    elapsed = time.time() - start_time
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {message}: {elapsed:.2f}s\n")


def check_market_open(stock_type, now):
    h, m = now.hour, now.minute

    if stock_type == 0:  # 한국 주식 (09:00 ~ 15:20)
        return (9, 0) <= (h, m) <= (15, 20)
    else:  # 미국 주식 (22:30 ~ 익일 05:00)
        # 22:30 이후 또는 05:00 이전 (미국 시간은 자정을 넘어가므로 or 연산)
        return (h, m) >= (22, 30) or h < 5


def calc_ticker_info_position(obj, idx):
    row = obj.full_df.iloc[idx]

    close_price = row['Close']
    open_price = row['Open']
    high_price = row['High']
    low_price = row['Low']
    change = row['Change'] * 100

    cur_min, cur_max = obj.ax.get_xlim()
    pos_ratio = (idx - cur_min) / (cur_max - cur_min) if (cur_max - cur_min) != 0 else 0

    y_min, y_max = obj.ax.get_ylim()
    target_y = (open_price + close_price) / 2
    y_ratio = (target_y - y_min) / (y_max - y_min) if (y_max - y_min) != 0 else 0

    x_off = -130 if pos_ratio > 0.6 else 30
    y_off = -100 if y_ratio > 0.6 else 15
    label_offset = (x_off, y_off)

    target_y = (open_price + close_price) / 2
    reason = row['reason'] if 'reason' in obj.full_df.columns else ""

    diff = close_price - open_price
    if open_price != 0:
        change_rate = (diff / open_price) * 100
    else:
        change_rate = 0

    # 1. 변동에 따른 색상 결정
    if diff > 0:
        bg_color = "red"  # 상승: 빨간 배경
        text_color = "white"
    elif diff < 0:
        bg_color = "blue"  # 하락: 파란 배경
        text_color = "white"
    else:
        bg_color = "white"  # 보합: 흰색 배경
        text_color = "black"

    daily_change_formatted = f"{change :+.2f}%"
    rate_text = f"{change_rate :+.2f}%"
    width = 20
    sep = "-" * width
    info = {
        "open": open_price,  # 시가
        "close": close_price,  # 종가
        "high": high_price,  # 최고가
        "low": low_price,  # 최저가
        "diff": diff,
        "rate_text": rate_text,  # 금일 대비
        "target_y": target_y,
        "offset": label_offset,
        "bg_color": bg_color,
        "text_color": text_color,
        "sep": sep,
        "daily_change": daily_change_formatted,  # 전일 대비
        'reason': reason  # 분석 결과
    }
    return info
def calc_max_min_info_position(obj):
    if hasattr(obj, 'cursor_annotation_high'):
        try:
            obj.cursor_annotation_high.remove()
        except:
            pass

    if hasattr(obj, 'cursor_annotation_low'):
        try:
            obj.cursor_annotation_low.remove()
        except:
            pass

    # 1. 범위 계산 로직 (기존과 동일)
    cur_min, cur_max = obj.ax.get_xlim()
    cur_ymin, cur_ymax = obj.ax.get_ylim()  # 현재 화면에 보이는 Y축 범위 가져오기

    start_idx = max(0, int(round(cur_min)))
    end_idx = min(len(obj.full_df) - 1, int(round(cur_max)))
    visible_data = obj.full_df.iloc[start_idx: end_idx + 1]

    if not visible_data.empty:
        max_price = visible_data['High'].max()
        min_price = visible_data['Low'].min()

        real_max_idx = start_idx + visible_data['High'].values.argmax()
        real_min_idx = start_idx + visible_data['Low'].values.argmin()

        max_pos_x_ratio = (real_max_idx - cur_min) / (cur_max - cur_min) if (cur_max - cur_min) != 0 else 0
        x_off = -70 if max_pos_x_ratio > 0.8 else 20

        max_pos_y_ratio = (max_price - cur_ymin) / (cur_ymax - cur_ymin) if (cur_ymax - cur_ymin) != 0 else 0
        y_off = -30 if max_pos_y_ratio > 0.85 else 20  # 너무 높으면 -30(아래로), 아니면 20(위로)

        # 새로운 주석 객체를 생성하여 저장 (이전 객체는 가비지 컬렉터가 처리)
        obj.cursor_annotation_high = obj.ax.annotate(
            f"최고가: {int(max_price):,}",
            xy=(real_max_idx, max_price),
            xytext=(x_off,y_off),
            textcoords="offset points", color="white", fontweight="bold",
            arrowprops=dict(arrowstyle='->', color='red'),
            bbox=dict(boxstyle='round,pad=0.3', fc='red', ec='red', alpha=0.8),
        )

        min_pos_x_ratio = (real_min_idx - cur_min) / (cur_max - cur_min) if (cur_max - cur_min) != 0 else 0
        min_x_off = -70 if min_pos_x_ratio > 0.8 else 20

        # 최저가가 바닥에 너무 붙었으면 위로 올림
        min_pos_y_ratio = (min_price - cur_ymin) / (cur_ymax - cur_ymin) if (cur_ymax - cur_ymin) != 0 else 0
        min_y_off = 20 if min_pos_y_ratio < 0.15 else -30  # 너무 낮으면 20(위로), 아니면 -30(아래로)

        obj.cursor_annotation_low = obj.ax.annotate(
            f"최저가: {int(min_price):,}",
            xy=(real_min_idx, min_price),
            xytext=(min_x_off,min_y_off),
            textcoords="offset points", color="white", fontweight="bold",
            arrowprops=dict(arrowstyle='->', color='blue'),
            bbox=dict(boxstyle='round,pad=0.3', fc='blue', ec='blue', alpha=0.8),
        )
        obj.ax.set_ylim(min_price * 0.90, max_price * 1.10)
        obj.canvas.draw_idle()
        return min_price, max_price
    return None, None


# 휠 이벤트 연결 (이제 휠 줌도 축 범위 변경을 유발하므로 자동으로 위의 함수가 작동함)
def on_scroll(obj, event):
    if event.inaxes != obj.ax: return
    base_scale = 1.2
    scale = 1 / base_scale if event.button == 'up' else base_scale

    # 1. 현재 축 범위 가져오기
    cur_xlim = obj.ax.get_xlim()
    cur_ylim = obj.ax.get_ylim()

    # 2. 마우스 위치 기준 잡기
    xdata, ydata = event.xdata, event.ydata

    # 3. 새로운 범위 계산 (X와 Y 동일하게 적용)
    new_width = (cur_xlim[1] - cur_xlim[0]) * scale
    new_height = (cur_ylim[1] - cur_ylim[0]) * scale

    relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
    rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

    # 4. 축 업데이트
    obj.ax.set_xlim(xdata - new_width * (1 - relx), xdata + new_width * relx)
    calc_max_min_info_position(obj)

    obj.canvas.draw_idle()

def on_press(obj, event):
    if event.inaxes == obj.ax:
        obj.is_dragging = True
        obj.press_data_x = event.xdata
        obj.press_pixel_x = event.x

def on_release(obj, event):
    obj.is_dragging = False

def on_motion(obj, event):
    if event.inaxes != obj.ax:  # 마우스가 차트 안에 있을 때만
        return

    if obj.is_dragging:
        # 드래그 거리 계산
        dx = obj.press_data_x - event.xdata
        cur_xlim = obj.ax.get_xlim()

        # 새로운 범위 계산
        new_min = cur_xlim[0] + dx
        new_max = cur_xlim[1] + dx

        total_len = len(obj.full_df)
        # [수정] 오른쪽 여백을 위해 total_len에 + 10 정도를 더해줍니다.
        padding = 10

        if new_min < -5:  # 왼쪽으로도 약간 더 갈 수 있게 수정
            return
        if new_max > total_len + padding:  # 오른쪽 끝에 여백 허용
            return

        obj.ax.set_xlim(new_min, new_max)

        # Y축 자동 조절
        calc_max_min_info_position(obj)

    obj.draw_current_candle_data(event)
    obj.canvas.draw_idle()

def limit_check_and_apply(obj, *args):
    # 1. 인덱스 기반 경계값 설정
    total_len = len(obj.full_df)
    min_limit = -1
    max_limit = total_len + 1
    # 2. 현재 축 범위 가져오기
    cur_min, cur_max = obj.ax.get_xlim()

    # 3. 제한 적용 로직 (인덱스 기준)
    needs_redraw = False
    new_min, new_max = cur_min, cur_max

    if cur_min < min_limit:
        new_min = min_limit
        needs_redraw = True
    if cur_max > max_limit:
        new_max = max_limit
        needs_redraw = True

    if needs_redraw:
        obj.ax.set_xlim(new_min, new_max)
        obj.canvas.draw_idle()