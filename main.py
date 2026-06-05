import requests
from datetime import datetime
from config import BOT_TOKEN, CHAT_ID

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "usd"
    }
    data = requests.get(url).json()

    return {
        "bitcoin": data["bitcoin"]["usd"],
        "ethereum": data["ethereum"]["usd"]
    }

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload)

def main():
    prices = get_prices()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"""
📊 قیمت ارزها
🕒 {now}

₿ بیت‌کوین: {prices['bitcoin']} $
Ξ اتریوم: {prices['ethereum']} $
"""

    send_message(message)

if __name__ == "__main__":
    main()
