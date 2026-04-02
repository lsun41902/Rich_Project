import os
import sys

# 1. TensorFlow 로그 레벨 설정 (가장 위에 배치)
# 0 = 모든 로그, 1 = 경고 제외, 2 = 에러만, 3 = 아무것도 안 봄
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' # oneDNN 관련 경고 제거

# 2. 콘솔 없는 환경에서 로그 버퍼 데드락 방지 (아까 드린 코드)
if getattr(sys, 'frozen', False):
    import io
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

def main():
    import tkinter as tk
    from database.connection_SQL import setup_database
    from ui.main_gui import StockApp
    import config  # config.py 불러오기
    import services.ui_helper as helper

    setup_database()
    helper.set_icons()
    root = tk.Tk()

    # GUI에도 설정값 전달
    app = StockApp(root, config.WATCHLIST)

    root.mainloop()

if __name__ == "__main__":
    main()
