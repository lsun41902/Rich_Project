import threading
import tkinter as tk
import requests
import config  # config.py 불러오기

from database.connection_SQL import setup_database
from ui.gui import StockApp
from services.alert import alert_worker

# 이제 config.WATCHLIST 처럼 접근 가능합니다.

def send_discord_message(content):
    # config에 있는 URL 리스트 사용
    for url in config.WEBHOOK_URLS:
        try:
            payload = {"content": content}
            requests.post(url, json=payload)
        except Exception as e:
            print(f"⚠️ 연결 오류: {e}")


def main():
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