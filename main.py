import os
import sys
import time
from dotenv import load_dotenv

# 0 = 모든 로그, 1 = 경고 제외, 2 = 에러만, 3 = 아무것도 안 봄
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0' # oneDNN 관련 경고 제거

# 2. 콘솔 없는 환경에서 로그 버퍼 데드락 방지 (아까 드린 코드)
if getattr(sys, 'frozen', False):
    import io
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

def main():
    start_time = time.time()
    import services.ui_helper as helper
    helper.log_time("helper 로드 완료", start_time)

    import tkinter as tk
    helper.log_time("tk 로드 완료", start_time)

    helper.set_icons()
    root = tk.Tk()
    helper.center_window(root, 500, 100)
    root.attributes('-topmost', True)  # 맨 위로 올리기
    root.update_idletasks()  # 반영
    root.attributes('-topmost', False)  # 고정 해제 (이제 다른 창 클릭 가능)

    loading = helper.LoadingWindow(root)
    loading.show_progress("데이터 베이스 설정중...")
    root.update()

    from database.connection_SQL import setup_database
    helper.log_time("DB 모듈 로드 완료", start_time)
    if setup_database():
        helper.log_time("ui 생성 시작", start_time)

        from ui.main_gui import StockApp
        import config  # config.py 불러오기
        loading.stop()
        # GUI에도 설정값 전달
        StockApp(root, config.WATCHLIST)
        root.mainloop()
    else:
        loading.stop()
        loading.show_message("설치중 오류가 발생했습니다.")



if __name__ == "__main__":
    main()
