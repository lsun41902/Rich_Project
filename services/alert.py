import services.ui_helper as helper
from datetime import datetime

def send_stock_open_close_alim(title, df):
    report = f"📊 **{title}**\n"
    for i, row in df.iterrows():
        code, name, target_price, target_price_us, buy_price, buy_price_us, amount, dollar_price, stock_type = row['Code'], row['Name'],row['Target_Price'],row['Target_Price_US'],row['Buy_Price'],row['Buy_Price_US'],row['Amount'],row['Dollar_Price'], row['Stock_Type']
        change = df['Change'].iloc[-1] * 100
        daily_change_formatted = f"{change :+.2f}%"
        price = row['Close']
        unit = helper.data_unit(stock_type)
        report += f"- {name}: {int(float(price)):,}{unit} ({daily_change_formatted})\n"

    __send_discord_message(report)
    print(f"📅 보고 발송 완료: {title}")

def send_stock_alim(title, msg):
    report = f"📊 **{title}**\n"
    message = report + msg
    __send_discord_message(message)
    print(f"📅 보고 발송 완료: {title}")

def __send_discord_message(content):
    import config  # config.py 불러오기
    import requests

    # config에 있는 URL 리스트 사용
    url = config.MY_INFO[0]['webhook']
    try:
        payload = {"content": content}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ 연결 오류: {e}")

def check_trading_signals(df, last_report_min,ticker_name):
    # 1. 골든크로스 체크
    ma5 = df['Close'].rolling(window=5).mean()
    ma20 = df['Close'].rolling(window=20).mean()
    now = datetime.now()
    current_minute = now.minute

    if ma5.iloc[-2] < ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]:
        unit = helper.data_unit(0)
        if current_minute % 5 == 0 and last_report_min != current_minute:
            change = df['Change'].iloc[-1] * 100
            daily_change_formatted = f"{change :+.2f}%"
            send_stock_alim("🚀 골든크로스 발생!", f"{ticker_name} : {int(df['Close'].iloc[-1]):,}{unit} ({daily_change_formatted})")
            return True
