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


import ctypes
import pyautogui

def set_korean_ime():
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

from tkinter import messagebox


def show_message_box(self, title, message, mtype=0):
    if mtype == 0:
        return messagebox.askyesno(title, message, parent=self.header_frame)
    elif mtype == 1:
        return messagebox.showwarning(title, message, parent=self.header_frame)
    else:
        return messagebox.askyesno(title, message, parent=self.header_frame)

from datetime import datetime, timedelta
def check_stock_open_close_time():
    now = datetime.now()
    if (now.hour == 9 and now.minute >= 0) or (9 < now.hour < 15) or (now.hour == 15 and now.minute <= 20):
        return True
    else:
        return False


import FinanceDataReader as fdr
import config

def pull_request_stock(code):
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


def volume_formatter(x, pos):
    """숫자 크기에 따라 단위를 붙여주는 함수"""
    if x >= 1e9:   # 10억 이상
        return f'{x*1e-9:,.1f}B'
    elif x >= 1e6: # 100만 이상
        return f'{x*1e-6:,.1f}M'
    elif x >= 1e3: # 1,000 이상
        return f'{x*1e-3:,.0f}K'
    else:
        return f'{x:,.0f}'

def date_formatter(date):
    # 1. 문자열을 날짜 객체로 변환 (Parse)
    dt_obj = datetime.strptime(str(date), "%Y%m%d")

    # 2. 원하는 형식의 문자열로 변환 (Format)
    return dt_obj.strftime("%Y/%m/%d")


from cryptography.fernet import Fernet
import base64
import hashlib
import subprocess

def get_crypto_key():
    """
    사용자 PC의 고유 UUID를 읽어와서 32바이트 암호화 열쇠를 생성합니다.
    열쇠를 별도로 저장할 필요가 없어서 매우 안전합니다.
    """
    try:
        # 윈도우 전용: 메인보드 고유 UUID 추출
        cmd = 'wmic csproduct get uuid'
        uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
    except:
        # 만약 실패할 경우를 대비한 백업 (컴퓨터 이름 사용)
        import platform
        uuid = platform.node()

    # UUID를 SHA256으로 해싱하여 32바이트 규격 생성
    key_hash = hashlib.sha256(uuid.encode()).digest()
    # Fernet 규격(Base64)으로 변환
    return base64.urlsafe_b64encode(key_hash)

def encrypt_key(raw_api_key):
    """DB 저장 전 호출: 평문 -> 암호문"""
    if not raw_api_key: return ""
    f = Fernet(get_crypto_key())
    return f.encrypt(raw_api_key.encode()).decode()

def decrypt_key(encrypted_api_key):
    """DB 로드 후 호출: 암호문 -> 평문"""
    if not encrypted_api_key: return ""
    try:
        f = Fernet(get_crypto_key())
        return f.decrypt(encrypted_api_key.encode()).decode()
    except:
        # 복호화 실패 시(이미 평문이거나 기기가 바뀐 경우) 원본 반환
        return encrypted_api_key


import tkinter as tk
from tkinter import ttk


class LoadingWindow:
    def __init__(self, parent, message="과거 60일의 주가와 거래량을\n근거로 향후 5일 예측 중..."):
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
        self.progress.stop()
        self.window.destroy()