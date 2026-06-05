import requests
from bs4 import BeautifulSoup

def get_prices():
    url = "https://www.tgju.org/"
    # اضافه کردن هدر برای شبیه‌سازی مرورگر واقعی
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # پیدا کردن قیمت‌ها با استفاده از کلاس‌های سایت
    try:
        dollar = soup.find("td", {"data-market-param": "price_dollar_rl"}).text
        gold = soup.find("td", {"data-market-param": "geram18"}).text
        
        with open("prices.txt", "w", encoding="utf-8") as f:
            f.write(f"قیمت دلار: {dollar}\nقیمت طلا ۱۸ عیار: {gold}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_prices()
