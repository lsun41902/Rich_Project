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

def send_discord_message(content):
    import config  # config.py 불러오기
    import requests

    # config에 있는 URL 리스트 사용
    url = config.MY_INFO[0]['webhook']
    try:
        payload = {"content": content}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ 연결 오류: {e}")


def main():
    import threading
    import tkinter as tk
    from database.connection_SQL import setup_database
    from ui.gui import StockApp
    from services.alert import alert_worker
    import config  # config.py 불러오기

    setup_database()

    # alert_worker에 설정값 전달
    alert_thread = threading.Thread(
        target=alert_worker,
        args=(send_discord_message,),
        daemon=True
    )
    alert_thread.start()

    root = tk.Tk()
    # GUI에도 설정값 전달
    app = StockApp(root, config.WATCHLIST)

    root.mainloop()

if __name__ == "__main__":
    main()