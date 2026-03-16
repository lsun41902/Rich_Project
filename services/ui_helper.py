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