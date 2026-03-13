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


import win32api
import win32con
import win32gui

def set_korean_ime():
    # 현재 포커스가 있는 윈도우의 핸들(hwnd)을 가져옴
    hwnd = win32gui.GetForegroundWindow()
    # HIMC(Input Context)를 열어서 한글 모드(0x01)로 설정
    # 0x0003: 가져오기, 0x0006: 설정하기
    himc = win32api.SendMessage(hwnd, win32con.WM_IME_CONTROL, 0x0003, 0)
    if himc:
        win32api.SendMessage(himc, win32con.WM_IME_CONTROL, 0x0006, 0x0001)