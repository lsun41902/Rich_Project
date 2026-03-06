import time
from datetime import datetime
import yfinance as yf
import config

# 전역 캐시 (필요시 사용)
current_prices_cache = {}


def get_stock_data(ticker):
    """yfinance를 이용한 최신 가격 추출"""
    try:
        stock = yf.Ticker(ticker)
        return stock.fast_info.last_price
    except Exception as e:
        print(f"⚠️ 가격 가져오기 실패({ticker}): {e}")
        return None


def send_stock_report(title, watchlist, send_message_func):
    """보고서 생성 및 발송 (중복 코드 제거)"""
    report = f"📊 **{title}**\n"
    for ticker, info in watchlist.items():
        name = info[0]
        price = current_prices_cache.get(ticker, 0)
        # 통화 단위 결정
        unit = "원" if any(ex in ticker for ex in [".KS", ".KQ"]) else "$"
        report += f"- {name}: {int(float(price)):,}{unit}\n"

    send_message_func(report)
    print(f"📅 보고 발송 완료: {title}")


def alert_worker(send_message_func):
    """배경에서 주가를 체크하여 알림 전송 (쓰레드 전용)"""
    print("🤖 알림 서비스가 가동되었습니다.")
    already_alerted = set()  # 리스트보다 검색 속도가 빠른 set 사용

    while True:
        now = datetime.now()

        for info in config.WATCHLIST.values():
            code, name, target = info
            current = get_stock_data(code)

            if current is None: continue

            # 1. 데이터 업데이트
            current_prices_cache[code] = current
            unit = "원" if any(ex in code for ex in [".KS", ".KQ"]) else "$"

            # 2. 목표가 도달 체크 (돌파 알림)
            if current >= target:
                if code not in already_alerted:
                    msg = f"🚀 **목표가 달성!**\n종목: {name}({code})\n현재가: **{int(float(current)):,}{unit}** (목표: {int(float(target)):,}{unit})"
                    send_message_func(msg)
                    already_alerted.add(code)
                    print(f"🔔 알림 발송: {name}")
            else:
                # 목표가 아래로 내려가면 알림 리스트에서 제거 (재진입 시 다시 알림)
                if code in already_alerted:
                    already_alerted.remove(code)

        # 3. 정기 보고 로직 (시간 조건)
        # 장 시작 보고 (09:00)
        if now.hour == 9 and now.minute == 0 and 0 <= now.second < 25:
            send_stock_report("오전 장 시작 보고", config.WATCHLIST, send_message_func)
            time.sleep(30)  # 중복 발송 방지

        # 장 마감 보고 (15:15)
        elif now.hour == 15 and now.minute == 15 and 0 <= now.second < 25:
            send_stock_report("오후 장 마감 보고", config.WATCHLIST, send_message_func)
            time.sleep(30)

        # 20초 주기 검사
        time.sleep(20)