def center_window(window, width, height, parent):
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

def pull_request_stock(code):
    from datetime import datetime, timedelta
    import FinanceDataReader as fdr
    import config

    try:
        default_code, suffix = code.split('.')

        selected = config.MY_INFO[0]['market_type']

        # 오늘과 7일 전 날짜 설정
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # 형식 변환
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        # 넉넉한 기간으로 조회
        # 라디오 버튼 값에 따라 소스 접두어 설정
        ticker = code.split('.')
        if selected == 0:  # Naver
            symbol = f"NAVER:{ticker[0]}"
        elif selected == 1:  # KRX
            symbol = ticker[0]
        elif selected == 2:  # Yahoo
            symbol = f"YAHOO:{default_code}.{suffix}"  # 야후는 .KS 접미사 필요
        else:
            symbol = code
        try:
            df = fdr.DataReader(symbol, start=start_str, end=end_str)
            return df
        except Exception as e:
            print(f"📡 fdr 데이터 로드 오류 ({symbol}): {e}")
        return 0
    except Exception as e:
        print(f"업데이트 오류: {e}")


def pull_request_stock_NASDAQ():
    import FinanceDataReader as fdr
    # 1. 나스닥(NASDAQ) 종목 리스트
    df_nasdaq = fdr.StockListing('S&P500')
    import pandas as pd
    # 1. 컬럼 너비 제한 해제 (내용이 길어도 다 보여줌)
    pd.set_option('display.max_colwidth', None)

    # 2. 보여줄 최대 컬럼 수 설정 (컬럼이 많아도 안 잘림)
    pd.set_option('display.max_columns', None)

    # 3. 출력 화면 너비 설정 (한 줄에 길게 나오도록)
    pd.set_option('display.width', 1000)

    print(df_nasdaq[['Symbol', 'Name', 'Sector', 'Industry']].head(20))


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

    def __init__(self, parent, message="과거 60일의 주가와 거래량을\n근거로 향후 5일 예측 중..."):

        import tkinter as tk
        from tkinter import ttk
        self.window = tk.Toplevel(parent)
        self.window.title("분석")
        self.window.geometry("300x100")

        # 메인 창 중앙에 배치
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 150
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 50
        self.window.geometry(f"+{x}+{y}")

        # 창 닫기 버튼 무효화 (작업 중 강제 종료 방지)
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
        self.window.attributes("-topmost", True)  # 항상 위에

        label = tk.Label(self.window, text=message)
        label.pack(pady=10)

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
